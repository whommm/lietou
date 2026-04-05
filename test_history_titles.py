from src.core.history import HistoryManager


def test_company_research_title_uses_company_name():
    manager = HistoryManager(record_type="company_research")

    title = manager._extract_title("[公司调研] 字节跳动", "<p>report</p>")

    assert title == "字节跳动"


def test_job_analysis_title_prefers_job_name_from_jd():
    manager = HistoryManager(record_type="job_analysis")

    jd_text = "岗位名称：高级算法工程师\n岗位职责：负责推荐系统优化"
    result = "<h2>岗位名称：AI产品经理</h2>"

    title = manager._extract_title(jd_text, result)

    assert title == "高级算法工程师"


def test_job_analysis_title_uses_first_line_when_it_looks_like_job_name():
    manager = HistoryManager(record_type="job_analysis")

    jd_text = "高级产品经理\n负责增长方向产品规划与落地"

    title = manager._extract_title(jd_text, "")

    assert title == "高级产品经理"


def test_job_analysis_title_skips_noise_and_falls_back_to_result():
    manager = HistoryManager(record_type="job_analysis")

    jd_text = "岗位职责\n负责大模型应用建设"
    result = "<p><strong>岗位名称：</strong>大模型应用工程师</p>"

    title = manager._extract_title(jd_text, result)

    assert title == "大模型应用工程师"
