"""Repository for persisted analysis history records."""

from typing import TYPE_CHECKING, List, Optional

from .database import DatabaseManager

if TYPE_CHECKING:
    pass


class AnalysisHistoryRepository:
    """Persist and query job analysis-style history records in SQLite."""

    def __init__(self, database: Optional[DatabaseManager] = None):
        self.database = database or DatabaseManager()

    @staticmethod
    def _build_record(row):
        from .history import HistoryRecord

        return HistoryRecord(
            id=row["id"],
            title=row["title"],
            jd_text=row["jd_text"],
            result=row["result"],
            created_at=row["created_at"],
            record_type=row["record_type"],
            match_criteria_json=row["match_criteria_json"] or "",
            match_criteria_confirmed=bool(row["match_criteria_confirmed"]),
        )

    def upsert(self, record):
        with self.database.connect() as connection:
            existing = connection.execute(
                "SELECT id FROM analysis_history WHERE id = ?", (record.id,)
            ).fetchone()
            if existing:
                connection.execute(
                    """
                    UPDATE analysis_history
                    SET title = ?, jd_text = ?, result = ?, created_at = ?, record_type = ?,
                        match_criteria_json = ?, match_criteria_confirmed = ?
                    WHERE id = ?
                    """,
                    (
                        record.title,
                        record.jd_text,
                        record.result,
                        record.created_at,
                        record.record_type,
                        record.match_criteria_json,
                        1 if record.match_criteria_confirmed else 0,
                        record.id,
                    ),
                )
            else:
                connection.execute(
                    """
                    INSERT INTO analysis_history (
                        id, title, jd_text, result, created_at, record_type,
                        match_criteria_json, match_criteria_confirmed
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record.id,
                        record.title,
                        record.jd_text,
                        record.result,
                        record.created_at,
                        record.record_type,
                        record.match_criteria_json,
                        1 if record.match_criteria_confirmed else 0,
                    ),
                )
        return record

    def list_by_type(self, record_type: str) -> List[object]:
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM analysis_history
                WHERE record_type = ?
                ORDER BY created_at DESC, id DESC
                """,
                (record_type,),
            ).fetchall()
        return [self._build_record(row) for row in rows]

    def get_by_id(self, record_id: str):
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM analysis_history WHERE id = ?", (record_id,)
            ).fetchone()
        return self._build_record(row) if row else None

    def delete(self, record_id: str) -> bool:
        with self.database.connect() as connection:
            cursor = connection.execute(
                "DELETE FROM analysis_history WHERE id = ?", (record_id,)
            )
        return cursor.rowcount > 0

    def clear_by_type(self, record_type: str) -> bool:
        with self.database.connect() as connection:
            connection.execute(
                "DELETE FROM analysis_history WHERE record_type = ?", (record_type,)
            )
        return True
