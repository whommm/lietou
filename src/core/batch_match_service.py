"""Batch match orchestration service."""

import re
from typing import Iterable, List, Optional

from .batch_match_repository import BatchMatchRepository
from .llm_client import LLMClient
from .prompt import RESUME_MATCH_PROMPT
from ..models import BatchMatchJob, BatchMatchResult, Candidate


class BatchMatchService:
    """Coordinate batch match jobs over stored candidates.

    This service intentionally starts as a thin orchestration layer so the data
    flow is fixed early. Later phases can add progress callbacks, cancellation,
    retries, and partial resume without changing its public contract.
    """

    def __init__(
        self,
        repository: BatchMatchRepository,
        llm_client: Optional[LLMClient] = None,
    ):
        self.repository = repository
        self.llm_client = llm_client

    SCORE_PATTERN = re.compile(r"(\d{1,3})%")
    ACTION_PATTERN = re.compile(r"建议动作：</strong>\s*([^<]+)")
    SUMMARY_PATTERN = re.compile(r"一句话结论：</strong>\s*([^<]+)")
    RISKS_PATTERN = re.compile(r"明确短板：</strong>\s*([^<]+)")

    def create_job(
        self,
        job_history_id: str,
        candidates: Iterable[Candidate],
        search_task_id: Optional[str] = None,
    ) -> BatchMatchJob:
        """Create a persisted batch job for the provided candidate set."""
        candidate_list = list(candidates)
        return self.repository.create_job(
            job_history_id=job_history_id,
            search_task_id=search_task_id,
            candidate_count=len(candidate_list),
        )

    def run_job(
        self,
        batch_job: BatchMatchJob,
        job_description: str,
        candidates: Iterable[Candidate],
    ) -> List[BatchMatchResult]:
        """Run matching for all candidates in sequence."""
        if self.llm_client is None:
            raise RuntimeError("BatchMatchService requires an LLM client to run jobs")

        self.repository.update_job_status(batch_job.id, "running", mark_started=True)
        results = []
        try:
            for candidate in candidates:
                result = self._match_candidate(batch_job.id, job_description, candidate)
                results.append(self.repository.save_result(result))
            self.repository.update_job_status(
                batch_job.id, "completed", mark_finished=True
            )
            return results
        except Exception as exc:
            self.repository.update_job_status(
                batch_job.id,
                "failed",
                error_message=str(exc),
                mark_finished=True,
            )
            raise

    def _match_candidate(
        self, batch_job_id: str, job_description: str, candidate: Candidate
    ) -> BatchMatchResult:
        """Generate a full match report for one candidate."""
        prompt = RESUME_MATCH_PROMPT.format(
            job_description=job_description,
            resume=candidate.resume_text,
        )
        report_html = self.llm_client.chat(prompt)
        parsed = self._parse_report(report_html)
        return BatchMatchResult(
            id="",
            batch_job_id=batch_job_id,
            candidate_id=candidate.id,
            score=parsed["score"],
            recommendation=parsed["recommendation"],
            summary=parsed["summary"],
            risks=parsed["risks"],
            full_report_html=report_html,
            status="completed",
        )

    def _parse_report(self, report_html: str) -> dict:
        """Extract batch list fields from the detailed HTML report."""
        score_match = self.SCORE_PATTERN.search(report_html or "")
        action_match = self.ACTION_PATTERN.search(report_html or "")
        summary_match = self.SUMMARY_PATTERN.search(report_html or "")
        risks_match = self.RISKS_PATTERN.search(report_html or "")

        score = None
        if score_match:
            try:
                score = max(0, min(100, int(score_match.group(1))))
            except ValueError:
                score = None

        recommendation = (action_match.group(1).strip() if action_match else "").strip()
        summary = (summary_match.group(1).strip() if summary_match else "").strip()
        risks = (risks_match.group(1).strip() if risks_match else "").strip()

        return {
            "score": score,
            "recommendation": recommendation,
            "summary": summary,
            "risks": risks,
        }
