from src.core.batch_match_service import BatchMatchService
from src.models import Candidate


class FakeLLMClient:
    def chat(self, prompt):
        return (
            "建议动作：建议优先推进\n"
            "一句话结论：候选人核心经历与岗位高度贴合\n"
            "匹配度分数：85\n"
            "明确短板：缺少海外业务经验"
        )


class FakeJsonLLMClient:
    def chat(self, prompt):
        return (
            "{"
            '"score": 91,'
            '"recommendation": "建议优先推进",'
            '"summary": "核心经历与岗位要求高度重合",'
            '"risks": "需要补充确认团队管理深度",'
            '"detail": "匹配度分数：91\\n建议动作：建议优先推进"'
            "}"
        )


class FakeFencedJsonLLMClient:
    def chat(self, prompt):
        return (
            "```json\n"
            "{"
            '"score": "87%",'
            '"recommendation": "建议先顾问深聊后再推",'
            '"summary": "方向基本匹配但管理跨度待确认",'
            '"risks": "管理经验描述较少"'
            "}\n"
            "```"
        )


class FakeHtmlLLMClient:
    def chat(self, prompt):
        return (
            "<div><p><strong>建议动作：</strong>建议优先推进</p>"
            "<p><strong>一句话结论：</strong>整体背景匹配</p>"
            "<p><strong>明确短板：</strong>行业深度一般</p>"
            "<p>匹配度分数：78</p></div>"
        )


def test_batch_match_service_parses_structured_fields():
    service = BatchMatchService(repository=None, llm_client=FakeLLMClient())
    candidate = Candidate(id="c1", resume_text="简历内容")
    job = service.create_job(job_history_id="job_001", candidates=[candidate])

    results = service.run_job(job, "岗位描述", [candidate])

    assert len(results) == 1
    assert results[0].candidate_id == "c1"
    assert results[0].score == 85
    assert results[0].recommendation == "建议优先推进"
    assert results[0].summary == "候选人核心经历与岗位高度贴合"
    assert results[0].risks == "缺少海外业务经验"
    assert "匹配度分数：85" in results[0].detail


def test_batch_match_service_prefers_json_payload():
    service = BatchMatchService(repository=None, llm_client=FakeJsonLLMClient())
    candidate = Candidate(id="c2", resume_text="简历内容")
    job = service.create_job(job_history_id="job_002", candidates=[candidate])

    results = service.run_job(job, "岗位描述", [candidate])

    assert len(results) == 1
    assert results[0].score == 91
    assert results[0].recommendation == "建议优先推进"
    assert results[0].summary == "核心经历与岗位要求高度重合"
    assert results[0].risks == "需要补充确认团队管理深度"
    assert "建议动作" in results[0].detail


def test_batch_match_service_supports_fenced_json_payload():
    service = BatchMatchService(repository=None, llm_client=FakeFencedJsonLLMClient())
    candidate = Candidate(id="c3", resume_text="简历内容")
    job = service.create_job(job_history_id="job_003", candidates=[candidate])

    results = service.run_job(job, "岗位描述", [candidate])

    assert len(results) == 1
    assert results[0].score == 87
    assert results[0].recommendation == "建议先顾问深聊后再推"
    assert results[0].summary == "方向基本匹配但管理跨度待确认"
    assert results[0].risks == "管理经验描述较少"
    assert "建议动作" in results[0].detail


def test_batch_match_service_reports_progress():
    service = BatchMatchService(repository=None, llm_client=FakeLLMClient())
    candidates = [
        Candidate(id="c1", name="张三", resume_text="简历1"),
        Candidate(id="c2", name="李四", resume_text="简历2"),
    ]
    job = service.create_job(job_history_id="job_004", candidates=candidates)
    progress = []

    service.run_job(
        job,
        "岗位描述",
        candidates,
        progress_callback=lambda current, total, candidate: progress.append(
            (current, total, candidate.name)
        ),
    )

    assert progress == [(1, 2, "张三"), (2, 2, "李四")]


def test_batch_match_service_normalizes_html_response_to_plain_text():
    service = BatchMatchService(repository=None, llm_client=FakeHtmlLLMClient())
    candidate = Candidate(id="c4", resume_text="简历内容")
    job = service.create_job(job_history_id="job_005", candidates=[candidate])

    results = service.run_job(job, "岗位描述", [candidate])

    assert len(results) == 1
    assert results[0].score == 78
    assert results[0].recommendation == "建议优先推进"
    assert results[0].summary == "整体背景匹配"
    assert results[0].risks == "行业深度一般"
    assert "<div>" not in results[0].detail
    assert "建议动作：建议优先推进" in results[0].detail
