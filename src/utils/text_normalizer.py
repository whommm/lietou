"""Text normalization helpers for candidate resume extraction."""

import re
from typing import Iterable, List


NOISE_LINES = (
    "在线沟通",
    "立即沟通",
    "收藏",
    "举报",
    "下载简历",
    "查看联系方式",
    "登录后查看",
)


def clean_text_lines(lines: Iterable[str]) -> List[str]:
    """Normalize a sequence of text lines and remove obvious UI noise."""
    normalized = []
    for line in lines:
        line = re.sub(r"\s+", " ", (line or "").strip())
        if not line:
            continue
        if line in NOISE_LINES:
            continue
        normalized.append(line)
    return normalized


def build_resume_text(
    basic_lines: Iterable[str],
    summary_lines: Iterable[str],
    experience_lines: Iterable[str],
    project_lines: Iterable[str],
    education_lines: Iterable[str],
    extra_lines: Iterable[str],
) -> str:
    """Build a stable resume text structure for downstream matching."""

    sections = [
        ("候选人基础信息", clean_text_lines(basic_lines)),
        ("个人概述", clean_text_lines(summary_lines)),
        ("工作经历", clean_text_lines(experience_lines)),
        ("项目经历", clean_text_lines(project_lines)),
        ("教育经历", clean_text_lines(education_lines)),
        ("补充信息", clean_text_lines(extra_lines)),
    ]

    rendered = []
    for title, lines in sections:
        if not lines:
            continue
        rendered.append("【{}】".format(title))
        rendered.extend(lines)
        rendered.append("")
    return "\n".join(rendered).strip()


def build_resume_summary(lines: Iterable[str], limit: int = 220) -> str:
    """Build a compact summary for candidate list previews."""
    summary = " ".join(clean_text_lines(lines))
    if len(summary) > limit:
        return summary[:limit] + "..."
    return summary
