"""Persist candidates from the current Liepin result page."""

from dataclasses import dataclass, field
from typing import Iterable, List, Optional

from .candidate_repository import CandidateRepository
from .liepin_resume_extractor import LiepinResumeExtractionError, LiepinResumeExtractor
from .liepin_search_service import LiepinSearchCandidate, LiepinSearchService
from .search_task_repository import SearchTaskRepository
from ..models import Candidate, SearchTask


@dataclass
class SearchTaskExecutionSummary:
    """Execution summary for one persisted search task."""

    task_id: str
    processed_keywords: List[str] = field(default_factory=list)
    candidate_count: int = 0
    failed_candidates: List[str] = field(default_factory=list)


class LiepinSearchTaskService:
    """Store candidates from the current result page into the local repository."""

    def __init__(
        self,
        task_repository: SearchTaskRepository,
        candidate_repository: CandidateRepository,
        search_service: LiepinSearchService,
        resume_extractor: LiepinResumeExtractor,
    ):
        self.task_repository = task_repository
        self.candidate_repository = candidate_repository
        self.search_service = search_service
        self.resume_extractor = resume_extractor

    def run_task(self, task_id: str) -> SearchTaskExecutionSummary:
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
            candidates = self.search_service.extract_current_page_candidates()
            keyword = self._pick_source_keyword(task)
            summary.processed_keywords.append(keyword)
            result_page = self.search_service.ensure_result_page()

            for rank_index, candidate_summary in enumerate(candidates, start=1):
                if summary.candidate_count >= task.max_candidates:
                    break
                self._process_candidate(
                    task,
                    candidate_summary,
                    keyword,
                    rank_index,
                    summary,
                    result_page,
                )

            self.task_repository.update_status(
                task.id,
                "completed",
                current_step="结果页入库完成，已入库 {} 位候选人".format(
                    summary.candidate_count
                ),
                mark_finished=True,
            )
            return summary
        except Exception as exc:
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
        rank_index: int,
        summary: SearchTaskExecutionSummary,
        result_page,
    ) -> None:
        self.task_repository.update_status(
            task.id,
            "running",
            current_step="提取候选人详情: {}".format(
                candidate_summary.name or candidate_summary.profile_url or rank_index
            ),
        )
        try:

            def _extract(page):
                detail_page = self.search_service.open_candidate_detail(
                    result_page, candidate_summary
                )
                try:
                    return self.resume_extractor.extract_candidate(
                        detail_page, candidate_summary
                    )
                finally:
                    self.search_service.close_detail_page(detail_page, result_page)

            browser_manager = self.search_service.browser_manager
            if hasattr(browser_manager, "run_with_page"):
                candidate = browser_manager.run_with_page(_extract)
            else:
                page = browser_manager.ensure_page()
                candidate = _extract(page)
            saved_candidate = self.candidate_repository.upsert_candidate(candidate)
            self.candidate_repository.add_source(
                candidate_id=saved_candidate.id,
                search_task_id=task.id,
                keyword=keyword,
                page_number=1,
                rank_index=rank_index,
            )
            summary.candidate_count += 1
        except Exception:
            failed_identifier = (
                candidate_summary.profile_url
                or candidate_summary.name
                or "candidate-{}".format(rank_index)
            )
            summary.failed_candidates.append(failed_identifier)
