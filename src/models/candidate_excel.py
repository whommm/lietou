"""Excel-backed candidate workflow models."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class CandidateExcelRecord:
    """One candidate row stored inside the workbook."""

    row_index: int
    sequence: int
    name: str = ""
    age: str = ""
    page_number: Optional[int] = None
    rank_index: Optional[int] = None
    profile_url: str = ""
    capture_status: str = "待抓取"
    resume_text: str = ""
    match_score: Optional[int] = None
    match_detail: str = ""
    captured_at: str = ""
    matched_at: str = ""
