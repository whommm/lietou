"""Tests for the background task queue."""

import threading
import time

import pytest

from src.core.task_queue import TaskCategory, TaskQueue, TaskStatus


class _FakeMaster:
    def __init__(self):
        self._alive = True

    def winfo_exists(self):
        return self._alive

    def after(self, _delay, callback, *args):
        callback(*args)


def _noop_task(task_id, cancel_event, task_info):
    time.sleep(0.05)


def _slow_task(task_id, cancel_event, task_info):
    for i in range(5):
        if cancel_event.is_set():
            raise RuntimeError("cancelled")
        time.sleep(0.05)


def test_submit_and_complete():
    master = _FakeMaster()
    queue = TaskQueue(master, max_compute=2)
    completed = threading.Event()
    result_task = {}

    def on_complete(task):
        result_task["id"] = task.task_id
        result_task["status"] = task.status
        completed.set()

    tid = queue.submit(
        name="test",
        category=TaskCategory.COMPUTE,
        target=_noop_task,
        on_complete=on_complete,
    )

    assert tid is not None
    task = queue.get_task(tid)
    assert task.status == TaskStatus.PENDING

    completed.wait(timeout=2.0)
    assert result_task["id"] == tid
    assert result_task["status"] == TaskStatus.COMPLETED

    queue.shutdown(wait_seconds=1.0)


def test_browser_tasks_run_serially():
    master = _FakeMaster()
    queue = TaskQueue(master, max_compute=2)
    running = threading.Lock()
    max_concurrent = [0]
    current_concurrent = [0]
    events = [threading.Event(), threading.Event()]
    call_count = [0]

    def tracked_task(task_id, cancel_event, task_info):
        idx = call_count[0]
        call_count[0] += 1
        with running:
            current_concurrent[0] += 1
            max_concurrent[0] = max(max_concurrent[0], current_concurrent[0])
            time.sleep(0.1)
            current_concurrent[0] -= 1
        events[idx].set()

    t1 = queue.submit("b1", TaskCategory.BROWSER, tracked_task)
    t2 = queue.submit("b2", TaskCategory.BROWSER, tracked_task)

    events[0].wait(timeout=2.0)
    events[1].wait(timeout=2.0)
    assert max_concurrent[0] == 1
    assert queue.get_task(t1).status == TaskStatus.COMPLETED
    assert queue.get_task(t2).status == TaskStatus.COMPLETED

    queue.shutdown(wait_seconds=1.0)


def test_compute_tasks_respect_limit():
    master = _FakeMaster()
    queue = TaskQueue(master, max_compute=2)
    running = threading.Lock()
    max_concurrent = [0]
    current_concurrent = [0]

    def tracked_task(task_id, cancel_event, task_info):
        with running:
            current_concurrent[0] += 1
            max_concurrent[0] = max(max_concurrent[0], current_concurrent[0])
            time.sleep(0.15)
            current_concurrent[0] -= 1

    t1 = queue.submit("c1", TaskCategory.COMPUTE, tracked_task)
    t2 = queue.submit("c2", TaskCategory.COMPUTE, tracked_task)
    t3 = queue.submit("c3", TaskCategory.COMPUTE, tracked_task)

    time.sleep(0.1)
    # At this point at most 2 should be running
    assert max_concurrent[0] <= 2

    time.sleep(0.5)
    assert queue.get_task(t1).status == TaskStatus.COMPLETED
    assert queue.get_task(t2).status == TaskStatus.COMPLETED
    assert queue.get_task(t3).status == TaskStatus.COMPLETED

    queue.shutdown(wait_seconds=1.0)


def test_cancel_task():
    master = _FakeMaster()
    queue = TaskQueue(master, max_compute=2)
    completed = threading.Event()
    result_task = {}

    def on_complete(task):
        result_task["status"] = task.status
        completed.set()

    tid = queue.submit(
        name="slow",
        category=TaskCategory.COMPUTE,
        target=_slow_task,
        on_complete=on_complete,
    )

    time.sleep(0.05)
    queue.cancel_task(tid)

    completed.wait(timeout=2.0)
    assert result_task["status"] == TaskStatus.CANCELLED

    queue.shutdown(wait_seconds=1.0)


def test_progress_callback():
    master = _FakeMaster()
    queue = TaskQueue(master, max_compute=2)
    updates = []

    def target(task_id, cancel_event, task_info):
        queue.update_progress(task_id, 1, 3, "step1")
        queue.update_progress(task_id, 2, 3, "step2")

    def on_update(task):
        updates.append((task.progress_current, task.progress_total, task.progress_message))

    tid = queue.submit(
        name="prog",
        category=TaskCategory.COMPUTE,
        target=target,
        on_update=on_update,
    )

    time.sleep(0.2)
    assert queue.get_task(tid).status == TaskStatus.COMPLETED
    # Filter to unique progress tuples
    unique = list(dict.fromkeys(updates))
    assert any(u[2] == "step1" for u in unique)
    assert any(u[2] == "step2" for u in unique)

    queue.shutdown(wait_seconds=1.0)
