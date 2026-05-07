import time

from src.workflow import JobCategory, JobManager


def wait_for_job(manager: JobManager, job_id: str, timeout: float = 3.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        snapshot = manager.snapshot(job_id)
        if snapshot and snapshot["status"] in ("completed", "failed", "cancelled"):
            return snapshot
        time.sleep(0.05)
    raise AssertionError("job did not finish")


def test_job_manager_runs_compute_job_and_reports_progress():
    manager = JobManager(max_compute=1)

    def target(context):
        context.report_progress(1, 2, "half")
        context.report_progress(2, 2, "done")
        return {"ok": True}

    job_id = manager.submit("demo", JobCategory.COMPUTE, target)
    snapshot = wait_for_job(manager, job_id)

    assert snapshot["status"] == "completed"
    assert snapshot["progress_current"] == 2
    assert snapshot["progress_total"] == 2
    assert snapshot["progress_message"] == "done"
    assert snapshot["result"] == {"ok": True}

    manager.shutdown()


def test_browser_jobs_run_serially():
    manager = JobManager(max_compute=2)
    events = []

    def first(context):
        events.append("first-start")
        time.sleep(0.15)
        events.append("first-end")
        return "first"

    def second(context):
        events.append("second-start")
        return "second"

    first_id = manager.submit("first", JobCategory.BROWSER, first)
    second_id = manager.submit("second", JobCategory.BROWSER, second)

    first_snapshot = wait_for_job(manager, first_id)
    second_snapshot = wait_for_job(manager, second_id)

    assert first_snapshot["status"] == "completed"
    assert second_snapshot["status"] == "completed"
    assert events == ["first-start", "first-end", "second-start"]

    manager.shutdown()
