from src.core.history import HistoryManager


def test_history_manager_save_and_get_all(tmp_path):
    manager = HistoryManager(
        record_type="job_analysis",
        history_path=str(tmp_path / "history_job_analysis.json"),
        db_path=str(tmp_path / "history.db"),
    )

    saved = manager.save_record(
        "岗位名称：算法工程师", "<p><strong>岗位名称：</strong>算法工程师</p>"
    )
    records = manager.get_all()

    assert saved.title == "算法工程师"
    assert len(records) == 1
    assert records[0].id == saved.id


def test_history_manager_delete_and_clear(tmp_path):
    manager = HistoryManager(
        record_type="resume_match",
        history_path=str(tmp_path / "history_resume_match.json"),
        db_path=str(tmp_path / "history.db"),
    )

    first = manager.save_record("岗位: 后端工程师", "匹配结果一")
    second = manager.save_record("岗位: 产品经理", "匹配结果二")

    assert manager.delete(first.id) is True
    assert manager.get_by_id(first.id) is None

    assert manager.clear() is True
    assert manager.get_all() == []
    assert manager.get_by_id(second.id) is None
