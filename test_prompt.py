from src.core.prompt import MATCH_CRITERIA_GENERATION_PROMPT, SEARCH_INTENT_PROMPT_APPENDIX


def test_search_intent_appendix_does_not_request_match_criteria():
    assert 'data-search-intent="true"' in SEARCH_INTENT_PROMPT_APPENDIX
    assert "recommended_rounds" in SEARCH_INTENT_PROMPT_APPENDIX
    assert "capability_terms" in SEARCH_INTENT_PROMPT_APPENDIX
    assert "exclude_terms" in SEARCH_INTENT_PROMPT_APPENDIX
    assert "core_requirements" not in SEARCH_INTENT_PROMPT_APPENDIX
    assert "dealbreakers" not in SEARCH_INTENT_PROMPT_APPENDIX


def test_match_criteria_generation_prompt_is_dedicated():
    assert "core_requirements" in MATCH_CRITERIA_GENERATION_PROMPT
    assert "{job_description}" in MATCH_CRITERIA_GENERATION_PROMPT
    assert "{analysis_html}" in MATCH_CRITERIA_GENERATION_PROMPT
