"""Batch match models for Liepin automation."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class BatchMatchJob:
    """A batch match job for one position and a candidate set."""

    id: str
    job_history_id: str
    search_task_id: Optional[str] = None
    candidate_count: int = 0
    status: str = "pending"
    created_at: str = ""
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    error_message: str = ""


@dataclass
class BatchMatchResult:
    """A single candidate result within a batch match job."""

    id: str
    batch_job_id: str
    candidate_id: str
    score: Optional[int] = None
    tier: Optional[str] = None
    core_met_count: int = 0
    core_total: int = 0
    dealbreaker_hit: bool = False
    recommendation: str = ""
    summary: str = ""
    risks: str = ""
    detail: str = ""
    status: str = "pending"
    created_at: str = ""
    updated_at: str = ""


@dataclass
class BatchMatchJobCandidate:
    """Snapshot entry linking a batch match job to one candidate."""

    id: str
    batch_job_id: str
    candidate_id: str
    snapshot_order: int
    created_at: str = ""
