"""FastAPI app exposing the local workflow tools for external agents."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .schemas import (
    AnalyzeJDRequest,
    BatchMatchRequest,
    GreetingRequest,
    LiepinCaptureRequest,
    RecordRequest,
    SearchStrategyRequest,
)
from ..core.workflow_facade import WorkflowError, WorkflowFacade


app = FastAPI(
    title="Liepin Workflow API",
    version="0.1.0",
    description="Local API for agent-driven Liepin workflow execution.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1", "http://localhost"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

facade = WorkflowFacade()


def _call(action):
    try:
        return action()
    except WorkflowError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/health")
def health():
    return _call(facade.health)


@app.post("/api/tools/analyze_jd")
def analyze_jd(request: AnalyzeJDRequest):
    return _call(lambda: facade.analyze_jd(request.jd_text, request.company_context))


@app.post("/api/tools/generate_match_criteria")
def generate_match_criteria(request: RecordRequest):
    return _call(lambda: facade.generate_match_criteria(request.record_id))


@app.post("/api/tools/generate_search_strategy")
def generate_search_strategy(request: SearchStrategyRequest):
    return _call(
        lambda: facade.generate_search_strategy(
            request.record_id,
            override_prompt_hint=request.override_prompt_hint,
        )
    )


@app.post("/api/tools/run_liepin_capture")
def run_liepin_capture(request: LiepinCaptureRequest):
    return _call(
        lambda: facade.start_liepin_capture(
            record_id=request.record_id,
            strategy=request.strategy,
            filters=request.filters,
            max_pages=request.max_pages,
            max_candidates=request.max_candidates,
            per_round_limit=request.per_round_limit,
        )
    )


@app.post("/api/tools/batch_match_candidates")
def batch_match_candidates(request: BatchMatchRequest):
    return _call(
        lambda: facade.start_batch_match_candidates(
            record_id=request.record_id,
            excel_path=request.excel_path,
            row_indexes=request.row_indexes,
            max_workers=request.max_workers,
        )
    )


@app.post("/api/tools/generate_greeting_text")
def generate_greeting_text(request: GreetingRequest):
    return _call(lambda: facade.generate_greeting_text(request.record_id, request.style))


@app.get("/api/jobs")
def list_jobs():
    return facade.list_jobs()


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str):
    snapshot = facade.get_job(job_id)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    return snapshot


@app.post("/api/jobs/{job_id}/cancel")
def cancel_job(job_id: str):
    if not facade.cancel_job(job_id):
        raise HTTPException(status_code=404, detail="任务不存在")
    return {"job_id": job_id, "cancel_requested": True}


def main() -> None:
    import uvicorn

    uvicorn.run(
        "src.api.app:app",
        host="127.0.0.1",
        port=8765,
        reload=False,
    )


if __name__ == "__main__":
    main()
