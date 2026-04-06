"""Repository for persisted Liepin search tasks."""

import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from .database import DatabaseManager
from ..models import SearchTask


class SearchTaskRepository:
    """Persist and query Liepin search tasks."""

    def __init__(self, database: Optional[DatabaseManager] = None):
        self.database = database or DatabaseManager()

    @staticmethod
    def _now() -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def _build_task(row) -> SearchTask:
        return SearchTask(
            id=row["id"],
            job_history_id=row["job_history_id"],
            task_name=row["task_name"],
            keywords=json.loads(row["keywords_json"]),
            search_mode=row["search_mode"],
            max_pages=row["max_pages"],
            max_candidates=row["max_candidates"],
            status=row["status"],
            current_step=row["current_step"] or "",
            error_message=row["error_message"] or "",
            created_at=row["created_at"],
            started_at=row["started_at"],
            finished_at=row["finished_at"],
        )

    def create(
        self,
        job_history_id: str,
        task_name: str,
        keywords: Dict[str, List[str]],
        search_mode: str = "keyword",
        max_pages: int = 1,
        max_candidates: int = 20,
    ) -> SearchTask:
        """Create and persist a search task."""
        task = SearchTask(
            id=uuid.uuid4().hex,
            job_history_id=job_history_id,
            task_name=task_name,
            keywords=keywords,
            search_mode=search_mode,
            max_pages=max_pages,
            max_candidates=max_candidates,
            created_at=self._now(),
        )
        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT INTO search_tasks (
                    id, job_history_id, task_name, keywords_json, search_mode,
                    max_pages, max_candidates, status, current_step,
                    error_message, created_at, started_at, finished_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task.id,
                    task.job_history_id,
                    task.task_name,
                    json.dumps(task.keywords, ensure_ascii=False),
                    task.search_mode,
                    task.max_pages,
                    task.max_candidates,
                    task.status,
                    task.current_step,
                    task.error_message,
                    task.created_at,
                    task.started_at,
                    task.finished_at,
                ),
            )
        return task

    def get_by_id(self, task_id: str) -> Optional[SearchTask]:
        """Return a search task by id."""
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM search_tasks WHERE id = ?", (task_id,)
            ).fetchone()
        return self._build_task(row) if row else None

    def list_all(self) -> List[SearchTask]:
        """Return all search tasks, newest first."""
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM search_tasks ORDER BY created_at DESC, id DESC"
            ).fetchall()
        return [self._build_task(row) for row in rows]

    def update_status(
        self,
        task_id: str,
        status: str,
        current_step: str = "",
        error_message: str = "",
        mark_started: bool = False,
        mark_finished: bool = False,
    ) -> bool:
        """Update a task status and lifecycle timestamps."""
        existing = self.get_by_id(task_id)
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
                UPDATE search_tasks
                SET status = ?, current_step = ?, error_message = ?,
                    started_at = ?, finished_at = ?
                WHERE id = ?
                """,
                (status, current_step, error_message, started_at, finished_at, task_id),
            )
        return True
