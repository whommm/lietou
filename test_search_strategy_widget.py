from src.ui.search_strategy_widget import SearchStrategyWidget


def test_search_strategy_widget_renders_and_parses_rounds():
    rounds = [
        {
            "query": "文创 潮玩",
            "position_filter": "产品",
            "intent": "命中文创潮玩产品背景",
            "match_mode": "all",
            "scope": "全部经历",
        }
    ]

    text = SearchStrategyWidget._build_round_text(rounds)
    parsed = SearchStrategyWidget._parse_round_text(text, rounds)

    assert "搜索栏：文创 潮玩" in text
    assert "职位栏：产品" in text
    assert parsed[0]["query"] == "文创 潮玩"
    assert parsed[0]["position_filter"] == "产品"
    assert parsed[0]["intent"] == "命中文创潮玩产品背景"


def test_search_strategy_widget_meta_defaults_activity_to_recent_week():
    text = SearchStrategyWidget._build_meta_text({"工作年限": "5年以上", "教育经历": "大专"})

    assert "活跃度：近一周" in text
    assert "每轮人数：最多 30 人" in text
