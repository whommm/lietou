"""Persist candidates from the current Liepin result page."""

import logging
from dataclasses import dataclass, field
from typing import List

from .candidate_excel_service import CandidateExcelService
from .liepin_resume_extractor import LiepinResumeExtractionError, LiepinResumeExtractor
from .liepin_search_service import LiepinSearchCandidate, LiepinSearchService
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


class LiepinSearchTaskService:
    """Store candidates from the current result page into an Excel workbook."""

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

    def run_task(self, task_id: str, cancel_event=None) -> SearchTaskExecutionSummary:
        """Import candidates from the current result page into local storage."""
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
            keyword = self._pick_source_keyword(task)
            summary.processed_keywords.append(keyword)
            summary.excel_path = self.candidate_excel_service.create_workbook(
                task.task_name or "候选人"
            )
            logger.warning("[run_task] task=%s max_pages=%s max_candidates=%s", task.id, task.max_pages, task.max_candidates)
            for page_number in range(1, max(1, task.max_pages) + 1):
                if cancel_event and cancel_event.is_set():
                    raise RuntimeError("用户已取消任务")
                self.task_repository.update_status(
                    task.id,
                    "running",
                    current_step="读取第 {} 页搜索结果".format(page_number),
                )
                candidates = self.search_service.extract_current_page_candidates()
                summary.pages_processed += 1
                logger.warning("[run_task] page=%s extracted_candidates=%s", page_number, len(candidates))

                for rank_index, candidate_summary in enumerate(candidates, start=1):
                    if cancel_event and cancel_event.is_set():
                        raise RuntimeError("用户已取消任务")
                    if summary.sourced_candidate_count >= task.max_candidates:
                        logger.warning("[run_task] reached max_candidates=%s, stopping", task.max_candidates)
                        break
                    self._process_candidate(
                        task,
                        candidate_summary,
                        keyword,
                        page_number,
                        rank_index,
                        summary,
                        None,
                    )

                if summary.sourced_candidate_count >= task.max_candidates:
                    break
                if page_number >= max(1, task.max_pages):
                    break
                logger.warning("[run_task] attempting to go to next page from page=%s", page_number)
                logger.warning("[run_task] about to go to next page from page=%s", page_number)
                if not self.search_service.go_to_next_result_page():
                    logger.warning("[run_task] go_to_next_result_page returned False, stopping pagination")
                    break
                logger.warning("[run_task] next page navigation succeeded, ensuring result page")
                # Refresh page reference after navigation and validate still on search page
                self.search_service.ensure_result_page()
                logger.warning("[run_task] result page ensured after navigation")

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

    def _pick_source_keyword(self, task: SearchTask) -> str:
        """Use the first configured keyword as the import source label."""
        flattened = self._flatten_keywords(task)
        return flattened[0] if flattened else "手动搜索"

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

    def _process_candidate(
        self,
        task: SearchTask,
        candidate_summary: LiepinSearchCandidate,
        keyword: str,
        page_number: int,
        rank_index: int,
        summary: SearchTaskExecutionSummary,
        result_page,
    ) -> None:
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
            return
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
                "页码": page_number,
                "排名": rank_index,
                "简历链接": candidate_summary.profile_url or "",
                "简历抓取状态": self.candidate_excel_service.CAPTURE_STATUS_PENDING,
                "简历详情": "",
                "匹配度分数": "",
                "匹配详情": "",
                "抓取时间": self.candidate_excel_service.now_text(),
                "匹配时间": "",
            },
        )

    def _classify_candidate_error(self, exc: Exception) -> str:
        if isinstance(exc, LiepinResumeExtractionError):
            return "简历提取失败: {}".format(str(exc))
        return "候选人详情处理失败: {}".format(str(exc))
