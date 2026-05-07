import json

from src.core.config import ConfigManager
from src.core.database import DatabaseManager
from src.core.workflow_facade import WorkflowFacade
from src.workflow import JobManager


def test_workflow_facade_generates_fallback_search_strategy_without_ui(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text("{}", encoding="utf-8")
    db_path = tmp_path / "workflow.db"
    history_path = tmp_path / "history_job_analysis.json"

    facade = WorkflowFacade(
        config_manager=ConfigManager(str(config_path)),
        database_manager=DatabaseManager(str(db_path)),
        job_manager=JobManager(),
        workspace_root=str(tmp_path),
        history_path=str(history_path),
    )
    analysis_html = """
    <script type="application/json" data-search-intent="true">
    {
      "direct_keywords": ["产品"],
      "domain_terms": ["文创", "潮玩"],
      "recommended_rounds": [
        {"query": "文创 潮玩", "position_filter": "产品"}
      ]
    }
    </script>
    """
    record = facade.job_history_manager.save_record(
        "岗位名称：文创产品经理\n深圳，本科，5年以上经验",
        analysis_html,
    )

    result = facade.generate_search_strategy(record.id)

    assert result["record_id"] == record.id
    assert result["warning"]
    assert result["strategy"]["executable_rounds"][0]["query"] == "文创 潮玩"
    assert result["strategy"]["filters"]["目前城市"][0] == "深圳"

    persisted = facade.job_history_manager.get_by_id(record.id)
    payload = json.loads(persisted.search_strategy_json)
    assert payload["executable_rounds"][0]["position_filter"] == "产品"

    facade.job_manager.shutdown()
