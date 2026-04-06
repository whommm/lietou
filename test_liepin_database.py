import os

from src.core.batch_match_repository import BatchMatchRepository
from src.core.candidate_repository import CandidateRepository
from src.core.database import DatabaseManager
from src.core.search_task_repository import SearchTaskRepository
from src.models import BatchMatchResult, Candidate


def test_database_initializes_expected_tables(tmp_path):
    db_path = os.path.join(tmp_path, "test.db")
    manager = DatabaseManager(db_path=db_path)

    with manager.connect() as connection:
        rows = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()

    table_names = {row["name"] for row in rows}
    assert "search_tasks" in table_names
    assert "candidates" in table_names
    assert "candidate_sources" in table_names
    assert "batch_match_jobs" in table_names
    assert "batch_match_results" in table_names


def test_search_task_repository_round_trip(tmp_path):
    manager = DatabaseManager(db_path=os.path.join(tmp_path, "test.db"))
    repository = SearchTaskRepository(manager)

    created = repository.create(
        job_history_id="job_001",
        task_name="算法岗搜索",
        keywords={"precise_keywords": ["算法工程师", "推荐系统"]},
        max_pages=3,
        max_candidates=50,
    )

    loaded = repository.get_by_id(created.id)

    assert loaded is not None
    assert loaded.task_name == "算法岗搜索"
    assert loaded.keywords["precise_keywords"] == ["算法工程师", "推荐系统"]
    assert loaded.max_pages == 3
    assert loaded.max_candidates == 50


def test_candidate_repository_upserts_by_profile_url_and_tracks_sources(tmp_path):
    manager = DatabaseManager(db_path=os.path.join(tmp_path, "test.db"))
    repository = CandidateRepository(manager)

    first = repository.upsert_candidate(
        Candidate(
            id="",
            profile_url="https://example.com/candidate/1",
            name="张三",
            current_company="字节跳动",
            resume_text="第一版简历",
        )
    )
    second = repository.upsert_candidate(
        Candidate(
            id="",
            profile_url="https://example.com/candidate/1",
            name="张三",
            current_company="字节跳动",
            resume_text="",
            resume_summary="更新后的摘要",
        )
    )

    repository.add_source(
        candidate_id=second.id,
        search_task_id="task_001",
        keyword="算法工程师",
        page_number=1,
        rank_index=2,
    )

    all_candidates = repository.list_all()
    sources = repository.list_sources_for_candidate(second.id)

    assert len(all_candidates) == 1
    assert first.id == second.id
    assert all_candidates[0].resume_text == "第一版简历"
    assert all_candidates[0].resume_summary == "更新后的摘要"
    assert len(sources) == 1
    assert sources[0].keyword == "算法工程师"


def test_batch_match_repository_persists_job_and_results(tmp_path):
    manager = DatabaseManager(db_path=os.path.join(tmp_path, "test.db"))
    repository = BatchMatchRepository(manager)

    job = repository.create_job(
        job_history_id="job_001", candidate_count=2, search_task_id="task_001"
    )
    repository.update_job_status(job.id, "running", mark_started=True)
    repository.save_result(
        BatchMatchResult(
            id="",
            batch_job_id=job.id,
            candidate_id="candidate_001",
            score=88,
            recommendation="strong_recommend",
            summary="高度匹配",
            risks="无明显硬伤",
            full_report_html="<div>ok</div>",
            status="completed",
        )
    )

    loaded_job = repository.get_job(job.id)
    results = repository.list_results(job.id)

    assert loaded_job is not None
    assert loaded_job.status == "running"
    assert len(results) == 1
    assert results[0].score == 88
    assert results[0].recommendation == "strong_recommend"
