"""SQLite bootstrap for Liepin automation features."""

import os
import sqlite3
import sys
from contextlib import contextmanager
from typing import Iterator, Optional


class DatabaseManager:
    """Manage the SQLite database for new automation features."""

    DEFAULT_DB_NAME = "liepin_workbench.db"

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or self._get_default_db_path()
        self.initialize()

    def _get_default_db_path(self) -> str:
        """Return the default database location in the project root."""
        if getattr(sys, "frozen", False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
        return os.path.join(base_dir, self.DEFAULT_DB_NAME)

    def get_connection(self) -> sqlite3.Connection:
        """Create a configured SQLite connection."""
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        """Provide a transactional SQLite connection."""
        connection = self.get_connection()
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        """Create all tables required by new automation features."""
        with self.connect() as connection:
            cursor = connection.cursor()
            cursor.executescript(
                """
                CREATE TABLE IF NOT EXISTS search_tasks (
                    id TEXT PRIMARY KEY,
                    job_history_id TEXT NOT NULL,
                    task_name TEXT NOT NULL,
                    keywords_json TEXT NOT NULL,
                    search_mode TEXT NOT NULL,
                    max_pages INTEGER NOT NULL,
                    max_candidates INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    current_step TEXT,
                    error_message TEXT,
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    finished_at TEXT
                );

                CREATE TABLE IF NOT EXISTS candidates (
                    id TEXT PRIMARY KEY,
                    platform TEXT NOT NULL,
                    platform_candidate_id TEXT,
                    profile_url TEXT NOT NULL,
                    name TEXT,
                    current_title TEXT,
                    current_company TEXT,
                    city TEXT,
                    work_years TEXT,
                    education TEXT,
                    resume_text TEXT,
                    resume_summary TEXT,
                    raw_payload_json TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE UNIQUE INDEX IF NOT EXISTS idx_candidates_profile_url
                ON candidates(profile_url);

                CREATE INDEX IF NOT EXISTS idx_candidates_name
                ON candidates(name);

                CREATE INDEX IF NOT EXISTS idx_candidates_company
                ON candidates(current_company);

                CREATE TABLE IF NOT EXISTS candidate_sources (
                    id TEXT PRIMARY KEY,
                    candidate_id TEXT NOT NULL,
                    search_task_id TEXT NOT NULL,
                    keyword TEXT NOT NULL,
                    page_number INTEGER,
                    rank_index INTEGER,
                    fetched_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS batch_match_jobs (
                    id TEXT PRIMARY KEY,
                    job_history_id TEXT NOT NULL,
                    search_task_id TEXT,
                    candidate_count INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    finished_at TEXT,
                    error_message TEXT
                );

                CREATE TABLE IF NOT EXISTS batch_match_results (
                    id TEXT PRIMARY KEY,
                    batch_job_id TEXT NOT NULL,
                    candidate_id TEXT NOT NULL,
                    score INTEGER,
                    recommendation TEXT,
                    summary TEXT,
                    risks TEXT,
                    full_report_html TEXT,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_batch_match_results_job
                ON batch_match_results(batch_job_id);

                CREATE INDEX IF NOT EXISTS idx_batch_match_results_candidate
                ON batch_match_results(candidate_id);
                """
            )
