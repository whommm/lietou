"""Generic background task queue with category-based concurrency control."""

import queue
import threading
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Dict, Optional, Set


class TaskCategory(Enum):
    BROWSER = "browser"
    COMPUTE = "compute"


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TaskInfo:
    task_id: str
    name: str
    category: TaskCategory
    target: Callable
    args: tuple
    kwargs: dict
    status: TaskStatus = TaskStatus.PENDING
    progress_current: int = 0
    progress_total: int = 0
    progress_message: str = ""
    error_message: str = ""
    cancel_event: threading.Event = field(default_factory=threading.Event)
    on_update: Optional[Callable[["TaskInfo"], None]] = None
    on_complete: Optional[Callable[["TaskInfo"], None]] = None


class TaskQueue:
    """Background task scheduler with per-category concurrency limits.

    - BROWSER tasks run strictly one-at-a-time because Playwright uses a
      single worker thread.
    - COMPUTE tasks run up to ``max_compute`` concurrently.
    """

    DEFAULT_MAX_COMPUTE = 2

    def __init__(self, master_widget, max_compute: int = DEFAULT_MAX_COMPUTE):
        self.master = master_widget
        self._max_compute = max(1, max_compute)
        self._task_queue: queue.Queue[TaskInfo] = queue.Queue()
        self._tasks: Dict[str, TaskInfo] = {}
        self._lock = threading.Lock()
        self._running_browser: Optional[str] = None
        self._running_compute: Set[str] = set()
        self._scheduler_thread = threading.Thread(target=self._schedule_loop, daemon=True)
        self._scheduler_thread.start()

    def submit(
        self,
        name: str,
        category: TaskCategory,
        target: Callable,
        args: tuple = (),
        kwargs: Optional[dict] = None,
        task_id: Optional[str] = None,
        on_update: Optional[Callable[[TaskInfo], None]] = None,
        on_complete: Optional[Callable[[TaskInfo], None]] = None,
    ) -> str:
        """Enqueue a new background task and return its id."""
        tid = task_id or str(uuid.uuid4())
        task = TaskInfo(
            task_id=tid,
            name=name,
            category=category,
            target=target,
            args=args,
            kwargs=kwargs or {},
            on_update=on_update,
            on_complete=on_complete,
        )
        with self._lock:
            self._tasks[tid] = task
        self._task_queue.put(task)
        return tid

    def get_task(self, task_id: str) -> Optional[TaskInfo]:
        with self._lock:
            return self._tasks.get(task_id)

    def list_tasks(self) -> list:
        """Return a snapshot of all tasks, newest first."""
        with self._lock:
            return list(self._tasks.values())[::-1]

    def cancel_task(self, task_id: str) -> bool:
        """Request cancellation of a task."""
        task = self.get_task(task_id)
        if task is None:
            return False
        task.cancel_event.set()
        return True

    def update_progress(self, task_id: str, current: int, total: int, message: str = ""):
        """Call from inside the worker to report progress."""
        task = self.get_task(task_id)
        if task is None:
            return
        task.progress_current = current
        task.progress_total = total
        task.progress_message = message
        if task.on_update:
            self._safe_ui_callback(task.on_update, task)

    def _safe_ui_callback(self, callback: Callable, *args):
        """Marshal a callback to the Tkinter main thread safely."""
        try:
            if self.master.winfo_exists():
                self.master.after(0, lambda: callback(*args))
        except Exception:
            # Tkinter already destroyed or similar
            pass

    def _schedule_loop(self):
        while True:
            task = self._task_queue.get()
            if task is None:
                break

            # Wait until concurrency slot is available
            while True:
                with self._lock:
                    can_run = False
                    if task.category == TaskCategory.BROWSER:
                        can_run = self._running_browser is None
                    else:
                        can_run = len(self._running_compute) < self._max_compute

                if can_run:
                    break
                # Back off briefly so we don't spin the CPU
                threading.Event().wait(0.2)

            with self._lock:
                task.status = TaskStatus.RUNNING
                if task.category == TaskCategory.BROWSER:
                    self._running_browser = task.task_id
                else:
                    self._running_compute.add(task.task_id)

            # Launch worker thread
            worker = threading.Thread(
                target=self._run_task,
                args=(task,),
                daemon=True,
            )
            worker.start()

    def _run_task(self, task: TaskInfo):
        """Execute the task target and handle completion / cancellation."""
        try:
            if task.cancel_event.is_set():
                raise RuntimeError("用户已取消任务")
            task.target(task.task_id, task.cancel_event, task, *task.args, **task.kwargs)
            if task.cancel_event.is_set():
                task.status = TaskStatus.CANCELLED
            else:
                task.status = TaskStatus.COMPLETED
        except Exception as exc:
            if task.cancel_event.is_set():
                task.status = TaskStatus.CANCELLED
                task.error_message = "用户已取消任务"
            else:
                task.status = TaskStatus.FAILED
                task.error_message = str(exc)
        finally:
            with self._lock:
                if task.category == TaskCategory.BROWSER:
                    if self._running_browser == task.task_id:
                        self._running_browser = None
                else:
                    self._running_compute.discard(task.task_id)

            if task.on_complete:
                self._safe_ui_callback(task.on_complete, task)

    def shutdown(self, wait_seconds: float = 5.0):
        """Cancel all running tasks and stop the scheduler."""
        with self._lock:
            for task in self._tasks.values():
                if task.status in (TaskStatus.PENDING, TaskStatus.RUNNING):
                    task.cancel_event.set()
            self._task_queue.put(None)
        self._scheduler_thread.join(timeout=wait_seconds)
