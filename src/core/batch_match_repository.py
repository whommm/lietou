"""Repository for batch match jobs and results."""

import uuid
from datetime import datetime
from typing import List, Optional

from .database import DatabaseManager
from ..models import BatchMatchJob, BatchMatchResult


class BatchMatchRepository:
    """Persist batch match jobs and candidate-level results."""

    def __init__(self, database: Optional[DatabaseManager] = None):
        self.database = database or DatabaseManager()

    @staticmethod
    def _now() -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def _build_job(row) -> BatchMatchJob:
        return BatchMatchJob(
            id=row["id"],
            job_history_id=row["job_history_id"],
            search_task_id=row["search_task_id"],
            candidate_count=row["candidate_count"],
            status=row["status"],
            created_at=row["created_at"],
            started_at=row["started_at"],
            finished_at=row["finished_at"],
            error_message=row["error_message"] or "",
        )

    @staticmethod
    def _build_result(row) -> BatchMatchResult:
        return BatchMatchResult(
            id=row["id"],
            batch_job_id=row["batch_job_id"],
            candidate_id=row["candidate_id"],
            score=row["score"],
            recommendation=row["recommendation"] or "",
            summary=row["summary"] or "",
            risks=row["risks"] or "",
            full_report_html=row["full_report_html"] or "",
            status=row["status"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def create_job(
        self,
        job_history_id: str,
        candidate_count: int,
        search_task_id: Optional[str] = None,
    ) -> BatchMatchJob:
        """Create and persist a batch match job."""
        job = BatchMatchJob(
            id=uuid.uuid4().hex,
            job_history_id=job_history_id,
            search_task_id=search_task_id,
            candidate_count=candidate_count,
            created_at=self._now(),
        )
        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT INTO batch_match_jobs (
                    id, job_history_id, search_task_id, candidate_count,
                    status, created_at, started_at, finished_at, error_message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job.id,
                    job.job_history_id,
                    job.search_task_id,
                    job.candidate_count,
                    job.status,
                    job.created_at,
                    job.started_at,
                    job.finished_at,
                    job.error_message,
                ),
            )
        return job

    def get_job(self, job_id: str) -> Optional[BatchMatchJob]:
        """Return a batch match job by id."""
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM batch_match_jobs WHERE id = ?", (job_id,)
            ).fetchone()
        return self._build_job(row) if row else None

    def update_job_status(
        self,
        job_id: str,
        status: str,
        error_message: str = "",
        mark_started: bool = False,
        mark_finished: bool = False,
    ) -> bool:
        """Update a batch job status and timestamps."""
        existing = self.get_job(job_id)
        if existing is None:
            return False

        started_at = existing.started_at
        finished_at = existing.finished_at
        if mark_started and not started_at:
            started_at = self._now()
        if mark_finished:
            finished_at = self._now()

        with self.database.connect() as connection:
            connection.execute(
                """
                UPDATE batch_match_jobs
                SET status = ?, error_message = ?, started_at = ?, finished_at = ?
                WHERE id = ?
                """,
                (status, error_message, started_at, finished_at, job_id),
            )
        return True

    def save_result(self, result: BatchMatchResult) -> BatchMatchResult:
        """Insert or update a candidate result in a batch job."""
        now = self._now()
        result.id = result.id or uuid.uuid4().hex
        result.created_at = result.created_at or now
        result.updated_at = now

        with self.database.connect() as connection:
            existing = connection.execute(
                "SELECT id FROM batch_match_results WHERE id = ?", (result.id,)
            ).fetchone()
            if existing:
                connection.execute(
                    """
                    UPDATE batch_match_results
                    SET batch_job_id = ?, candidate_id = ?, score = ?, recommendation = ?,
                        summary = ?, risks = ?, full_report_html = ?, status = ?,
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        result.batch_job_id,
                        result.candidate_id,
                        result.score,
                        result.recommendation,
                        result.summary,
                        result.risks,
                        result.full_report_html,
                        result.status,
                        result.updated_at,
                        result.id,
                    ),
                )
            else:
                connection.execute(
                    """
                    INSERT INTO batch_match_results (
                        id, batch_job_id, candidate_id, score, recommendation,
                        summary, risks, full_report_html, status, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        result.id,
                        result.batch_job_id,
                        result.candidate_id,
                        result.score,
                        result.recommendation,
                        result.summary,
                        result.risks,
                        result.full_report_html,
                        result.status,
                        result.created_at,
                        result.updated_at,
                    ),
                )
        return result

    def list_results(self, batch_job_id: str) -> List[BatchMatchResult]:
        """Return all results for a batch job ordered by score."""
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM batch_match_results
                WHERE batch_job_id = ?
                ORDER BY score DESC, updated_at DESC, id DESC
                """,
                (batch_job_id,),
            ).fetchall()
        return [self._build_result(row) for row in rows]

    def get_result(self, result_id: str) -> Optional[BatchMatchResult]:
        """Return one batch result by id."""
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM batch_match_results WHERE id = ?", (result_id,)
            ).fetchone()
        return self._build_result(row) if row else None
