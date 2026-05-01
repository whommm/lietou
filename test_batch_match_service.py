from src.core.batch_match_service import BatchMatchService
from src.models import Candidate, CandidateExcelRecord, MatchCriteria, MatchCriterionItem


class FakeLLMClient:
    def chat(self, prompt):
        return (
            "建议动作：建议优先推进\n"
            "一句话结论：候选人核心经历与岗位高度贴合\n"
            "档位判定：A\n"
            "核心要求符合数：3/4\n"
            "明确短板：缺少海外业务经验"
        )


class FakeJsonLLMClient:
    def chat(self, prompt):
        return (
            "{"
            '"tier":"A",'
            '"core_met_count":3,'
            '"core_total":4,'
            '"dealbreaker_hit":false,'
            '"recommendation":"建议优先推进",'
            '"summary":"核心经历与岗位要求高度重合",'
            '"risks":"需要补充确认团队管理深度",'
            '"detail":"档位判定：A\\n建议动作：建议优先推进"'
            "}"
        )


class FakeFencedJsonLLMClient:
    def chat(self, prompt):
        return (
            "```json\n"
            "{"
            '"tier":"A",'
            '"core_met_count":4,'
            '"core_total":5,'
            '"dealbreaker_hit":false,'
            '"recommendation":"建议先顾问深聊后再推",'
            '"summary":"方向基本匹配但管理跨度待确认",'
            '"risks":"管理经验描述较少"'
            "}\n"
            "```"
        )


class FakeHtmlLLMClient:
    def chat(self, prompt):
        return (
            "<div><p><strong>建议动作：</strong>建议优先推进</p>"
            "<p><strong>一句话结论：</strong>整体背景匹配</p>"
            "<p><strong>明确短板：</strong>行业深度一般</p>"
            "<p>档位判定：B</p>"
            "<p>核心要求符合数：2/4</p></div>"
        )


class FakeTierJsonLLMClient:
    """Returns tier-based JSON."""

    def chat(self, prompt):
        return (
            "步骤 1：显式能力：Java后端开发。推断能力：具备高并发经验（依据：负责电商平台订单系统）。\n"
            "步骤 2：无否决项。\n"
            "步骤 3：档位判定：A，核心要求符合数：4/5\n"
            '{"tier":"A","core_met_count":4,"core_total":5,"dealbreaker_hit":false,"recommendation":"顾问深聊后再推","summary":"技术栈匹配度高","risks":"管理经验待验证"}'
        )


class FakeDealbreakerJsonLLMClient:
    """Returns JSON with dealbreaker_hit=true."""

    def chat(self, prompt):
        return (
            '{"tier":"C","core_met_count":1,"core_total":5,"dealbreaker_hit":true,"recommendation":"暂不建议推进","summary":"缺少核心管理经验","risks":"未带过3人以上团队"}'
        )


LONG_RESUME = "具备五年以上Java后端开发经验。负责过大型分布式系统的设计与优化。" * 20


def test_batch_match_service_parses_structured_fields():
    service = BatchMatchService(repository=None, llm_client=FakeLLMClient())
    candidate = Candidate(id="c1", resume_text=LONG_RESUME)
    job = service.create_job(job_history_id="job_001", candidates=[candidate])

    results = service.run_job(job, "岗位描述", [candidate])

    assert len(results) == 1
    assert results[0].candidate_id == "c1"
    assert results[0].tier == "A"
    assert results[0].core_met_count == 3
    assert results[0].core_total == 4
    assert results[0].recommendation == "建议优先推进"
    assert results[0].summary == "候选人核心经历与岗位高度贴合"
    assert results[0].risks == "缺少海外业务经验"
    assert "档位判定" not in results[0].detail


def test_batch_match_service_prefers_json_payload():
    service = BatchMatchService(repository=None, llm_client=FakeJsonLLMClient())
    candidate = Candidate(id="c2", resume_text=LONG_RESUME)
    job = service.create_job(job_history_id="job_002", candidates=[candidate])

    results = service.run_job(job, "岗位描述", [candidate])

    assert len(results) == 1
    assert results[0].tier == "A"
    assert results[0].core_met_count == 3
    assert results[0].core_total == 4
    assert results[0].recommendation == "建议优先推进"
    assert results[0].summary == "核心经历与岗位要求高度重合"
    assert results[0].risks == "需要补充确认团队管理深度"
    assert "建议动作" in results[0].detail


def test_batch_match_service_supports_fenced_json_payload():
    service = BatchMatchService(repository=None, llm_client=FakeFencedJsonLLMClient())
    candidate = Candidate(id="c3", resume_text=LONG_RESUME)
    job = service.create_job(job_history_id="job_003", candidates=[candidate])

    results = service.run_job(job, "岗位描述", [candidate])

    assert len(results) == 1
    assert results[0].tier == "A"
    assert results[0].core_met_count == 4
    assert results[0].core_total == 5
    assert results[0].recommendation == "建议先顾问深聊后再推"
    assert results[0].summary == "方向基本匹配但管理跨度待确认"
    assert results[0].risks == "管理经验描述较少"
    assert "建议动作" in results[0].detail


def test_batch_match_service_reports_progress():
    service = BatchMatchService(repository=None, llm_client=FakeLLMClient())
    candidates = [
        Candidate(id="c1", name="张三", resume_text=LONG_RESUME),
        Candidate(id="c2", name="李四", resume_text=LONG_RESUME),
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
    candidate = Candidate(id="c4", resume_text=LONG_RESUME)
    job = service.create_job(job_history_id="job_005", candidates=[candidate])

    results = service.run_job(job, "岗位描述", [candidate])

    assert len(results) == 1
    assert results[0].tier == "B"
    assert results[0].core_met_count == 2
    assert results[0].core_total == 4
    assert results[0].recommendation == "建议优先推进"
    assert results[0].summary == "整体背景匹配"
    assert results[0].risks == "行业深度一般"
    assert "<div>" not in results[0].detail
    assert "建议动作：建议优先推进" in results[0].detail


def test_batch_match_service_parses_tier_json():
    service = BatchMatchService(
        repository=None, llm_client=FakeTierJsonLLMClient()
    )
    candidate = Candidate(id="c5", resume_text=LONG_RESUME)
    job = service.create_job(job_history_id="job_006", candidates=[candidate])

    results = service.run_job(job, "岗位描述", [candidate])

    assert len(results) == 1
    result = results[0]
    assert result.tier == "A"
    assert result.core_met_count == 4
    assert result.core_total == 5


def test_batch_match_service_caps_tier_when_dealbreaker_hit():
    service = BatchMatchService(
        repository=None, llm_client=FakeDealbreakerJsonLLMClient()
    )
    candidate = Candidate(id="c6", resume_text=LONG_RESUME)
    job = service.create_job(job_history_id="job_007", candidates=[candidate])

    results = service.run_job(job, "岗位描述", [candidate], match_criteria=None)

    assert len(results) == 1
    result = results[0]
    assert result.tier == "C"
    assert result.dealbreaker_hit is True


def test_batch_match_service_uses_match_criteria_in_prompt():
    """When MatchCriteria is provided, the prompt should contain rendered criteria."""
    service = BatchMatchService(repository=None)
    criteria = MatchCriteria(
        dealbreakers=[MatchCriterionItem(id="db_1", text="5年以上经验", enabled=True)],
        core_requirements=[
            MatchCriterionItem(id="core_1", text="Java", enabled=True, weight=100)
        ],
        basic_requirements=[
            MatchCriterionItem(id="br_1", text="分布式 / 微服务", enabled=True)
        ],
        misjudgment_reminders=["年限±6个月视为匹配"],
    )
    prompt = service._build_batch_match_prompt(
        job_description="JD",
        resume="候选人具备 Java 和分布式项目经验",
        match_criteria=criteria,
    )
    assert "<排除词 / 负向方向>" in prompt
    assert "<核心命中词>" in prompt
    assert "5年以上经验" in prompt
    assert "Java" in prompt
    assert "系统预扫描命中" in prompt
    assert "核心命中词命中：Java" in prompt
    assert "相邻相关词命中：分布式" in prompt
    assert "年限±6个月视为匹配" in prompt


def test_batch_match_service_extracts_json_from_pre_tags():
    service = BatchMatchService(repository=None)
    raw = '<pre>{"tier":"A","core_met_count":3,"core_total":4,"dealbreaker_hit":false}</pre>'
    extracted = service._extract_json_text(raw)
    assert extracted == '{"tier":"A","core_met_count":3,"core_total":4,"dealbreaker_hit":false}'


class FakeFactoryLLMClient:
    """A factory-backed client to verify concurrent execution uses isolated clients."""

    def __init__(self, tiers):
        self.tiers = tiers
        self.index = 0

    def chat(self, prompt):
        tier = self.tiers[self.index % len(self.tiers)]
        self.index += 1
        return f'{{"tier":"{tier}","core_met_count":3,"core_total":4,"dealbreaker_hit":false,"recommendation":"推进","summary":"ok","risks":""}}'


def test_batch_match_service_runs_excel_candidates_concurrently():
    tiers = ["A", "B", "D", "C", "A"]
    factory_calls = {"count": 0}

    def factory():
        factory_calls["count"] += 1
        return FakeFactoryLLMClient(tiers)

    service = BatchMatchService(
        repository=None, llm_client=None, llm_client_factory=factory
    )
    long_resume = "具备五年以上Java后端开发经验。" * 30  # ensure > 200 chars
    candidates = [
        CandidateExcelRecord(row_index=i + 1, sequence=i + 1, name=f"候选人{i+1}", resume_text=long_resume)
        for i in range(5)
    ]
    progress = []

    results = service.match_excel_candidates(
        "岗位描述",
        candidates,
        progress_callback=lambda current, total, candidate: progress.append(
            (current, total, candidate.name)
        ),
    )

    assert len(results) == 5
    # All candidates processed
    assert sorted([r.row_index for r in results]) == [1, 2, 3, 4, 5]
    # Factory was invoked at least once per worker, up to max_workers
    assert factory_calls["count"] >= 1
    assert factory_calls["count"] <= service.max_workers
    # Progress reported all 5 steps
    assert len(progress) == 5
    assert sorted([p[0] for p in progress]) == [1, 2, 3, 4, 5]


def test_batch_match_service_respects_custom_max_workers():
    factory_calls = {"count": 0}

    def factory():
        factory_calls["count"] += 1
        return FakeFactoryLLMClient(["A"])

    service = BatchMatchService(
        repository=None, llm_client=None, llm_client_factory=factory, max_workers=2
    )
    long_resume = "具备五年以上Java后端开发经验。" * 30
    candidates = [
        CandidateExcelRecord(row_index=i + 1, sequence=i + 1, name=f"候选人{i+1}", resume_text=long_resume)
        for i in range(4)
    ]

    results = service.match_excel_candidates("岗位描述", candidates)
    assert len(results) == 4
    assert service.max_workers == 2
    # Factory is called per task (each task gets its own client), so it may be called up to candidate count
    assert factory_calls["count"] == 4


def test_batch_match_service_skips_invalid_resumes():
    """Only truly empty or very short resumes are skipped locally; others go to LLM."""
    factory_calls = {"count": 0}

    def factory():
        factory_calls["count"] += 1
        return FakeFactoryLLMClient(["A"])

    service = BatchMatchService(
        repository=None, llm_client=None, llm_client_factory=factory
    )
    long_resume = "具备五年以上Java后端开发经验。" * 30
    short_resume = "简历"
    empty_resume = ""
    footer_noise_resume = (
        "我的主页 个人中心 津ICP备15007986号-11 Copyright 用户协议 隐私政策 "
        "违法和不良信息举报 营业执照 用户协议 隐私政策"
    )
    # Add enough real content so the total length exceeds the 50-char threshold
    footer_noise_resume = long_resume + "\n" + footer_noise_resume

    # Navigation-only resume with no career keywords (mimics failed extraction)
    nav_only_resume = (
        "【候选人基础信息】\n"
        "--\n"
        "你好，--\n"
        "我的主页 个人中心\n"
        "安全中心 账户资源\n"
        "用户规则 通话管理\n"
        "安全退出"
    )

    candidates = [
        CandidateExcelRecord(row_index=1, sequence=1, name="有效", resume_text=long_resume),
        CandidateExcelRecord(row_index=2, sequence=2, name="太短", resume_text=short_resume),
        CandidateExcelRecord(row_index=3, sequence=3, name="空", resume_text=empty_resume),
        CandidateExcelRecord(row_index=4, sequence=4, name="含页脚但内容足", resume_text=footer_noise_resume),
        CandidateExcelRecord(row_index=5, sequence=5, name="仅导航无职业信息", resume_text=nav_only_resume),
    ]

    results = service.match_excel_candidates("岗位描述", candidates)

    assert len(results) == 5
    # Valid candidate went through LLM
    assert results[0].tier == "A"
    assert results[0].dealbreaker_hit is False
    # Short resume skipped locally
    assert results[1].tier == "C"
    assert results[1].dealbreaker_hit is True
    # Empty resume skipped locally
    assert results[2].tier == "C"
    assert results[2].dealbreaker_hit is True
    # Resume with footer noise but substantial content should still go to LLM
    assert results[3].tier == "A"
    assert results[3].dealbreaker_hit is False
    # Navigation-only resume with no career keywords should be skipped locally
    assert results[4].tier == "C"
    assert results[4].dealbreaker_hit is True
    # Factory called for the 2 valid/long resumes
    assert factory_calls["count"] == 2
