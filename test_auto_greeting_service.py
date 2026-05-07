from src.core.auto_greeting_service import AutoGreetingService
from src.models import CandidateExcelRecord


def test_auto_greeting_requires_explicit_high_tier():
    record = CandidateExcelRecord(
        row_index=2,
        sequence=1,
        name="张三",
        profile_url="https://example.com/resume/1",
        capture_status="抓取成功",
        resume_text="完整简历内容",
    )

    assert AutoGreetingService._get_tier(record) is None
    assert AutoGreetingService._is_greetable_candidate(record, {"A", "B"}) is False


def test_auto_greeting_accepts_explicit_tier_or_detail_tier():
    explicit = CandidateExcelRecord(
        row_index=2,
        sequence=1,
        name="张三",
        profile_url="https://example.com/resume/1",
        capture_status="抓取成功",
        match_tier="A",
        talent_tags="金领",
    )
    from_detail = CandidateExcelRecord(
        row_index=3,
        sequence=2,
        name="李四",
        profile_url="https://example.com/resume/2",
        capture_status="部分成功",
        match_detail="档位判定：B\n建议动作：可聊待验证",
        resume_text="金领人才",
    )

    assert AutoGreetingService._is_greetable_candidate(explicit, {"A", "B"}) is True
    assert AutoGreetingService._is_greetable_candidate(from_detail, {"A", "B"}) is True


def test_auto_greeting_rejects_gold_collar_with_contact_info():
    record = CandidateExcelRecord(
        row_index=2,
        sequence=1,
        name="张三",
        profile_url="https://example.com/resume/1",
        capture_status="抓取成功",
        match_tier="A",
        talent_tags="金领",
        resume_text="候选人电话 13800138000",
    )

    assert AutoGreetingService._is_greetable_candidate(record, {"A", "B"}) is False
