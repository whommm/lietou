from src.ui.html_renderer import build_loading_animation_html


def test_job_analysis_loading_variant_contains_analysis_steps():
    html = build_loading_animation_html("job_analysis")

    assert "分析岗位" in html
    assert "读取岗位描述" in html
    assert "生成搜寻建议" in html


def test_resume_match_loading_variant_contains_resume_steps():
    html = build_loading_animation_html("resume_match")

    assert "匹配简历" in html
    assert "提取简历经历" in html
    assert "生成沟通建议" in html


def test_company_research_loading_variant_contains_research_steps():
    html = build_loading_animation_html("company_research")

    assert "调研公司" in html
    assert "搜索公开信息" in html
    assert "生成调研报告" in html
