"""Repository for candidates and their source mappings."""

import uuid
from datetime import datetime
from typing import List, Optional

from .database import DatabaseManager
from ..models import Candidate, CandidateSource


class CandidateRepository:
    """Persist candidates and search-hit relationships."""

    def __init__(self, database: Optional[DatabaseManager] = None):
        self.database = database or DatabaseManager()

    @staticmethod
    def _now() -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def _build_candidate(row) -> Candidate:
        return Candidate(
            id=row["id"],
            platform=row["platform"],
            platform_candidate_id=row["platform_candidate_id"],
            profile_url=row["profile_url"],
            name=row["name"] or "",
            current_title=row["current_title"] or "",
            current_company=row["current_company"] or "",
            city=row["city"] or "",
            work_years=row["work_years"] or "",
            education=row["education"] or "",
            resume_text=row["resume_text"] or "",
            resume_summary=row["resume_summary"] or "",
            raw_payload_json=row["raw_payload_json"] or "",
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    @staticmethod
    def _build_source(row) -> CandidateSource:
        return CandidateSource(
            id=row["id"],
            candidate_id=row["candidate_id"],
            search_task_id=row["search_task_id"],
            keyword=row["keyword"],
            page_number=row["page_number"],
            rank_index=row["rank_index"],
            fetched_at=row["fetched_at"],
        )

    def upsert_candidate(self, candidate: Candidate) -> Candidate:
        """Insert a new candidate or update the existing one by profile URL."""
        now = self._now()
        with self.database.connect() as connection:
            existing = connection.execute(
                "SELECT * FROM candidates WHERE profile_url = ?",
                (candidate.profile_url,),
            ).fetchone()

            if existing:
                candidate_id = existing["id"]
                updated_resume_text = (
                    candidate.resume_text or existing["resume_text"] or ""
                )
                updated_resume_summary = (
                    candidate.resume_summary or existing["resume_summary"] or ""
                )
                updated_raw_payload = (
                    candidate.raw_payload_json or existing["raw_payload_json"] or ""
                )
                connection.execute(
                    """
                    UPDATE candidates
                    SET platform = ?, platform_candidate_id = ?, name = ?,
                        current_title = ?, current_company = ?, city = ?,
                        work_years = ?, education = ?, resume_text = ?,
                        resume_summary = ?, raw_payload_json = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        candidate.platform or existing["platform"],
                        candidate.platform_candidate_id
                        or existing["platform_candidate_id"],
                        candidate.name or existing["name"],
                        candidate.current_title or existing["current_title"],
                        candidate.current_company or existing["current_company"],
                        candidate.city or existing["city"],
                        candidate.work_years or existing["work_years"],
                        candidate.education or existing["education"],
                        updated_resume_text,
                        updated_resume_summary,
                        updated_raw_payload,
                        now,
                        candidate_id,
                    ),
                )
                return self.get_by_id(candidate_id)

            candidate.id = candidate.id or uuid.uuid4().hex
            candidate.created_at = candidate.created_at or now
            candidate.updated_at = now
            connection.execute(
                """
                INSERT INTO candidates (
                    id, platform, platform_candidate_id, profile_url, name,
                    current_title, current_company, city, work_years, education,
                    resume_text, resume_summary, raw_payload_json,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    candidate.id,
                    candidate.platform,
                    candidate.platform_candidate_id,
                    candidate.profile_url,
                    candidate.name,
                    candidate.current_title,
                    candidate.current_company,
                    candidate.city,
                    candidate.work_years,
                    candidate.education,
                    candidate.resume_text,
                    candidate.resume_summary,
                    candidate.raw_payload_json,
                    candidate.created_at,
                    candidate.updated_at,
                ),
            )
        return candidate

    def get_by_id(self, candidate_id: str) -> Optional[Candidate]:
        """Return a candidate by id."""
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM candidates WHERE id = ?", (candidate_id,)
            ).fetchone()
        return self._build_candidate(row) if row else None

    def get_by_profile_url(self, profile_url: str) -> Optional[Candidate]:
        """Return a candidate by profile url."""
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM candidates WHERE profile_url = ?", (profile_url,)
            ).fetchone()
        return self._build_candidate(row) if row else None

    def list_all(self) -> List[Candidate]:
        """Return all candidates, newest first."""
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM candidates ORDER BY updated_at DESC, id DESC"
            ).fetchall()
        return [self._build_candidate(row) for row in rows]

    def add_source(
        self,
        candidate_id: str,
        search_task_id: str,
        keyword: str,
        page_number: Optional[int] = None,
        rank_index: Optional[int] = None,
    ) -> CandidateSource:
        """Persist one search hit for a candidate."""
        source = CandidateSource(
            id=uuid.uuid4().hex,
            candidate_id=candidate_id,
            search_task_id=search_task_id,
            keyword=keyword,
            page_number=page_number,
            rank_index=rank_index,
            fetched_at=self._now(),
        )
        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT INTO candidate_sources (
                    id, candidate_id, search_task_id, keyword,
                    page_number, rank_index, fetched_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    source.id,
                    source.candidate_id,
                    source.search_task_id,
                    source.keyword,
                    source.page_number,
                    source.rank_index,
                    source.fetched_at,
                ),
            )
        return source

    def list_sources_for_candidate(self, candidate_id: str) -> List[CandidateSource]:
        """Return all source links for a candidate."""
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM candidate_sources
                WHERE candidate_id = ?
                ORDER BY fetched_at DESC, id DESC
                """,
                (candidate_id,),
            ).fetchall()
        return [self._build_source(row) for row in rows]

    def list_by_search_task(self, search_task_id: str) -> List[Candidate]:
        """Return distinct candidates linked to one search task."""
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT DISTINCT c.*
                FROM candidates c
                INNER JOIN candidate_sources cs ON cs.candidate_id = c.id
                WHERE cs.search_task_id = ?
                ORDER BY c.updated_at DESC, c.id DESC
                """,
                (search_task_id,),
            ).fetchall()
        return [self._build_candidate(row) for row in rows]
