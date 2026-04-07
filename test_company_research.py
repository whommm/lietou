from src.core.company_research_client import CompanyResearchClient, CompanyResearchError


class FakeLLM:
    def __init__(self):
        self.prompts = []

    def chat(self, prompt):
        self.prompts.append(prompt)
        return "<div>report</div>"


def build_client():
    client = CompanyResearchClient.__new__(CompanyResearchClient)
    client.llm = FakeLLM()
    client.tavily = None
    return client


def test_research_returns_hint_when_search_results_empty(monkeypatch):
    client = build_client()
    monkeypatch.setattr(client, "_search_company", lambda company_name: [])

    result = client.research("不存在公司")

    assert result == "未找到相关搜索结果，请检查公司名称是否正确"


def test_search_company_deduplicates_and_sorts_results():
    class FakeTavily:
        def __init__(self):
            self.calls = []

        def search(self, **kwargs):
            self.calls.append(kwargs["query"])
            if "公司简介" in kwargs["query"]:
                return {
                    "results": [
                        {"url": "https://a.com", "score": 0.4, "title": "A"},
                        {"url": "https://b.com", "score": 0.9, "title": "B"},
                    ]
                }
            return {
                "results": [
                    {"url": "https://a.com", "score": 0.8, "title": "A2"},
                    {"url": "https://c.com", "score": 0.5, "title": "C"},
                ]
            }

    client = build_client()
    client.tavily = FakeTavily()

    results = client._search_company("测试公司")

    assert [item["url"] for item in results] == [
        "https://b.com",
        "https://c.com",
        "https://a.com",
    ]
    assert len(client.tavily.calls) == 2


def test_search_company_wraps_tavily_errors():
    class BrokenTavily:
        def search(self, **kwargs):
            raise RuntimeError("boom")

    client = build_client()
    client.tavily = BrokenTavily()

    try:
        client._search_company("测试公司")
    except CompanyResearchError as exc:
        assert "搜索失败" in str(exc)
    else:
        raise AssertionError("expected CompanyResearchError")


def test_generate_report_uses_detailed_content_when_available():
    client = build_client()

    report = client._generate_report(
        "测试公司",
        [
            {
                "title": "官网",
                "url": "https://example.com",
                "content": "公司介绍",
            }
        ],
        [{"url": "https://example.com", "content": "详细网页正文"}],
    )

    assert report == "<div>report</div>"
    assert "测试公司" in client.llm.prompts[0]
    assert "详细网页正文" in client.llm.prompts[0]
    assert "官网" in client.llm.prompts[0]


def test_generate_report_uses_fallback_text_without_detailed_content():
    client = build_client()

    client._generate_report(
        "测试公司",
        [{"title": "官网", "url": "https://example.com", "content": "简介"}],
        [],
    )

    assert "未获取到详细网页内容" in client.llm.prompts[0]
