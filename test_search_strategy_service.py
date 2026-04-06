from src.core.search_strategy_service import SearchStrategyService


def test_build_from_analysis_result_extracts_copy_links():
    service = SearchStrategyService()

    strategy = service.build_from_analysis_result(
        '<a href="copy://算法工程师">算法工程师</a>'
        '<a href="copy://推荐系统">推荐系统</a>'
        '<a href="copy://算法工程师">算法工程师</a>'
    )

    assert strategy.precise_keywords == ["算法工程师", "推荐系统"]
    assert strategy.expansion_keywords == []


def test_to_payload_returns_serializable_structure():
    service = SearchStrategyService()
    strategy = service.build_from_analysis_result(
        '<a href="copy://后端开发">后端开发</a>'
    )

    payload = service.to_payload(strategy)

    assert payload["precise_keywords"] == ["后端开发"]
    assert payload["boolean_queries"] == []
