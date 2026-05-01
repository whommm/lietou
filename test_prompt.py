from src.core.prompt import (
    MATCH_CRITERIA_GENERATION_PROMPT,
    SEARCH_STRATEGY_GENERATION_PROMPT,
)


def test_search_strategy_generation_prompt_is_dedicated():
    assert "recommended_rounds" in SEARCH_STRATEGY_GENERATION_PROMPT
    assert "position_filter" in SEARCH_STRATEGY_GENERATION_PROMPT
    assert "搜索栏" in SEARCH_STRATEGY_GENERATION_PROMPT
    assert "职位栏" in SEARCH_STRATEGY_GENERATION_PROMPT
    assert "core_requirements" not in SEARCH_STRATEGY_GENERATION_PROMPT
    assert "dealbreakers" not in SEARCH_STRATEGY_GENERATION_PROMPT


def test_match_criteria_generation_prompt_is_dedicated():
    assert "core_requirements" in MATCH_CRITERIA_GENERATION_PROMPT
    assert "关键词匹配规则" in MATCH_CRITERIA_GENERATION_PROMPT
    assert "核心命中词" in MATCH_CRITERIA_GENERATION_PROMPT
    assert "weight 固定为 0" in MATCH_CRITERIA_GENERATION_PROMPT
    assert "{job_description}" in MATCH_CRITERIA_GENERATION_PROMPT
    assert "{analysis_html}" in MATCH_CRITERIA_GENERATION_PROMPT
