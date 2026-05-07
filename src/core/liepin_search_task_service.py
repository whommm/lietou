"""Persist candidates from the current Liepin result page."""

import json
import logging
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from .candidate_excel_service import CandidateExcelService
from .liepin_resume_extractor import LiepinResumeExtractionError, LiepinResumeExtractor
from .liepin_search_service import (
    LiepinSearchCandidate,
    LiepinSearchNoResultsError,
    LiepinSearchService,
)
from .search_task_repository import SearchTaskRepository
from ..models import SearchTask

logger = logging.getLogger(__name__)


@dataclass
class SearchTaskExecutionSummary:
    """Execution summary for one persisted search task."""

    task_id: str
    excel_path: str = ""
    processed_keywords: List[str] = field(default_factory=list)
    pages_processed: int = 0
    sourced_candidate_count: int = 0
    enriched_candidate_count: int = 0
    partial_candidate_count: int = 0
    failed_candidate_count: int = 0
    failed_candidates: List[dict] = field(default_factory=list)
    executed_rounds: List[dict] = field(default_factory=list)
    query_level_stats: List[dict] = field(default_factory=list)


class LiepinSearchTaskService:
    """Execute search rounds and store candidates into an Excel workbook."""

    def __init__(
        self,
        task_repository: SearchTaskRepository,
        candidate_excel_service: CandidateExcelService,
        search_service: LiepinSearchService,
        resume_extractor: LiepinResumeExtractor,
    ):
        self.task_repository = task_repository
        self.candidate_excel_service = candidate_excel_service
        self.search_service = search_service
        self.resume_extractor = resume_extractor

    def run_task(
        self,
        task_id: str,
        cancel_event=None,
        on_round_complete: Optional[Callable] = None,
        on_all_complete: Optional[Callable] = None,
    ) -> SearchTaskExecutionSummary:
        """Execute the configured search plan and persist candidates."""
        task = self.task_repository.get_by_id(task_id)
        if task is None:
            raise ValueError("搜索任务不存在: {}".format(task_id))

        summary = SearchTaskExecutionSummary(task_id=task.id)
        self.task_repository.update_status(
            task.id,
            "running",
            current_step="读取当前搜索结果页",
            mark_started=True,
        )

        try:
            rounds = self._build_search_rounds(task)
            if not rounds:
                rounds = [{"query": self._pick_source_keyword(task), "label": "手动搜索", "priority": 1}]
            summary.excel_path = self.candidate_excel_service.create_workbook(
                task.task_name or "候选人"
            )
            seen_candidates = set()
            control_snapshot = self._build_search_control_snapshot(rounds)
            filters = task.keywords.get("filters") or {}
            per_round_limit = int(task.keywords.get("per_round_limit") or 30)
            self.task_repository.update_execution_artifacts(
                task.id,
                executed_queries=[],
                query_level_stats=[],
                search_control_snapshot=control_snapshot,
            )
            logger.warning("[run_task] task=%s rounds=%s max_pages=%s max_candidates=%s", task.id, len(rounds), task.max_pages, task.max_candidates)

            for round_index, round_info in enumerate(rounds, start=1):
                if cancel_event and cancel_event.is_set():
                    raise RuntimeError("用户已取消任务")
                query = (round_info.get("query") or "").strip()
                if not query:
                    continue
                summary.processed_keywords.append(query)
                summary.executed_rounds.append(
                    {
                        "round_index": round_index,
                        "query": query,
                        "label": round_info.get("label") or "第{}轮搜索".format(round_index),
                        "priority": round_info.get("priority") or round_index,
                        "match_mode": round_info.get("match_mode") or "all",
                        "scope": round_info.get("scope") or "全部经历",
                        "position_filter": round_info.get("position_filter") or "",
                        "intent": round_info.get("intent") or "",
                    }
                )
                round_stats = {
                    "round_index": round_index,
                    "query": query,
                    "label": round_info.get("label") or "第{}轮搜索".format(round_index),
                    "priority": round_info.get("priority") or round_index,
                    "match_mode": round_info.get("match_mode") or "all",
                    "scope": round_info.get("scope") or "全部经历",
                    "position_filter": round_info.get("position_filter") or "",
                    "intent": round_info.get("intent") or "",
                    "pages_processed": 0,
                    "raw_candidates": 0,
                    "accepted_candidates": 0,
                    "deduplicated_candidates": 0,
                    "failed_candidates": 0,
                    "row_indexes": [],
                }
                summary.query_level_stats.append(round_stats)
                round_row_indexes: List[int] = []
                self._persist_execution_progress(task.id, summary, control_snapshot)
                self.task_repository.update_status(
                    task.id,
                    "running",
                    current_step="执行第 {} 轮搜索：{}".format(round_index, query),
                )
                try:
                    candidates = self._search_with_filters(query, filters, round_info)
                except LiepinSearchNoResultsError as exc:
                    logger.warning("[run_task] round=%s query=%s empty results: %s", round_index, query, exc)
                    round_stats["pages_processed"] += 1
                    summary.pages_processed += 1
                    self._persist_execution_progress(task.id, summary, control_snapshot)
                    continue
                round_pages_processed = 1
                summary.pages_processed += 1
                round_stats["pages_processed"] += 1
                logger.warning("[run_task] round=%s query=%s page=%s extracted_candidates=%s", round_index, query, 1, len(candidates))

                stop_round = self._process_candidate_batch(
                    task=task,
                    candidates=candidates,
                    keyword=query,
                    page_number=1,
                    summary=summary,
                    seen_candidates=seen_candidates,
                    round_stats=round_stats,
                    round_row_indexes=round_row_indexes,
                    max_round_candidates=per_round_limit,
                    cancel_event=cancel_event,
                )
                self._persist_execution_progress(task.id, summary, control_snapshot)
                if stop_round and summary.sourced_candidate_count >= task.max_candidates:
                    break

                while (not stop_round) and round_pages_processed < max(1, task.max_pages):
                    if cancel_event and cancel_event.is_set():
                        raise RuntimeError("用户已取消任务")
                    if summary.sourced_candidate_count >= task.max_candidates:
                        logger.warning("[run_task] reached max_candidates=%s, stopping", task.max_candidates)
                        break
                    if round_stats["accepted_candidates"] >= per_round_limit:
                        logger.warning("[run_task] reached per_round_limit=%s for query=%s", per_round_limit, query)
                        break
                    if not self.search_service.go_to_next_result_page():
                        logger.warning("[run_task] no more pages for query=%s", query)
                        break
                    self.search_service.ensure_result_page()
                    round_pages_processed += 1
                    summary.pages_processed += 1
                    round_stats["pages_processed"] += 1
                    self.task_repository.update_status(
                        task.id,
                        "running",
                        current_step="执行第 {} 轮搜索第 {} 页：{}".format(
                            round_index, round_pages_processed, query
                        ),
                    )
                    candidates = self.search_service.extract_current_page_candidates()
                    logger.warning("[run_task] round=%s query=%s page=%s extracted_candidates=%s", round_index, query, round_pages_processed, len(candidates))
                    stop_round = self._process_candidate_batch(
                        task=task,
                        candidates=candidates,
                        keyword=query,
                        page_number=round_pages_processed,
                        summary=summary,
                        seen_candidates=seen_candidates,
                        round_stats=round_stats,
                        round_row_indexes=round_row_indexes,
                        max_round_candidates=per_round_limit,
                        cancel_event=cancel_event,
                    )
                    self._persist_execution_progress(task.id, summary, control_snapshot)
                    if stop_round:
                        break
                round_stats["row_indexes"] = list(round_row_indexes)
                if on_round_complete:
                    on_round_complete(
                        summary.excel_path,
                        round_index,
                        dict(round_info),
                        list(round_row_indexes),
                        dict(round_stats),
                        task,
                    )
                if summary.sourced_candidate_count >= task.max_candidates:
                    break

            self.task_repository.update_status(
                task.id,
                "completed",
                current_step="结果页入库完成，已处理 {} 页，线索 {} 位，完整 {} 位，待补抓 {} 位，失败 {} 位".format(
                    summary.pages_processed,
                    summary.sourced_candidate_count,
                    summary.enriched_candidate_count,
                    summary.partial_candidate_count,
                    summary.failed_candidate_count,
                ),
                mark_finished=True,
            )
            logger.warning("[run_task] completed pages=%s sourced=%s enriched=%s partial=%s failed=%s", summary.pages_processed, summary.sourced_candidate_count, summary.enriched_candidate_count, summary.partial_candidate_count, summary.failed_candidate_count)
            if on_all_complete:
                on_all_complete(summary, task)
            return summary
        except Exception as exc:
            logger.exception("[run_task] task failed")
            self.task_repository.update_status(
                task.id,
                "failed",
                current_step="结果页入库失败",
                error_message=str(exc),
                mark_finished=True,
            )
            raise

    def _search_with_filters(
        self, query: str, filters: Dict[str, object], round_info: Optional[Dict[str, object]] = None
    ):
        """Search with filters and per-round mode/scope while preserving test-double compatibility."""
        round_info = round_info or {}
        controls = {
            "match_mode": round_info.get("match_mode") or "",
            "scope": round_info.get("scope") or "",
            "position_filter": round_info.get("position_filter") or "",
        }
        controls = {key: value for key, value in controls.items() if value}
        if filters or controls:
            try:
                return self.search_service.search(query, filters=filters, **controls)
            except TypeError:
                try:
                    if filters:
                        return self.search_service.search(query, filters=filters)
                    return self.search_service.search(query)
                except TypeError:
                    candidates = self.search_service.search(query)
                    if filters and hasattr(self.search_service, "apply_filters"):
                        self.search_service.apply_filters(filters)
                        if hasattr(self.search_service, "extract_current_page_candidates"):
                            return self.search_service.extract_current_page_candidates()
                    return candidates
        return self.search_service.search(query)

    def _pick_source_keyword(self, task: SearchTask) -> str:
        """Use the first configured keyword as the import source label."""
        flattened = self._flatten_keywords(task)
        return flattened[0] if flattened else "手动搜索"

    def _build_search_rounds(self, task: SearchTask) -> List[dict]:
        rounds = []
        for item in task.keywords.get("executable_rounds", []):
            if not isinstance(item, dict):
                continue
            query = (item.get("query") or "").strip()
            if not query:
                continue
            rounds.append(
                {
                    "label": item.get("label") or "搜索轮次",
                    "query": query,
                    "intent": item.get("intent") or "",
                    "priority": item.get("priority") or len(rounds) + 1,
                    "match_mode": item.get("match_mode") or "all",
                    "scope": item.get("scope") or "全部经历",
                    "position_filter": item.get("position_filter") or "",
                }
            )
        if rounds:
            return rounds
        return [
            {
                "label": "默认搜索",
                "query": keyword,
                "priority": index + 1,
            }
            for index, keyword in enumerate(self._flatten_keywords(task))
        ]

    def _flatten_keywords(self, task: SearchTask) -> List[str]:
        ordered_keys = [
            "precise_keywords",
            "expansion_keywords",
            "synonyms",
            "boolean_queries",
        ]
        flattened = []
        seen = set()
        for key in ordered_keys:
            for item in task.keywords.get(key, []):
                normalized = (item or "").strip()
                if not normalized or normalized in seen:
                    continue
                seen.add(normalized)
                flattened.append(normalized)
        return flattened

    def _process_candidate_batch(
        self,
        task: SearchTask,
        candidates: List[LiepinSearchCandidate],
        keyword: str,
        page_number: int,
        summary: SearchTaskExecutionSummary,
        seen_candidates: set,
        round_stats: dict,
        round_row_indexes: Optional[List[int]] = None,
        max_round_candidates: Optional[int] = None,
        cancel_event=None,
    ) -> bool:
        round_stats["raw_candidates"] += len(candidates or [])
        for rank_index, candidate_summary in enumerate(candidates, start=1):
            if cancel_event and cancel_event.is_set():
                raise RuntimeError("用户已取消任务")
            if summary.sourced_candidate_count >= task.max_candidates:
                return True
            if max_round_candidates and round_stats["accepted_candidates"] >= max_round_candidates:
                return True
            candidate_key = self._build_candidate_dedupe_key(candidate_summary)
            if candidate_key and candidate_key in seen_candidates:
                round_stats["deduplicated_candidates"] += 1
                continue
            if candidate_key:
                seen_candidates.add(candidate_key)
            process_result = self._process_candidate(
                task,
                candidate_summary,
                keyword,
                page_number,
                rank_index,
                summary,
                None,
            )
            if process_result:
                round_stats["accepted_candidates"] += 1
                if round_row_indexes is not None:
                    round_row_indexes.append(process_result)
            else:
                round_stats["failed_candidates"] += 1
        return summary.sourced_candidate_count >= task.max_candidates or (
            bool(max_round_candidates)
            and round_stats["accepted_candidates"] >= int(max_round_candidates)
        )

    @staticmethod
    def _build_candidate_dedupe_key(candidate_summary: LiepinSearchCandidate) -> str:
        parts = [
            (candidate_summary.profile_url or "").strip().lower(),
            (candidate_summary.name or "").strip(),
            (candidate_summary.current_company or "").strip(),
            (candidate_summary.current_title or "").strip(),
        ]
        if parts[0]:
            return parts[0]
        fallback = "|".join(part for part in parts[1:] if part)
        return fallback.lower()

    def _process_candidate(
        self,
        task: SearchTask,
        candidate_summary: LiepinSearchCandidate,
        keyword: str,
        page_number: int,
        rank_index: int,
        summary: SearchTaskExecutionSummary,
        result_page,
    ) -> Optional[int]:
        import time
        start_time = time.time()
        try:
            row_index = self._save_candidate_summary(
                candidate_summary,
                keyword,
                page_number,
                rank_index,
                summary,
            )
        except Exception as exc:
            logger.error("[_process_candidate] save_candidate_summary failed: %s", exc)
            summary.failed_candidate_count += 1
            return None
        summary.sourced_candidate_count += 1

        self.task_repository.update_status(
            task.id,
            "running",
            current_step="提取候选人详情: {}".format(
                candidate_summary.name or candidate_summary.profile_url or rank_index
            ),
        )

        try:
            import random
            # Light anti-bot jitter: 0.3~1.2s before opening each detail
            time.sleep(random.uniform(0.3, 1.2))

            def _extract(page):
                detail_page = self.search_service.open_candidate_detail(
                    page, candidate_summary
                )
                try:
                    # Brief pause to let dynamic content settle and reduce bot signals
                    import random
                    time.sleep(random.uniform(0.5, 1.0))
                    return self.resume_extractor.extract_candidate(
                        detail_page, candidate_summary
                    )
                finally:
                    self.search_service.close_detail_page(detail_page, page)

            browser_manager = self.search_service.browser_manager
            if hasattr(browser_manager, "run_with_page"):
                candidate = browser_manager.run_with_page(_extract)
            else:
                page = browser_manager.ensure_page()
                candidate = _extract(page)
            resume_text = (candidate.resume_text or "").strip()
            if resume_text:
                capture_status = self.candidate_excel_service.CAPTURE_STATUS_SUCCESS
                self.candidate_excel_service.update_candidate_detail(
                    summary.excel_path,
                    row_index,
                    resume_text,
                    capture_status,
                )
                summary.enriched_candidate_count += 1
            else:
                capture_status = self.candidate_excel_service.CAPTURE_STATUS_PARTIAL
                self.candidate_excel_service.update_candidate_detail(
                    summary.excel_path,
                    row_index,
                    "",
                    capture_status,
                )
                summary.partial_candidate_count += 1
            logger.warning("[_process_candidate] rank=%s name=%s elapsed=%.2fs status=%s", rank_index, candidate_summary.name, time.time() - start_time, capture_status)
            return row_index
        except Exception as exc:
            logger.exception("[_process_candidate] rank=%s name=%s failed", rank_index, candidate_summary.name)
            try:
                self.candidate_excel_service.update_candidate_detail(
                    summary.excel_path,
                    row_index,
                    "",
                    self.candidate_excel_service.CAPTURE_STATUS_FAILED,
                )
            except Exception:
                # Excel 被占用等写入失败不应拖垮整个任务
                pass
            summary.partial_candidate_count += 1
            summary.failed_candidate_count += 1
            failed_identifier = (
                candidate_summary.profile_url
                or candidate_summary.name
                or "candidate-{}".format(rank_index)
            )
            summary.failed_candidates.append(
                {
                    "identifier": failed_identifier,
                    "name": candidate_summary.name or "",
                    "profile_url": candidate_summary.profile_url or "",
                    "page_number": page_number,
                    "rank_index": rank_index,
                    "row_index": row_index,
                    "reason": self._classify_candidate_error(exc),
                    "capture_status": self.candidate_excel_service.CAPTURE_STATUS_FAILED,
                }
            )
            return None

    def _persist_execution_progress(
        self,
        task_id: str,
        summary: SearchTaskExecutionSummary,
        control_snapshot: dict,
    ) -> None:
        self.task_repository.update_execution_artifacts(
            task_id,
            executed_queries=summary.executed_rounds,
            query_level_stats=summary.query_level_stats,
            search_control_snapshot=control_snapshot,
        )

    @staticmethod
    def _build_search_control_snapshot(rounds: List[dict]) -> dict:
        return {
            "round_count": len(rounds or []),
            "queries": [
                {
                    "label": item.get("label") or "",
                    "query": item.get("query") or "",
                    "priority": item.get("priority") or 0,
                    "position_filter": item.get("position_filter") or "",
                }
                for item in (rounds or [])
            ],
        }

    def _save_candidate_summary(
        self,
        candidate_summary: LiepinSearchCandidate,
        keyword: str,
        page_number: int,
        rank_index: int,
        summary: SearchTaskExecutionSummary,
    ) -> int:
        """Persist the result-card snapshot first, so failed detail extraction remains visible."""
        return self.candidate_excel_service.append_candidate_row(
            summary.excel_path,
            {
                "序号": summary.sourced_candidate_count + 1,
                "姓名": candidate_summary.name or "",
                "年龄": candidate_summary.age or "",
                "来源关键词": keyword,
                "页码": page_number,
                "排名": rank_index,
                "简历链接": candidate_summary.profile_url or "",
                "简历抓取状态": self.candidate_excel_service.CAPTURE_STATUS_PENDING,
                "简历详情": "",
                "匹配度分数": "",
                "匹配详情": "",
                "抓取时间": self.candidate_excel_service.now_text(),
                "匹配时间": "",
                "人才标签": self.candidate_excel_service.extract_talent_tags(
                    candidate_summary.summary or ""
                ),
                "联系方式": self.candidate_excel_service.extract_contact_info(
                    candidate_summary.summary or ""
                ),
            },
        )

    def _classify_candidate_error(self, exc: Exception) -> str:
        if isinstance(exc, LiepinResumeExtractionError):
            return "简历提取失败: {}".format(str(exc))
        return "候选人详情处理失败: {}".format(str(exc))
