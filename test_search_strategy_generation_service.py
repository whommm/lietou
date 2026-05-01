import json

from src.core.search_strategy_generation_service import SearchStrategyGenerationService


class FakeLLMClient:
    def __init__(self, response):
        self.response = response
        self.prompts = []

    def chat(self, prompt, system_message=""):
        self.prompts.append(prompt)
        return self.response


def test_generate_builds_precise_scene_rounds_with_position_filter():
    response = json.dumps(
        {
            "position_filter": "产品总监",
            "direct_keywords": ["产品总监", "产品设计经理"],
            "domain_terms": ["文创", "潮玩", "IP衍生品", "益智玩具", "科普"],
            "capability_terms": ["产品设计", "供应链", "量产"],
            "recommended_rounds": [
                {"query": "文创 潮玩", "position_filter": "产品"},
                {"query": "IP衍生品", "position_filter": "产品"},
                {"query": "文创衍生品", "position_filter": "产品"},
                {"query": "益智玩具 科普", "position_filter": "产品"},
            ],
            "rejected_terms": [{"term": "产品设计", "reason": "过泛"}],
        },
        ensure_ascii=False,
    )
    service = SearchStrategyGenerationService(FakeLLMClient(response))

    strategy = service.generate("<p>5年+经验，大专及以上</p>", "产品总监")
    queries = [item["query"] for item in strategy.executable_rounds]

    assert queries == ["文创 潮玩", "IP衍生品", "文创衍生品", "益智玩具 科普"]
    assert all(item["position_filter"] == "产品" for item in strategy.executable_rounds)
    assert strategy.filters["活跃度"] == "近一周"


def test_generate_rejects_generic_product_design_rounds():
    response = json.dumps(
        {
            "position_filter": "产品",
            "direct_keywords": ["产品总监"],
            "domain_terms": ["文创", "潮玩"],
            "recommended_rounds": [
                {"query": "产品设计", "position_filter": "产品"},
                {"query": "设计 产品设计", "position_filter": "产品"},
                {"query": "文创 潮玩", "position_filter": "产品"},
            ],
        },
        ensure_ascii=False,
    )
    service = SearchStrategyGenerationService(FakeLLMClient(response))

    strategy = service.generate("", "产品总监")
    queries = [item["query"] for item in strategy.executable_rounds]

    assert queries == ["文创 潮玩"]
