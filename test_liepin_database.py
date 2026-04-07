import os

from src.core.database import DatabaseManager
from src.core.search_task_repository import SearchTaskRepository


def test_database_initializes_expected_tables(tmp_path):
    db_path = os.path.join(tmp_path, "test.db")
    manager = DatabaseManager(db_path=db_path)

    with manager.connect() as connection:
        rows = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()

    table_names = {row["name"] for row in rows}
    assert "search_tasks" in table_names
    assert "analysis_history" in table_names


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
