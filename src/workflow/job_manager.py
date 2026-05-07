"""UI-independent background job manager for workflow API calls."""

from __future__ import annotations

import queue
import threading
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Optional, Set


class JobCategory(str, Enum):
    """Concurrency category for workflow jobs."""

    BROWSER = "browser"
    COMPUTE = "compute"


class JobStatus(str, Enum):
    """Observable lifecycle state for a workflow job."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class JobInfo:
    """Internal state for one submitted workflow job."""

    job_id: str
    name: str
    category: JobCategory
    target: Callable[["JobContext"], Any]
    status: JobStatus = JobStatus.PENDING
    progress_current: int = 0
    progress_total: int = 0
    progress_message: str = ""
    result: Any = None
    error_message: str = ""
    cancel_event: threading.Event = field(default_factory=threading.Event)


class JobContext:
    """Context object passed into job targets."""

    def __init__(self, manager: "JobManager", job: JobInfo):
        self._manager = manager
        self._job = job

    @property
    def job_id(self) -> str:
        return self._job.job_id

    @property
    def cancel_event(self) -> threading.Event:
        return self._job.cancel_event

    def report_progress(self, current: int, total: int, message: str = "") -> None:
        self._manager.update_progress(self.job_id, current, total, message)

    def raise_if_cancelled(self) -> None:
        if self.cancel_event.is_set():
            raise RuntimeError("用户已取消任务")


class JobManager:
    """Background scheduler with serial browser jobs and limited compute jobs."""

    DEFAULT_MAX_COMPUTE = 2

    def __init__(self, max_compute: int = DEFAULT_MAX_COMPUTE):
        self._max_compute = max(1, int(max_compute or self.DEFAULT_MAX_COMPUTE))
        self._queue: queue.Queue[Optional[JobInfo]] = queue.Queue()
        self._jobs: Dict[str, JobInfo] = {}
        self._lock = threading.Lock()
        self._running_browser: Optional[str] = None
        self._running_compute: Set[str] = set()
        self._scheduler_thread = threading.Thread(
            target=self._schedule_loop,
            name="WorkflowJobScheduler",
            daemon=True,
        )
        self._scheduler_thread.start()

    def submit(
        self,
        name: str,
        category: JobCategory,
        target: Callable[[JobContext], Any],
        job_id: Optional[str] = None,
    ) -> str:
        """Submit a background job and return its id."""
        resolved_id = job_id or uuid.uuid4().hex
        job = JobInfo(
            job_id=resolved_id,
            name=name,
            category=category,
            target=target,
        )
        with self._lock:
            self._jobs[resolved_id] = job
        self._queue.put(job)
        return resolved_id

    def get(self, job_id: str) -> Optional[JobInfo]:
        with self._lock:
            return self._jobs.get(job_id)

    def snapshot(self, job_id: str) -> Optional[dict]:
        """Return a JSON-serializable snapshot of one job."""
        job = self.get(job_id)
        if job is None:
            return None
        return {
            "job_id": job.job_id,
            "name": job.name,
            "category": job.category.value,
            "status": job.status.value,
            "progress_current": job.progress_current,
            "progress_total": job.progress_total,
            "progress_message": job.progress_message,
            "result": job.result,
            "error": job.error_message,
        }

    def list_snapshots(self) -> list:
        with self._lock:
            jobs = list(self._jobs.values())[::-1]
        return [self.snapshot(job.job_id) for job in jobs]

    def cancel(self, job_id: str) -> bool:
        job = self.get(job_id)
        if job is None:
            return False
        job.cancel_event.set()
        return True

    def update_progress(
        self, job_id: str, current: int, total: int, message: str = ""
    ) -> None:
        job = self.get(job_id)
        if job is None:
            return
        with self._lock:
            job.progress_current = int(current or 0)
            job.progress_total = int(total or 0)
            job.progress_message = message or ""

    def shutdown(self, wait_seconds: float = 5.0) -> None:
        with self._lock:
            for job in self._jobs.values():
                if job.status in (JobStatus.PENDING, JobStatus.RUNNING):
                    job.cancel_event.set()
            self._queue.put(None)
        self._scheduler_thread.join(timeout=wait_seconds)

    def _schedule_loop(self) -> None:
        while True:
            job = self._queue.get()
            if job is None:
                break

            while not self._can_run(job):
                threading.Event().wait(0.2)

            with self._lock:
                job.status = JobStatus.RUNNING
                if job.category == JobCategory.BROWSER:
                    self._running_browser = job.job_id
                else:
                    self._running_compute.add(job.job_id)

            worker = threading.Thread(
                target=self._run_job,
                args=(job,),
                name="WorkflowJob-{}".format(job.job_id[:8]),
                daemon=True,
            )
            worker.start()

    def _can_run(self, job: JobInfo) -> bool:
        with self._lock:
            if job.category == JobCategory.BROWSER:
                return self._running_browser is None
            return len(self._running_compute) < self._max_compute

    def _run_job(self, job: JobInfo) -> None:
        try:
            if job.cancel_event.is_set():
                raise RuntimeError("用户已取消任务")
            result = job.target(JobContext(self, job))
            with self._lock:
                if job.cancel_event.is_set():
                    job.status = JobStatus.CANCELLED
                    job.error_message = "用户已取消任务"
                else:
                    job.status = JobStatus.COMPLETED
                    job.result = result
        except Exception as exc:
            with self._lock:
                if job.cancel_event.is_set():
                    job.status = JobStatus.CANCELLED
                    job.error_message = "用户已取消任务"
                else:
                    job.status = JobStatus.FAILED
                    job.error_message = str(exc)
        finally:
            with self._lock:
                if job.category == JobCategory.BROWSER:
                    if self._running_browser == job.job_id:
                        self._running_browser = None
                else:
                    self._running_compute.discard(job.job_id)
