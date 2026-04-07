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

                CREATE TABLE IF NOT EXISTS analysis_history (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    jd_text TEXT NOT NULL,
                    result TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    record_type TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_analysis_history_type
                ON analysis_history(record_type, created_at DESC);
                """
            )
