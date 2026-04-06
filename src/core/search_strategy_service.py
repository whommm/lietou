"""Structured search strategy generation for Liepin automation."""

import re
from dataclasses import dataclass, field
from typing import List


@dataclass
class SearchStrategy:
    """Structured output for downstream search automation."""

    precise_keywords: List[str] = field(default_factory=list)
    expansion_keywords: List[str] = field(default_factory=list)
    synonyms: List[str] = field(default_factory=list)
    exclude_keywords: List[str] = field(default_factory=list)
    boolean_queries: List[str] = field(default_factory=list)
    source_company_hints: List[str] = field(default_factory=list)


class SearchStrategyService:
    """Build structured search strategies from current project artifacts.

    The first implementation intentionally stays conservative: it can extract
    copyable tag keywords from the HTML report and produce a stable object that
    later RPA code can consume without parsing UI widgets directly.
    """

    COPY_LINK_PATTERN = re.compile(r'href="copy://([^"]+)"')

    def build_from_analysis_result(self, analysis_html: str) -> SearchStrategy:
        """Create a first-pass strategy from a job analysis HTML report."""
        raw_keywords = self.COPY_LINK_PATTERN.findall(analysis_html or "")
        unique_keywords = []
        seen = set()
        for keyword in raw_keywords:
            normalized = keyword.strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            unique_keywords.append(normalized)

        return SearchStrategy(
            precise_keywords=unique_keywords[:6],
            expansion_keywords=unique_keywords[6:12],
        )

    def to_payload(self, strategy: SearchStrategy) -> dict:
        """Return a serializable payload for task creation."""
        return {
            "precise_keywords": list(strategy.precise_keywords),
            "expansion_keywords": list(strategy.expansion_keywords),
            "synonyms": list(strategy.synonyms),
            "exclude_keywords": list(strategy.exclude_keywords),
            "boolean_queries": list(strategy.boolean_queries),
            "source_company_hints": list(strategy.source_company_hints),
        }
