"""Request schemas for the local workflow API."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AnalyzeJDRequest(BaseModel):
    jd_text: str
    company_context: str = ""


class RecordRequest(BaseModel):
    record_id: str


class SearchStrategyRequest(BaseModel):
    record_id: str
    override_prompt_hint: str = ""


class LiepinCaptureRequest(BaseModel):
    record_id: str
    strategy: Optional[Dict[str, Any]] = None
    filters: Optional[Dict[str, Any]] = None
    max_pages: int = Field(default=1, ge=1, le=20)
    max_candidates: int = Field(default=30, ge=1, le=500)
    per_round_limit: int = Field(default=30, ge=1, le=200)


class BatchMatchRequest(BaseModel):
    record_id: str
    excel_path: str
    row_indexes: Optional[List[int]] = None
    max_workers: int = Field(default=5, ge=1, le=10)


class GreetingRequest(BaseModel):
    record_id: str
    style: str = "general"
