import json

from src.core.match_criteria_service import MatchCriteriaService


class FakeLLMClient:
    def __init__(self, response):
        self.response = response
        self.prompts = []

    def chat(self, prompt):
        self.prompts.append(prompt)
        return self.response


def test_match_criteria_service_generates_valid_criteria():
    response = json.dumps(
        {
            "dealbreakers": [
                {"id": "db_1", "text": "无相关行业经验", "enabled": True, "weight": 0}
            ],
            "core_requirements": [
                {"id": "cr_1", "text": "结构设计", "enabled": True, "weight": 60},
                {"id": "cr_2", "text": "灯具经验", "enabled": True, "weight": 40},
            ],
            "basic_requirements": [
                {"id": "br_1", "text": "本科", "enabled": True, "weight": 0}
            ],
            "bonuses": [
                {"id": "bo_1", "text": "散热经验", "enabled": True, "weight": 0}
            ],
            "misjudgment_reminders": ["不要只看职位名"],
            "version": 1,
            "confirmed_at": "",
        },
        ensure_ascii=False,
    )
    service = MatchCriteriaService(FakeLLMClient(response))

    criteria = service.generate("<html>分析</html>", "深圳灯具结构工程师")

    assert criteria.core_requirements[0].text == "结构设计"
    assert sum(item.weight for item in criteria.core_requirements) == 100
    assert "深圳灯具结构工程师" in service.llm_client.prompts[0]


def test_match_criteria_service_falls_back_on_invalid_json():
    service = MatchCriteriaService(FakeLLMClient("不是JSON"))

    criteria = service.generate("", "算法工程师")

    assert criteria.validate() == []
    assert criteria.core_requirements


def test_match_criteria_service_extracts_from_analysis_tail():
    raw = """
    <html>报告</html>
    {"dealbreakers":[],"core_requirements":[{"id":"cr_1","text":"算法","enabled":true,"weight":100}],"basic_requirements":[],"bonuses":[],"misjudgment_reminders":[],"version":1,"confirmed_at":""}
    """
    service = MatchCriteriaService(FakeLLMClient(""))

    criteria = service.extract_from_analysis(raw)

    assert criteria is not None
    assert criteria.core_requirements[0].text == "算法"
