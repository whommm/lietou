from src.core.batch_match_repository import BatchMatchRepository
from src.core.batch_match_service import BatchMatchService
from src.core.database import DatabaseManager
from src.models import Candidate


class FakeLLMClient:
    def chat(self, prompt):
        return (
            '<div class="card card-blue">'
            "<p><strong>建议动作：</strong>建议优先推进</p>"
            "<p><strong>一句话结论：</strong>候选人核心经历与岗位高度贴合</p>"
            "</div>"
            '<div class="rating"><span class="rating-value">85%</span></div>'
            '<div class="card card-orange">'
            "<p><strong>明确短板：</strong>缺少海外业务经验</p>"
            "</div>"
        )


def test_batch_match_service_parses_structured_fields(tmp_path):
    repository = BatchMatchRepository(
        DatabaseManager(db_path=str(tmp_path / "test.db"))
    )
    service = BatchMatchService(repository=repository, llm_client=FakeLLMClient())
    candidate = Candidate(id="c1", resume_text="简历内容")
    job = service.create_job(job_history_id="job_001", candidates=[candidate])

    results = service.run_job(job, "岗位描述", [candidate])

    assert len(results) == 1
    assert results[0].score == 85
    assert results[0].recommendation == "建议优先推进"
    assert results[0].summary == "候选人核心经历与岗位高度贴合"
    assert results[0].risks == "缺少海外业务经验"
