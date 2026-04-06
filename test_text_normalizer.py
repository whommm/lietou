from src.utils.text_normalizer import (
    build_resume_summary,
    build_resume_text,
    clean_text_lines,
)


def test_clean_text_lines_removes_noise_and_blank_lines():
    lines = clean_text_lines(["", " 在线沟通 ", "高级算法工程师", "\n", "字节跳动"])

    assert lines == ["高级算法工程师", "字节跳动"]


def test_build_resume_text_keeps_section_structure():
    text = build_resume_text(
        basic_lines=["姓名：张三", "当前职位：算法工程师"],
        summary_lines=["负责推荐系统优化"],
        experience_lines=["字节跳动 / 算法工程师 / 2021-至今"],
        project_lines=[],
        education_lines=["北京大学 / 计算机"],
        extra_lines=[],
    )

    assert "【候选人基础信息】" in text
    assert "【个人概述】" in text
    assert "【工作经历】" in text
    assert "【教育经历】" in text


def test_build_resume_summary_truncates_long_text():
    summary = build_resume_summary(["a" * 300], limit=50)

    assert summary.endswith("...")
    assert len(summary) == 53
