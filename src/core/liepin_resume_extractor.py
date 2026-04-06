"""Candidate detail extraction and resume normalization for Liepin."""

import json
from dataclasses import asdict
from typing import Dict, List, Optional

from .liepin_search_service import LiepinSearchCandidate
from ..models import Candidate
from ..utils.text_normalizer import build_resume_summary, build_resume_text

try:
    from playwright.sync_api import Error, Page
except ImportError:  # pragma: no cover
    Error = Exception
    Page = None


class LiepinResumeExtractionError(Exception):
    """Raised when candidate detail extraction fails."""


class LiepinResumeExtractor:
    """Extract candidate detail sections from a Liepin detail page."""

    BASIC_INFO_SELECTORS = [
        ".resume-header",
        ".resume-info",
        ".basic-info",
        "body",
    ]
    SUMMARY_SELECTORS = [
        ".self-evaluation",
        ".summary-section",
        ".resume-summary",
    ]
    EXPERIENCE_SELECTORS = [
        ".work-experience",
        ".resume-work",
        ".work-section",
    ]
    PROJECT_SELECTORS = [
        ".project-experience",
        ".resume-project",
        ".project-section",
    ]
    EDUCATION_SELECTORS = [
        ".education-experience",
        ".resume-education",
        ".education-section",
    ]
    EXTRA_SELECTORS = [
        ".skill-section",
        ".resume-extra",
        ".additional-info",
    ]

    def extract_candidate(
        self, page: Page, summary: LiepinSearchCandidate
    ) -> Candidate:
        """Extract a normalized candidate from the current detail page."""
        sections = self.extract_sections(page)
        resume_text = build_resume_text(
            basic_lines=sections.get("basic_info", []),
            summary_lines=sections.get("summary", []),
            experience_lines=sections.get("experience", []),
            project_lines=sections.get("projects", []),
            education_lines=sections.get("education", []),
            extra_lines=sections.get("extra", []),
        )
        summary_lines = (
            sections.get("basic_info", [])
            + sections.get("summary", [])
            + sections.get("experience", [])[:3]
        )
        return Candidate(
            id="",
            profile_url=summary.profile_url,
            name=summary.name,
            current_title=summary.current_title,
            current_company=summary.current_company,
            city=summary.city,
            work_years=summary.work_years,
            education=summary.education,
            resume_text=resume_text,
            resume_summary=build_resume_summary(summary_lines or [summary.summary]),
            raw_payload_json=json.dumps(sections, ensure_ascii=False),
        )

    def extract_sections(self, page: Page) -> Dict[str, List[str]]:
        """Extract all structured sections from the current page."""
        sections = {
            "basic_info": self._extract_first_section(page, self.BASIC_INFO_SELECTORS),
            "summary": self._extract_first_section(page, self.SUMMARY_SELECTORS),
            "experience": self._extract_first_section(page, self.EXPERIENCE_SELECTORS),
            "projects": self._extract_first_section(page, self.PROJECT_SELECTORS),
            "education": self._extract_first_section(page, self.EDUCATION_SELECTORS),
            "extra": self._extract_first_section(page, self.EXTRA_SELECTORS),
        }
        if not any(sections.values()):
            raise LiepinResumeExtractionError("未提取到简历详情内容，请检查详情页结构")
        return sections

    def _extract_first_section(self, page: Page, selectors: List[str]) -> List[str]:
        for selector in selectors:
            try:
                locator = page.locator(selector).first
                if locator.is_visible(timeout=1500):
                    text = locator.inner_text(timeout=3000)
                    lines = [line.strip() for line in text.splitlines() if line.strip()]
                    if lines:
                        return lines
            except Exception:
                continue
        return []
