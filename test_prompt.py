from src.core.prompt import MATCH_CRITERIA_PROMPT_APPENDIX


def test_match_criteria_prompt_appendix_requires_search_intent_script():
    assert 'data-search-intent="true"' in MATCH_CRITERIA_PROMPT_APPENDIX
    assert "recommended_rounds" in MATCH_CRITERIA_PROMPT_APPENDIX
    assert "capability_terms" in MATCH_CRITERIA_PROMPT_APPENDIX
    assert "exclude_terms" in MATCH_CRITERIA_PROMPT_APPENDIX
