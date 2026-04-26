"""Search task models for Liepin automation."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class SearchTask:
    """A persisted Liepin search task."""

    id: str
    job_history_id: str
    task_name: str
    keywords: Dict[str, Any] = field(default_factory=dict)
    search_mode: str = "keyword"
    max_pages: int = 1
    max_candidates: int = 20
    status: str = "pending"
    current_step: str = ""
    error_message: str = ""
    executed_queries_json: str = ""
    query_level_stats_json: str = ""
    search_control_snapshot_json: str = ""
    created_at: str = ""
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
