"""Structured search strategy generation for Liepin automation."""

import html
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
    TAG_TEXT_PATTERN = re.compile(
        r'<a[^>]*href="copy://([^"]+)"[^>]*>(.*?)</a>', re.DOTALL
    )
    HTML_TAG_PATTERN = re.compile(r"<[^>]+>")
    SECTION_PATTERN_TEMPLATE = (
        r"<p><strong>{label}</strong>[:：]?</p>\s*"
        r'<div class="tag-cloud">(.*?)</div>'
    )
    INLINE_SECTION_PATTERN_TEMPLATE = (
        r"<p><strong>{label}</strong>[:：]</p>\s*(.*?)</(?:div|p|ol|ul)>"
    )
    FREE_TEXT_LABELS = {
        "exclude_keywords": ["排除 / 去噪思路", "高噪音词提醒"],
        "boolean_queries": ["推荐组合搜索公式"],
    }

    def build_from_analysis_result(self, analysis_html: str) -> SearchStrategy:
        """Create a first-pass strategy from a job analysis HTML report."""
        analysis_html = analysis_html or ""
        all_keywords = self._extract_unique_copy_keywords(analysis_html)

        precise_keywords = self._extract_keywords_from_section(
            analysis_html,
            ["第一轮精准搜索词", "精准搜索词"],
        )
        expansion_keywords = self._extract_keywords_from_section(
            analysis_html,
            ["第二轮扩池词", "扩池词"],
        )
        synonyms = self._extract_keywords_from_section(
            analysis_html,
            ["同义岗位词 / 内部叫法 / 替代叫法"],
        )
        scene_keywords = self._extract_keywords_from_section(
            analysis_html,
            ["核心能力 / 业务场景词"],
        )
        source_company_hints = self._extract_keywords_from_section(
            analysis_html,
            ["优先来源公司 / 团队线索"],
        )
        exclude_keywords = self._extract_free_text_points(
            analysis_html, self.FREE_TEXT_LABELS["exclude_keywords"]
        )
        boolean_queries = self._extract_free_text_points(
            analysis_html, self.FREE_TEXT_LABELS["boolean_queries"]
        )

        fallback_pool = [
            keyword
            for keyword in all_keywords
            if keyword
            not in precise_keywords
            + expansion_keywords
            + synonyms
            + scene_keywords
            + source_company_hints
        ]
        if not precise_keywords:
            precise_keywords = fallback_pool[:6]
        if not expansion_keywords:
            expansion_keywords = fallback_pool[6:12]
        if not synonyms:
            synonyms = fallback_pool[12:18]
        if scene_keywords:
            synonyms = self._merge_unique_lists(synonyms, scene_keywords)

        return SearchStrategy(
            precise_keywords=precise_keywords[:6],
            expansion_keywords=expansion_keywords[:6],
            synonyms=synonyms[:6],
            exclude_keywords=exclude_keywords[:6],
            boolean_queries=boolean_queries[:6],
            source_company_hints=source_company_hints[:6],
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

    def _extract_unique_copy_keywords(self, analysis_html: str) -> List[str]:
        seen = set()
        keywords = []
        for raw_keyword, display_text in self.TAG_TEXT_PATTERN.findall(analysis_html):
            normalized = self._normalize_keyword(raw_keyword or display_text)
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            keywords.append(normalized)
        return keywords

    def _extract_keywords_from_section(
        self, analysis_html: str, labels: List[str]
    ) -> List[str]:
        for label in labels:
            pattern = re.compile(
                r"<p><strong>[^<]*{}[^<]*</strong>[:：]?</p>\s*<div class=\"tag-cloud\">(.*?)</div>".format(
                    re.escape(label)
                ),
                re.DOTALL,
            )
            match = pattern.search(analysis_html)
            if not match:
                continue

            section_html = match.group(1)
            values = self._extract_unique_copy_keywords(section_html)
            if values:
                return values
        return []

    def _extract_free_text_points(
        self, analysis_html: str, labels: List[str]
    ) -> List[str]:
        values = []
        for label in labels:
            section = self._extract_text_after_label(analysis_html, label)
            if not section:
                continue

            parts = self._split_to_points(section)
            values = self._merge_unique_lists(values, parts)
        return values

    def _extract_text_after_label(self, analysis_html: str, label: str) -> str:
        list_pattern = re.compile(
            r"<p><strong>[^<]*{}[^<]*</strong>[:：]?</p>\s*<(ol|ul)>(.*?)</\1>".format(
                re.escape(label)
            ),
            re.DOTALL,
        )
        match = list_pattern.search(analysis_html)
        if match:
            list_items = re.findall(r"<li>(.*?)</li>", match.group(2), re.DOTALL)
            text = "\n".join(self._clean_text(item) for item in list_items if item)
            if text:
                return text

        pattern = re.compile(
            r"<p><strong>[^<]*{}[^<]*</strong>[:：]?</p>(.*?)(?:</div>|<p><strong>|<ol>|<ul>)".format(
                re.escape(label)
            ),
            re.DOTALL,
        )
        match = pattern.search(analysis_html)
        if match:
            text = self._clean_text(match.group(1))
            if text:
                return text

        inline_pattern = re.compile(
            r"<p><strong>[^<]*{}[^<]*</strong>[:：]?\s*(.*?)</p>".format(
                re.escape(label)
            ),
            re.DOTALL,
        )
        match = inline_pattern.search(analysis_html)
        if match:
            text = self._clean_text(match.group(1))
            if text:
                return text
        return ""

    def _split_to_points(self, text: str) -> List[str]:
        if not text:
            return []

        normalized = text.replace("；", "\n").replace("。", "\n")
        normalized = normalized.replace("例如", "\n例如")
        parts = re.split(r"\n+|\d+\.\s*|\d+、|[;；]", normalized)
        return [
            item
            for item in (self._normalize_keyword(part) for part in parts)
            if item and len(item) >= 2
        ]

    def _clean_text(self, value: str) -> str:
        value = html.unescape(value or "")
        value = self.HTML_TAG_PATTERN.sub(" ", value)
        return re.sub(r"\s+", " ", value).strip()

    def _normalize_keyword(self, value: str) -> str:
        cleaned = self._clean_text(value)
        cleaned = cleaned.strip(" ,，。；;：:-")
        return cleaned

    @staticmethod
    def _merge_unique_lists(base: List[str], extra: List[str]) -> List[str]:
        merged = []
        seen = set()
        for item in list(base) + list(extra):
            normalized = (item or "").strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            merged.append(normalized)
        return merged
