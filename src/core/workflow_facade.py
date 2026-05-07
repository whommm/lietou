"""UI-independent facade for workflow API integrations."""

from __future__ import annotations

import json
import os
import re
from dataclasses import asdict
from typing import Dict, List, Optional

from .batch_match_service import BatchMatchService
from .candidate_excel_service import CandidateExcelService
from .config import ConfigManager
from .database import DatabaseManager
from .greeting_text_generation_service import GreetingTextGenerationService
from .history import HistoryManager, HistoryRecord
from .liepin_browser import LiepinBrowserManager
from .liepin_resume_extractor import LiepinResumeExtractor
from .liepin_search_service import LiepinSearchService
from .liepin_search_task_service import LiepinSearchTaskService
from .llm_client import LLMClient
from .match_criteria_service import MatchCriteriaService
from .search_strategy_generation_service import SearchStrategyGenerationService
from .search_strategy_service import SearchStrategyService
from .search_task_repository import SearchTaskRepository
from ..models import MatchCriteria
from ..utils.city_data import extract_city_from_text
from ..utils.helpers import validate_api_key, validate_url
from ..workflow import JobCategory, JobManager


class WorkflowError(Exception):
    """Raised when a workflow API action cannot be completed."""


class WorkflowFacade:
    """Expose core capabilities without depending on desktop UI widgets."""

    def __init__(
        self,
        config_manager: Optional[ConfigManager] = None,
        database_manager: Optional[DatabaseManager] = None,
        job_manager: Optional[JobManager] = None,
        workspace_root: Optional[str] = None,
        history_path: Optional[str] = None,
    ):
        self.config_manager = config_manager or ConfigManager()
        self.database_manager = database_manager or DatabaseManager()
        db_path = self.database_manager.db_path
        self.job_history_manager = HistoryManager(
            record_type="job_analysis",
            history_path=history_path,
            db_path=db_path,
        )
        self.search_task_repository = SearchTaskRepository(self.database_manager)
        self.candidate_excel_service = CandidateExcelService(
            workspace_root=workspace_root
        )
        self.search_strategy_service = SearchStrategyService()
        self.liepin_browser_manager = LiepinBrowserManager(self.config_manager)
        self.liepin_search_service = LiepinSearchService(self.liepin_browser_manager)
        self.liepin_resume_extractor = LiepinResumeExtractor()
        self.liepin_search_task_service = LiepinSearchTaskService(
            task_repository=self.search_task_repository,
            candidate_excel_service=self.candidate_excel_service,
            search_service=self.liepin_search_service,
            resume_extractor=self.liepin_resume_extractor,
        )
        self.job_manager = job_manager or JobManager()

    def health(self) -> dict:
        """Return service readiness for API callers."""
        browser_state = self.liepin_browser_manager.get_state()
        return {
            "status": "ok",
            "llm_configured": self._has_valid_llm_config(),
            "browser": asdict(browser_state),
        }

    def analyze_jd(self, jd_text: str, company_context: str = "") -> dict:
        """Analyze a JD and persist the resulting job history record."""
        jd_text = (jd_text or "").strip()
        if not jd_text:
            raise WorkflowError("岗位描述不能为空")
        client = self._create_llm_client()
        result = client.analyze_jd(jd_text, company_context or "")
        record = self.job_history_manager.save_record(jd_text, result)
        return {
            "record_id": record.id,
            "title": record.title,
            "analysis_html": result,
            "created_at": record.created_at,
        }

    def generate_match_criteria(self, record_id: str) -> dict:
        """Generate and persist match criteria for a job record."""
        record = self._get_job_record(record_id)
        warning = ""
        try:
            client = self._create_llm_client()
            criteria = MatchCriteriaService(client).generate(
                record.result, record.jd_text
            )
        except Exception as exc:
            criteria = MatchCriteriaService.build_fallback(record.jd_text)
            warning = "匹配条件生成失败，已使用本地保底规则：{}".format(exc)

        record.match_criteria_json = json.dumps(
            criteria.to_dict(), ensure_ascii=False
        )
        record.match_criteria_confirmed = True
        self.job_history_manager.repository.upsert(record)
        return {
            "record_id": record.id,
            "match_criteria": criteria.to_dict(),
            "warning": warning,
        }

    def generate_search_strategy(
        self, record_id: str, override_prompt_hint: str = ""
    ) -> dict:
        """Generate and persist executable Liepin search strategy."""
        record = self._get_job_record(record_id)
        analysis_html = record.result or ""
        if override_prompt_hint:
            analysis_html = "{}\n\n【额外搜索提示】\n{}".format(
                analysis_html, override_prompt_hint.strip()
            )

        warning = ""
        try:
            client = self._create_llm_client()
            strategy = SearchStrategyGenerationService(client).generate(
                analysis_html, record.jd_text
            )
        except Exception as exc:
            strategy = self.search_strategy_service.build_from_analysis_result(
                "{}\n{}".format(analysis_html, record.jd_text or "")
            )
            warning = "搜索策略生成失败，已使用本地保底策略：{}".format(exc)

        payload = self.search_strategy_service.to_payload(strategy)
        record.search_strategy_json = json.dumps(payload, ensure_ascii=False)
        record.search_strategy_confirmed = True
        self.job_history_manager.repository.upsert(record)
        return {
            "record_id": record.id,
            "strategy": payload,
            "warning": warning,
        }

    def start_liepin_capture(
        self,
        record_id: str,
        strategy: Optional[dict] = None,
        filters: Optional[dict] = None,
        max_pages: int = 1,
        max_candidates: int = 30,
        per_round_limit: int = 30,
    ) -> dict:
        """Create a browser job that captures Liepin candidates into Excel."""
        record = self._get_job_record(record_id)
        strategy_payload = dict(strategy or self._load_or_build_strategy(record))
        merged_filters = dict(strategy_payload.get("filters") or {})
        if filters is not None:
            merged_filters.update(filters or {})
        strategy_payload["filters"] = merged_filters
        strategy_payload["per_round_limit"] = max(1, int(per_round_limit or 30))

        search_task = self.search_task_repository.create(
            job_history_id=record.id,
            task_name="{} - API 猎聘抓取".format(record.title),
            keywords=strategy_payload,
            max_pages=max(1, int(max_pages or 1)),
            max_candidates=max(1, int(max_candidates or 30)),
        )
        rounds = strategy_payload.get("executable_rounds") or []

        def _run(context):
            total_rounds = max(1, len(rounds))

            def on_round_complete(
                excel_path,
                round_index,
                round_info,
                row_indexes,
                round_stats,
                _search_task,
            ):
                message = "{}：收录 {} 位".format(
                    round_info.get("query") or round_info.get("label") or "搜索轮次",
                    len(row_indexes or []),
                )
                context.report_progress(round_index, total_rounds, message)

            summary = self.liepin_search_task_service.run_task(
                search_task.id,
                cancel_event=context.cancel_event,
                on_round_complete=on_round_complete,
            )
            context.report_progress(total_rounds, total_rounds, "候选人抓取完成")
            return self._capture_summary_to_dict(summary)

        job_id = self.job_manager.submit(
            name="猎聘抓取 - {}".format(record.title),
            category=JobCategory.BROWSER,
            target=_run,
        )
        return {
            "job_id": job_id,
            "search_task_id": search_task.id,
            "record_id": record.id,
        }

    def start_batch_match_candidates(
        self,
        record_id: str,
        excel_path: str,
        row_indexes: Optional[List[int]] = None,
        max_workers: int = BatchMatchService.DEFAULT_WORKERS,
    ) -> dict:
        """Create a compute job that matches Excel candidates and writes results back."""
        record = self._get_job_record(record_id)
        excel_path = (excel_path or "").strip()
        if not excel_path:
            raise WorkflowError("候选人 Excel 路径不能为空")
        if not os.path.exists(excel_path):
            raise WorkflowError("候选人 Excel 文件不存在：{}".format(excel_path))

        rows = [int(item) for item in (row_indexes or []) if item]
        if rows:
            candidates = self.candidate_excel_service.load_matchable_candidates_by_rows(
                excel_path, rows
            )
        else:
            candidates = self.candidate_excel_service.load_matchable_candidates(
                excel_path
            )
        if not candidates:
            raise WorkflowError("当前 Excel 中没有可匹配候选人")

        match_criteria = self._load_match_criteria(record)
        if match_criteria is None:
            match_criteria = MatchCriteriaService.build_fallback(record.jd_text)

        config = self._get_llm_config()

        def _run(context):
            service = BatchMatchService(
                None,
                llm_client_factory=lambda: LLMClient(
                    api_base_url=config["api_base_url"],
                    api_key=config["api_key"],
                    model_name=config["model_name"],
                    timeout=180,
                ),
                max_workers=max_workers,
            )

            def progress_callback(current, total, candidate):
                context.report_progress(
                    current,
                    total,
                    getattr(candidate, "name", "") or "未命名候选人",
                )

            results = service.match_excel_candidates(
                record.jd_text,
                candidates,
                match_criteria=match_criteria,
                progress_callback=progress_callback,
            )
            payload = []
            for result in results:
                self.candidate_excel_service.write_match_result(
                    excel_path,
                    result.row_index,
                    result.tier,
                    result.detail,
                )
                payload.append(
                    {
                        "row_index": result.row_index,
                        "candidate_name": result.candidate_name,
                        "tier": result.tier or "",
                        "core_met_count": result.core_met_count,
                        "core_total": result.core_total,
                        "dealbreaker_hit": result.dealbreaker_hit,
                        "recommendation": result.recommendation,
                        "summary": result.summary,
                        "risks": result.risks,
                    }
                )
            return {
                "record_id": record.id,
                "excel_path": excel_path,
                "matched_count": len(payload),
                "results": payload,
            }

        job_id = self.job_manager.submit(
            name="批量匹配 - {}".format(record.title),
            category=JobCategory.COMPUTE,
            target=_run,
        )
        return {
            "job_id": job_id,
            "record_id": record.id,
            "candidate_count": len(candidates),
        }

    def generate_greeting_text(self, record_id: str, style: str = "general") -> dict:
        """Generate one greeting message for a job record."""
        record = self._get_job_record(record_id)
        client = self._create_llm_client(timeout=60)
        service = GreetingTextGenerationService(client)
        city = extract_city_from_text(record.jd_text) or extract_city_from_text(
            record.result
        )
        salary_range = self._extract_salary_range(record.jd_text)
        text = service.generate(
            job_title=record.title or "目标岗位",
            city=city or "该城市",
            job_description=record.jd_text,
            salary_range=salary_range,
            style=style or "general",
        )
        return {
            "record_id": record.id,
            "title": record.title,
            "text": text,
        }

    def get_job(self, job_id: str) -> Optional[dict]:
        return self.job_manager.snapshot(job_id)

    def list_jobs(self) -> list:
        return self.job_manager.list_snapshots()

    def cancel_job(self, job_id: str) -> bool:
        return self.job_manager.cancel(job_id)

    def _get_job_record(self, record_id: str) -> HistoryRecord:
        record = self.job_history_manager.get_by_id((record_id or "").strip())
        if record is None:
            raise WorkflowError("未找到岗位记录：{}".format(record_id))
        return record

    def _get_llm_config(self) -> dict:
        config = self.config_manager.config
        url = (config.api_base_url or "").strip()
        key = (config.api_key or "").strip()
        model = (config.model_name or "deepseek-chat").strip()
        if not url or not validate_url(url):
            raise WorkflowError("请先配置有效的 API Base URL")
        if not key or not validate_api_key(key):
            raise WorkflowError("请先配置有效的 API Key")
        return {
            "api_base_url": url,
            "api_key": key,
            "model_name": model,
            "timeout": int(config.timeout or 120),
        }

    def _has_valid_llm_config(self) -> bool:
        try:
            self._get_llm_config()
            return True
        except WorkflowError:
            return False

    def _create_llm_client(self, timeout: Optional[int] = None) -> LLMClient:
        config = self._get_llm_config()
        return LLMClient(
            api_base_url=config["api_base_url"],
            api_key=config["api_key"],
            model_name=config["model_name"],
            timeout=int(timeout or config["timeout"]),
        )

    def _load_or_build_strategy(self, record: HistoryRecord) -> dict:
        if record.search_strategy_json:
            try:
                payload = json.loads(record.search_strategy_json)
                if isinstance(payload, dict):
                    return payload
            except (TypeError, ValueError):
                pass
        return self.generate_search_strategy(record.id)["strategy"]

    @staticmethod
    def _load_match_criteria(record: HistoryRecord) -> Optional[MatchCriteria]:
        if not record.match_criteria_json:
            return None
        try:
            payload = json.loads(record.match_criteria_json)
            if isinstance(payload, dict):
                return MatchCriteria.from_dict(payload)
        except (TypeError, ValueError):
            return None
        return None

    @staticmethod
    def _capture_summary_to_dict(summary) -> dict:
        payload = asdict(summary)
        payload["message"] = (
            "抓取完成：处理 {} 页，收录 {} 位，完整 {} 位，部分 {} 位，失败 {} 位".format(
                summary.pages_processed,
                summary.sourced_candidate_count,
                summary.enriched_candidate_count,
                summary.partial_candidate_count,
                summary.failed_candidate_count,
            )
        )
        return payload

    @staticmethod
    def _extract_salary_range(text: str) -> str:
        patterns = [
            r"\d+\s*-\s*\d+\s*[kK]",
            r"\d+\s*[kK]\s*-\s*\d+\s*[kK]",
            r"\d+\s*-\s*\d+\s*万",
            r"年薪\s*\d+\s*-\s*\d+\s*万",
        ]
        for pattern in patterns:
            match = re.search(pattern, text or "")
            if match:
                return match.group(0)
        return ""
