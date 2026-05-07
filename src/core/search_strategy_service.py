"""Structured search strategy generation for Liepin automation."""

import html
import json
import re
from dataclasses import dataclass, field
from typing import Dict, List

from ..utils.city_data import build_default_city_scope, extract_city_from_text


@dataclass
class SearchStrategy:
    """Structured output for downstream search automation."""

    precise_keywords: List[str] = field(default_factory=list)
    expansion_keywords: List[str] = field(default_factory=list)
    synonyms: List[str] = field(default_factory=list)
    direct_keywords: List[str] = field(default_factory=list)
    indirect_keywords: List[str] = field(default_factory=list)
    long_tail_keywords: List[str] = field(default_factory=list)
    exclude_keywords: List[str] = field(default_factory=list)
    boolean_queries: List[str] = field(default_factory=list)
    source_company_hints: List[str] = field(default_factory=list)
    atomic_terms: Dict[str, List[str]] = field(default_factory=dict)
    executable_rounds: List[Dict[str, object]] = field(default_factory=list)
    filters: Dict[str, object] = field(default_factory=dict)


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
    SEARCH_INTENT_SCRIPT_PATTERN = re.compile(
        r'<script[^>]*data-search-intent="true"[^>]*>(.*?)</script>',
        re.DOTALL | re.IGNORECASE,
    )
    ROLE_SUFFIXES = (
        "工程师",
        "设计师",
        "经理",
        "主管",
        "专员",
        "顾问",
        "负责人",
        "总监",
        "架构师",
    )
    STOP_TERMS = {"工程师", "经理", "主管", "专员", "顾问", "总监", "负责人"}

    def build_from_analysis_result(self, analysis_html: str) -> SearchStrategy:
        """Create a first-pass strategy from a job analysis HTML report."""
        analysis_html = analysis_html or ""
        search_intent = self._extract_search_intent_json(analysis_html)
        all_keywords = self._extract_unique_copy_keywords(analysis_html)

        direct_section_keywords = self._extract_keywords_from_section(
            analysis_html, ["直接关键词", "直接词"]
        )
        indirect_section_keywords = self._extract_keywords_from_section(
            analysis_html, ["间接关键词", "间接词"]
        )
        long_tail_section_keywords = self._extract_keywords_from_section(
            analysis_html, ["长尾关键词", "长尾词"]
        )
        title_variant_keywords = self._extract_keywords_from_section(
            analysis_html, ["职称穷尽", "同一岗位的N种叫法"]
        )

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
        if direct_section_keywords and not precise_keywords:
            precise_keywords = direct_section_keywords
        if indirect_section_keywords and not expansion_keywords:
            expansion_keywords = indirect_section_keywords
        if title_variant_keywords:
            synonyms = self._merge_unique_lists(synonyms, title_variant_keywords)
        if long_tail_section_keywords:
            synonyms = self._merge_unique_lists(synonyms, long_tail_section_keywords)

        exclude_keywords = self._extract_free_text_points(
            analysis_html, self.FREE_TEXT_LABELS["exclude_keywords"]
        )
        boolean_queries = self._extract_free_text_points(
            analysis_html, self.FREE_TEXT_LABELS["boolean_queries"]
        )
        progressive_rounds = self._extract_progressive_search_rounds(analysis_html)

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

        direct_keywords = self._take_short_terms(search_intent.get("direct_keywords", []) or direct_section_keywords)
        indirect_keywords = self._take_short_terms(search_intent.get("indirect_keywords", []) or indirect_section_keywords)
        long_tail_keywords = self._take_short_terms(search_intent.get("long_tail_keywords", []) or long_tail_section_keywords)

        atomic_terms = self._build_atomic_terms(
            precise_keywords=precise_keywords,
            expansion_keywords=expansion_keywords,
            synonyms=synonyms,
            exclude_keywords=exclude_keywords,
            boolean_queries=boolean_queries,
            search_intent=search_intent,
        )
        executable_rounds = self._build_executable_rounds(
            atomic_terms=atomic_terms,
            precise_keywords=precise_keywords,
            expansion_keywords=expansion_keywords,
            synonyms=synonyms,
            boolean_queries=boolean_queries,
            search_intent=search_intent,
            progressive_rounds=progressive_rounds,
        )
        filters = self.extract_filters_from_analysis(analysis_html)

        return SearchStrategy(
            precise_keywords=precise_keywords[:6],
            expansion_keywords=expansion_keywords[:6],
            synonyms=synonyms[:6],
            direct_keywords=direct_keywords[:6],
            indirect_keywords=indirect_keywords[:6],
            long_tail_keywords=long_tail_keywords[:6],
            exclude_keywords=exclude_keywords[:6],
            boolean_queries=boolean_queries[:6],
            source_company_hints=source_company_hints[:6],
            atomic_terms=atomic_terms,
            executable_rounds=executable_rounds,
            filters=filters,
        )

    def to_payload(self, strategy: SearchStrategy) -> dict:
        """Return a serializable payload for task creation."""
        return {
            "precise_keywords": list(strategy.precise_keywords),
            "expansion_keywords": list(strategy.expansion_keywords),
            "synonyms": list(strategy.synonyms),
            "direct_keywords": list(strategy.direct_keywords),
            "indirect_keywords": list(strategy.indirect_keywords),
            "long_tail_keywords": list(strategy.long_tail_keywords),
            "exclude_keywords": list(strategy.exclude_keywords),
            "boolean_queries": list(strategy.boolean_queries),
            "source_company_hints": list(strategy.source_company_hints),
            "atomic_terms": {
                key: list(values) for key, values in (strategy.atomic_terms or {}).items()
            },
            "executable_rounds": [dict(item) for item in strategy.executable_rounds],
            "filters": dict(strategy.filters or {}),
        }

    def extract_filters_from_analysis(self, analysis_html: str) -> Dict[str, object]:
        """Extract conservative Liepin filters from the analysis/JD text."""
        text = self._plain_text(analysis_html)
        filters: Dict[str, object] = {}

        city = extract_city_from_text(text)
        city_scope = build_default_city_scope(city)
        if city_scope:
            filters["目前城市"] = city_scope

        work_years = self._extract_work_years(text)
        if work_years:
            filters["工作年限"] = work_years

        education = self._extract_education(text)
        if education:
            filters["教育经历"] = education

        gender = self._extract_gender(text)
        if gender:
            filters["性别"] = gender
        filters["活跃度"] = "近一周"

        return filters

    def _plain_text(self, html_text: str) -> str:
        text = re.sub(r"<script[^>]*>.*?</script>", " ", html_text or "", flags=re.DOTALL | re.IGNORECASE)
        text = self.HTML_TAG_PATTERN.sub(" ", text)
        text = html.unescape(text)
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def _extract_work_years(text: str) -> str:
        explicit = re.search(
            r"(\d+)\s*年\s*(?:\+|以上|及以上).*?(?:管理经验|团队管理|产品研发|工作经验|经验)",
            text,
        )
        if explicit:
            return "{}年以上".format(explicit.group(1))
        patterns = [
            (r"(\d+)\s*[-~至到]\s*(\d+)\s*年(?:经验|工作经验)?", "{}-{}年"),
            (r"(\d+)\s*年\s*(?:及)?以上", "{}年以上"),
            (r"(\d+)\s*年以上", "{}年以上"),
            (r"经验不限|不限经验|工作年限不限", "不限"),
        ]
        for pattern, template in patterns:
            match = re.search(pattern, text)
            if not match:
                continue
            if "{}-{}" in template:
                if int(match.group(1)) == 0:
                    continue
                return template.format(match.group(1), match.group(2))
            if "{}" in template:
                return template.format(match.group(1))
            return template
        return ""

    @staticmethod
    def _extract_education(text: str) -> str:
        if re.search(r"(学历不限|不限学历)", text):
            return "不限"
        if re.search(r"(大专|专科)\s*(及以上|以上|学历)?|统招大专", text):
            return "大专"
        if re.search(r"(本科)\s*(及以上|以上|学历)", text):
            return "本科"
        if re.search(r"博士", text):
            return "博士"
        if re.search(r"硕士|研究生", text):
            return "硕士"
        if re.search(r"本科", text):
            return "本科"
        if re.search(r"大专|专科", text):
            return "大专"
        return ""

    @staticmethod
    def _extract_gender(text: str) -> str:
        if re.search(r"性别[:：\s]*(男|男性)|限男|男性优先", text):
            return "男"
        if re.search(r"性别[:：\s]*(女|女性)|限女|女性优先", text):
            return "女"
        return "不限"

    def _extract_search_intent_json(self, analysis_html: str) -> Dict[str, List[str]]:
        match = self.SEARCH_INTENT_SCRIPT_PATTERN.search(analysis_html or "")
        if not match:
            return {}
        try:
            data = json.loads(self._clean_text(match.group(1)))
        except (TypeError, ValueError):
            return {}
        if not isinstance(data, dict):
            return {}
        normalized = {}
        for key, value in data.items():
            if isinstance(value, list):
                if key == "recommended_rounds":
                    normalized[key] = self._normalize_recommended_rounds(value)
                else:
                    normalized[key] = [
                        item
                        for item in (self._normalize_keyword(part) for part in value if isinstance(part, str))
                        if item
                    ]
        return normalized

    def _normalize_recommended_rounds(self, rounds: List[object]) -> List[object]:
        normalized = []
        for item in rounds:
            if isinstance(item, str):
                query = self._normalize_boolean_query(item)
                if query:
                    normalized.append(query)
                continue
            if not isinstance(item, dict):
                continue
            query = self._normalize_boolean_query(str(item.get("query") or ""))
            if not query:
                continue
            normalized.append(
                {
                    "query": query,
                    "match_mode": item.get("match_mode") or "all",
                    "scope": item.get("scope") or "全部经历",
                    "intent": item.get("intent") or "",
                    "position_filter": item.get("position_filter") or "",
                }
            )
        return normalized

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

    def _extract_progressive_search_rounds(self, analysis_html: str) -> List[Dict[str, object]]:
        section = self._extract_text_after_label(analysis_html, "渐进式搜索策略")
        if not section:
            return []
        rounds = []
        for line in self._split_to_points(section):
            query = self._extract_query_from_round_text(line)
            if not query:
                continue
            label = "第{}轮搜索".format(len(rounds) + 1)
            label_match = re.search(r"第\s*(\d+)\s*轮(?:（([^）]+)）)?", line)
            if label_match:
                label = "第{}轮{}".format(label_match.group(1), label_match.group(2) or "搜索")
            rounds.append(
                {
                    "label": label,
                    "query": query,
                    "intent": label,
                    "priority": len(rounds) + 1,
                    "match_mode": "any" if "OR模式" in line or "测绘" in line else "all",
                    "scope": "全部经历",
                }
            )
        return rounds[:6]

    def _extract_query_from_round_text(self, text: str) -> str:
        text = self._clean_text(text)
        if not text:
            return ""
        candidates = []
        for marker in ("示例：", "示例:", "：", ":"):
            if marker in text:
                candidates.append(text.rsplit(marker, 1)[-1])
        candidates.append(text)
        for candidate in candidates:
            normalized = self._normalize_boolean_query(candidate)
            match = re.search(
                r"(.+\b(?:AND|OR|NOT)\b.+)",
                normalized,
                flags=re.IGNORECASE,
            )
            if match:
                return self._normalize_boolean_query(match.group(1))
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

    def _build_atomic_terms(
        self,
        precise_keywords: List[str],
        expansion_keywords: List[str],
        synonyms: List[str],
        exclude_keywords: List[str],
        boolean_queries: List[str],
        search_intent: Dict[str, List[str]],
    ) -> Dict[str, List[str]]:
        if search_intent:
            atomic_terms = {
                "domain_terms": self._take_short_terms(search_intent.get("domain_terms", [])),
                "capability_terms": self._take_short_terms(search_intent.get("capability_terms", [])),
                "process_terms": self._take_short_terms(search_intent.get("process_terms", [])),
                "object_terms": self._take_short_terms(search_intent.get("object_terms", [])),
                "exclude_terms": self._merge_unique_lists(
                    self._take_short_terms(search_intent.get("exclude_terms", [])),
                    self._take_short_terms(exclude_keywords),
                ),
            }
            return atomic_terms

        classified_terms = self._classify_search_terms(
            precise_keywords=precise_keywords,
            expansion_keywords=expansion_keywords,
            synonyms=synonyms,
            boolean_queries=boolean_queries,
        )
        capability_terms = classified_terms.get("capability_terms", [])
        domain_terms = classified_terms.get("domain_terms", [])
        process_terms = classified_terms.get("process_terms", [])
        object_terms = classified_terms.get("object_terms", [])
        if not capability_terms:
            capability_terms = self._pick_capability_terms(precise_keywords + expansion_keywords)
        if not domain_terms:
            domain_terms = self._pick_domain_terms(precise_keywords + expansion_keywords + synonyms)
        if not process_terms:
            process_terms = self._pick_process_terms(synonyms + self._split_query_terms(boolean_queries))
        if not object_terms:
            object_terms = self._pick_object_terms(synonyms + precise_keywords + expansion_keywords)
        return {
            "domain_terms": domain_terms,
            "capability_terms": capability_terms,
            "process_terms": process_terms,
            "object_terms": object_terms,
            "exclude_terms": self._take_short_terms(exclude_keywords),
        }

    def _build_executable_rounds(
        self,
        atomic_terms: Dict[str, List[str]],
        precise_keywords: List[str],
        expansion_keywords: List[str],
        synonyms: List[str],
        boolean_queries: List[str],
        search_intent: Dict[str, List[str]],
        progressive_rounds: List[Dict[str, object]] = None,
    ) -> List[Dict[str, object]]:
        if search_intent.get("recommended_rounds"):
            rounds = []
            for index, item in enumerate(search_intent.get("recommended_rounds", []), start=1):
                if isinstance(item, dict):
                    raw_query = item.get("query", "")
                    if self._has_boolean_syntax(str(raw_query or "")):
                        continue
                    query = self._normalize_liepin_query(raw_query)
                    if not query or self._is_noise_only_query(query):
                        continue
                    rounds.append(
                        {
                            "label": item.get("intent") or "第{}轮搜索".format(index),
                            "query": query,
                            "intent": item.get("intent") or "模型推荐轮次",
                            "priority": index,
                            "match_mode": item.get("match_mode") or "all",
                            "scope": item.get("scope") or "全部经历",
                            "position_filter": item.get("position_filter") or "",
                        }
                    )
                elif isinstance(item, str):
                    if self._has_boolean_syntax(item):
                        continue
                    normalized = self._normalize_liepin_query(item)
                    if not normalized or self._is_noise_only_query(normalized):
                        continue
                    rounds.append(
                        {
                            "label": "第{}轮搜索".format(index),
                            "query": normalized,
                            "intent": "模型推荐轮次",
                            "priority": index,
                            "match_mode": "all",
                            "scope": "全部经历",
                        }
                    )
            if rounds:
                return rounds[:4]

        if progressive_rounds:
            platform_rounds = [
                item
                for item in progressive_rounds
                if not self._has_boolean_syntax(str(item.get("query") or ""))
                and not self._is_noise_only_query(str(item.get("query") or ""))
            ]
            if platform_rounds:
                return platform_rounds[:4]

        matrix_rounds = self._build_keyword_matrix_rounds(
            precise_keywords=precise_keywords,
            expansion_keywords=expansion_keywords,
            synonyms=synonyms,
            boolean_queries=boolean_queries,
        )
        if matrix_rounds:
            return matrix_rounds[:4]

        rounds = []
        seen = set()
        capabilities = atomic_terms.get("capability_terms", [])
        domains = atomic_terms.get("domain_terms", [])
        processes = atomic_terms.get("process_terms", [])

        for domain in domains[:3]:
            for capability in capabilities[:2]:
                self._append_round(
                    rounds,
                    seen,
                    label="主搜",
                    query_terms=[capability, domain],
                    intent="能力+领域",
                )

        for domain in domains[1:4]:
            for capability in capabilities[:1]:
                self._append_round(
                    rounds,
                    seen,
                    label="扩展",
                    query_terms=[capability, domain],
                    intent="能力+替代领域",
                )

        for process in processes[:3]:
            for capability in capabilities[:1]:
                if not domains:
                    self._append_round(
                        rounds,
                        seen,
                        label="收敛",
                        query_terms=[capability, process],
                        intent="能力+关键工艺",
                    )
                else:
                    self._append_round(
                        rounds,
                        seen,
                        label="收敛",
                        query_terms=[capability, domains[0], process],
                        intent="能力+领域+关键工艺",
                    )

        for query in precise_keywords + expansion_keywords + self._split_query_terms(boolean_queries):
            normalized = self._normalize_boolean_query(query)
            if not normalized or normalized in seen or self._is_noise_only_query(normalized):
                continue
            seen.add(normalized)
            rounds.append(
                {
                    "label": "补充",
                    "query": normalized,
                    "intent": "现有策略补充",
                    "priority": len(rounds) + 1,
                }
            )

        return rounds[:4]

    def _build_keyword_matrix_rounds(
        self,
        precise_keywords: List[str],
        expansion_keywords: List[str],
        synonyms: List[str],
        boolean_queries: List[str],
    ) -> List[Dict[str, object]]:
        classified_terms = self._classify_search_terms(
            precise_keywords=precise_keywords,
            expansion_keywords=expansion_keywords,
            synonyms=synonyms,
            boolean_queries=boolean_queries,
        )
        if not any(classified_terms.values()):
            return []
        title_terms = classified_terms.get("title_terms", [])
        domain_terms = classified_terms.get("domain_terms", [])
        position_terms = self._build_position_filter_terms(title_terms)

        rounds = []
        seen = set()
        short_domains = [
            term
            for term in self._short_search_terms(domain_terms)
            if not self._is_noise_only_query(term)
        ]
        if not short_domains:
            return []
        scene_queries = self._build_precise_scene_queries(short_domains)
        position_filter = position_terms[0] if position_terms else ""

        for query in scene_queries[:4]:
            self._append_plain_round(
                rounds,
                seen,
                label="第{}轮场景".format(len(rounds) + 1),
                query_terms=[query],
                intent="精准行业/业务场景",
                position_filter=position_filter,
            )

        return rounds[:4]

    def _build_precise_scene_queries(self, short_domains: List[str]) -> List[str]:
        terms = self._merge_unique_lists([], short_domains or [])
        scenes = []
        has = lambda marker: any(marker in term for term in terms)
        if has("文创") or has("潮玩"):
            scenes.append("文创 潮玩")
        if has("IP"):
            scenes.append("IP衍生品")
        if has("文创"):
            scenes.append("文创衍生品")
        if has("益智") or has("玩具") or has("科普"):
            scenes.append("益智玩具 科普")
        if has("展品") or has("展馆"):
            scenes.append("展品 展馆")
        if has("手办") and not has("潮玩"):
            scenes.append("手办")
        for index in range(0, len(terms), 2):
            chunk_terms = [term for term in terms[index : index + 2] if not self._is_noise_only_query(term)]
            chunk = " ".join(chunk_terms).strip()
            if chunk:
                scenes.append(chunk)
        return self._merge_unique_lists([], scenes)

    @staticmethod
    def _build_position_filter_terms(title_terms: List[str]) -> List[str]:
        terms = ["产品"]
        for term in title_terms or []:
            if not term:
                continue
            if "产品设计" in term:
                terms.append("产品设计")
            elif "设计总监" in term:
                terms.append("设计总监")
            elif "产品" in term:
                terms.append("产品")
            elif "研发" in term:
                terms.append("研发")
        result = []
        for term in terms:
            if term not in result:
                result.append(term)
        return result[:3]

    def _short_search_terms(self, terms: List[str]) -> List[str]:
        result = []
        for term in terms or []:
            short = self._to_short_search_term(term)
            if short and short not in result:
                result.append(short)
        return result

    @staticmethod
    def _to_short_search_term(term: str) -> str:
        term = (term or "").strip()
        mapping = [
            ("供应链", "供应链"),
            ("从0到1", "从0到1"),
            ("3D打印", "3D打印"),
            ("文创", "文创"),
            ("潮玩", "潮玩"),
            ("展品", "展品"),
            ("展馆", "展馆"),
            ("科普", "科普"),
            ("益智", "益智"),
            ("玩具", "玩具"),
            ("手办", "手办"),
            ("量产", "量产"),
            ("打样", "打样"),
            ("工业设计", "工业设计"),
            ("结构设计", "结构设计"),
            ("产品设计", "产品设计"),
            ("爆款", "爆款"),
            ("团队搭建", "团队搭建"),
        ]
        for marker, replacement in mapping:
            if marker in term:
                return replacement
        return term

    def _classify_search_terms(
        self,
        precise_keywords: List[str],
        expansion_keywords: List[str],
        synonyms: List[str],
        boolean_queries: List[str],
    ) -> Dict[str, List[str]]:
        terms = self._merge_unique_lists(
            [],
            list(precise_keywords or [])
            + list(expansion_keywords or [])
            + list(synonyms or [])
            + self._split_query_terms(boolean_queries or []),
        )
        normalized_terms = [self._normalize_strategy_term(term) for term in terms]
        normalized_terms = self._merge_unique_lists([], normalized_terms)
        title_terms = self._prioritize_terms(
            [term for term in normalized_terms if self._looks_like_title_term(term)],
            ["产品总监", "产品设计经理", "产品开发总监", "设计总监", "产品研发经理", "研发经理", "NPD", "Director"],
        )[:5]
        domain_terms = self._prioritize_terms(
            [
                term
                for term in normalized_terms
                if self._looks_like_domain_term(term) and term not in title_terms
            ],
            ["文创", "潮玩", "展品", "展馆", "科普", "益智", "玩具", "手办", "IP"],
        )[:6]
        capability_terms = self._prioritize_terms(
            [
                term
                for term in normalized_terms
                if self._looks_like_capability_term(term) and term not in title_terms
            ],
            ["产品设计", "3D打印", "供应链", "量产", "工业设计", "结构设计", "打样", "模具"],
        )[:8]
        process_terms = self._prioritize_terms(
            [term for term in normalized_terms if self._looks_like_outcome_term(term)],
            ["从0到1", "爆款", "团队搭建", "商业转化", "盈利模型", "千万级"],
        )[:5]
        object_terms = self._prioritize_terms(
            [
                term
                for term in normalized_terms
                if term not in title_terms + domain_terms + capability_terms + process_terms
                and self._looks_like_object_term(term)
            ],
            ["产品开发", "产品", "展品", "手办", "玩具"],
        )[:5]
        return {
            "title_terms": title_terms,
            "domain_terms": domain_terms,
            "capability_terms": capability_terms,
            "process_terms": process_terms,
            "object_terms": object_terms,
        }

    @staticmethod
    def _normalize_strategy_term(term: str) -> str:
        term = (term or "").strip()
        if not term:
            return ""
        if "供应链" in term:
            return "供应链管理"
        if "从立项到量产" in term:
            return "量产"
        if "打造爆款" in term:
            return "爆款"
        return term

    @staticmethod
    def _pick_first_matching(terms: List[str], hints: List[str]) -> str:
        for hint in hints:
            for term in terms or []:
                if hint and term and hint in term:
                    return term
        return ""

    def _append_plain_round(
        self,
        rounds: List[Dict[str, object]],
        seen: set,
        label: str,
        query_terms: List[str],
        intent: str,
        position_filter: str = "",
    ) -> None:
        query = self._normalize_liepin_query(" ".join(term for term in query_terms if term))
        if not query or query in seen:
            return
        seen.add(query)
        rounds.append(
            {
                "label": label,
                "query": query,
                "intent": intent,
                "priority": len(rounds) + 1,
                "match_mode": "all",
                "scope": "全部经历",
                "position_filter": position_filter,
            }
        )

    def _normalize_liepin_query(self, value: str) -> str:
        query = self._normalize_boolean_query(value)
        query = re.sub(r"\b(?:AND|OR|NOT)\b", " ", query, flags=re.IGNORECASE)
        query = re.sub(r"[()\"'“”‘’]", " ", query)
        return re.sub(r"\s+", " ", query).strip()

    @staticmethod
    def _has_boolean_syntax(value: str) -> bool:
        return bool(re.search(r"\b(?:AND|OR|NOT)\b|[()\"“”]", value or "", re.IGNORECASE))

    @staticmethod
    def _is_noise_only_query(value: str) -> bool:
        tokens = [token.strip() for token in re.split(r"\s+", value or "") if token.strip()]
        if not tokens:
            return True
        noise_terms = {
            "产品",
            "设计",
            "产品设计",
            "产品研发",
            "产品开发",
            "研发",
            "工业设计",
            "结构设计",
            "供应链",
            "供应链管理",
            "量产",
            "量产落地",
            "3D打印",
            "打样",
            "团队搭建",
        }
        return all(token in noise_terms for token in tokens)

    @staticmethod
    def _dedupe_overlapping_terms(terms: List[str]) -> List[str]:
        result = []
        for term in terms or []:
            term = (term or "").strip()
            if not term:
                continue
            if any(term == existing or existing in term for existing in result):
                continue
            result = [existing for existing in result if term not in existing]
            result.append(term)
        return result

    @staticmethod
    def _prioritize_terms(terms: List[str], priority_hints: List[str]) -> List[str]:
        indexed_terms = list(enumerate(terms or []))

        def score(item):
            index, term = item
            for priority, hint in enumerate(priority_hints):
                if hint and term and (hint in term or term in hint):
                    return priority, index
            return len(priority_hints), index

        return [term for _, term in sorted(indexed_terms, key=score)]

    def _append_boolean_round(
        self,
        rounds: List[Dict[str, object]],
        seen: set,
        label: str,
        query: str,
        intent: str,
        match_mode: str = "all",
        scope: str = "全部经历",
    ) -> None:
        query = self._normalize_boolean_query(query)
        if not query or query in seen:
            return
        seen.add(query)
        rounds.append(
            {
                "label": label,
                "query": query,
                "intent": intent,
                "priority": len(rounds) + 1,
                "match_mode": match_mode,
                "scope": scope,
            }
        )

    @staticmethod
    def _quote_if_needed(term: str) -> str:
        term = (term or "").strip()
        if not term:
            return ""
        if len(term) >= 4 and not (term.startswith('"') and term.endswith('"')):
            return '"{}"'.format(term)
        return term

    @staticmethod
    def _looks_like_title_term(term: str) -> bool:
        term = (term or "").strip()
        return bool(
            term
            and (
                re.search(r"(总监|经理|负责人|主管|合伙人|Director|Manager|Head)", term, re.IGNORECASE)
                or term in {"产品经理", "产品总监", "设计总监"}
            )
        )

    @staticmethod
    def _looks_like_domain_term(term: str) -> bool:
        term = (term or "").strip()
        return bool(
            term
            and re.search(
                r"(文创|潮玩|玩具|展馆|展品|科普|益智|手办|IP|博物馆|科技馆|消费电子|工业产品|实体产品)",
                term,
            )
        )

    @staticmethod
    def _looks_like_capability_term(term: str) -> bool:
        term = (term or "").strip()
        return bool(
            term
            and re.search(
                r"(产品设计|工业设计|结构设计|3D打印|供应链|量产|打样|模具|CREO|SolidWorks|Rhino|FDM|SLA|SLS|产品开发)",
                term,
                re.IGNORECASE,
            )
        )

    @staticmethod
    def _looks_like_outcome_term(term: str) -> bool:
        term = (term or "").strip()
        return bool(
            term
            and re.search(r"(从0到1|爆款|团队搭建|千万级|市场占有率|盈利模型|上市变现|商业转化)", term)
        )

    @staticmethod
    def _looks_like_object_term(term: str) -> bool:
        term = (term or "").strip()
        return bool(term and re.search(r"(产品|展品|手办|玩具|模具|样品|原型)", term))

    def _append_round(
        self,
        rounds: List[Dict[str, object]],
        seen: set,
        label: str,
        query_terms: List[str],
        intent: str,
    ) -> None:
        query = self._normalize_query(" ".join(term for term in query_terms if term))
        if not query or query in seen:
            return
        seen.add(query)
        rounds.append(
            {
                "label": "第{}轮{}".format(len(rounds) + 1, label),
                "query": query,
                "intent": intent,
                "priority": len(rounds) + 1,
            }
        )

    def _pick_capability_terms(self, keywords: List[str]) -> List[str]:
        picked = []
        for keyword in keywords:
            collapsed = self._strip_role_suffix(keyword)
            parts = self._split_compound_keyword(collapsed)
            if parts:
                picked.extend(parts[-1:])
            elif collapsed:
                picked.append(collapsed)
        return self._take_short_terms(picked)

    def _pick_domain_terms(self, keywords: List[str]) -> List[str]:
        picked = []
        for keyword in keywords:
            collapsed = self._strip_role_suffix(keyword)
            parts = self._split_compound_keyword(collapsed)
            if len(parts) >= 2:
                picked.extend(parts[:-1])
            elif collapsed and collapsed not in self.STOP_TERMS:
                picked.append(collapsed)
        return self._take_short_terms(picked)

    def _pick_process_terms(self, keywords: List[str]) -> List[str]:
        hints = []
        for keyword in keywords:
            for part in self._split_compound_keyword(keyword):
                if part.endswith(("设计", "开发", "散热", "注塑", "钣金", "压铸", "测试", "制造")):
                    hints.append(part)
        return self._take_short_terms(hints)

    def _pick_object_terms(self, keywords: List[str]) -> List[str]:
        hints = []
        for keyword in keywords:
            for part in self._split_compound_keyword(keyword):
                if part.endswith(("系统", "平台", "产品", "模组", "外壳", "支架", "灯具", "电池")):
                    hints.append(part)
        return self._take_short_terms(hints)

    def _split_query_terms(self, queries: List[str]) -> List[str]:
        terms = []
        for query in queries:
            terms.extend(self._split_compound_keyword(query.replace("+", " ")))
        return terms

    def _split_compound_keyword(self, keyword: str) -> List[str]:
        normalized = self._normalize_keyword(keyword)
        if not normalized:
            return []
        normalized = normalized.replace("/", " ").replace(",", " ").replace("，", " ")
        parts = [part.strip() for part in normalized.split() if part.strip()]
        if parts:
            return parts
        if len(normalized) <= 4:
            return [normalized]
        for suffix in self.ROLE_SUFFIXES:
            if normalized.endswith(suffix):
                normalized = normalized[: -len(suffix)]
                break
        return [part for part in re.split(r"(?<=.{2})(?=.{2,4}$)", normalized) if part]

    def _take_short_terms(self, terms: List[str]) -> List[str]:
        result = []
        seen = set()
        for raw in terms:
            value = self._normalize_keyword(raw)
            if not value or value in seen:
                continue
            if len(value) > 8:
                continue
            if value in self.STOP_TERMS:
                continue
            seen.add(value)
            result.append(value)
        return result[:8]

    def _strip_role_suffix(self, keyword: str) -> str:
        normalized = self._normalize_keyword(keyword)
        for suffix in self.ROLE_SUFFIXES:
            if normalized.endswith(suffix) and len(normalized) > len(suffix):
                return normalized[: -len(suffix)]
        return normalized

    def _normalize_query(self, value: str) -> str:
        parts = self._split_compound_keyword(value)
        return " ".join(self._merge_unique_lists([], parts))

    def _normalize_boolean_query(self, value: str) -> str:
        """Normalize punctuation while preserving executable Boolean syntax."""
        query = self._clean_text(value)
        if not query:
            return ""
        replacements = {
            "（": "(",
            "）": ")",
            "“": '"',
            "”": '"',
            "‘": "'",
            "’": "'",
            "，": " ",
            "；": " ",
            "　": " ",
        }
        for source, target in replacements.items():
            query = query.replace(source, target)
        query = query.replace("+", " AND ")
        query = re.sub(r"\s+", " ", query).strip(" ,;；")
        query = re.sub(r"\b(and|or|not)\b", lambda m: m.group(1).upper(), query, flags=re.IGNORECASE)
        query = re.sub(r"\s+", " ", query).strip()
        return query

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
