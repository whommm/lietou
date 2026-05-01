"""Dedicated LLM generation for executable Liepin search strategy."""

import json
import re
from typing import Dict, List, Optional

from .llm_client import LLMClient
from .prompt import SEARCH_STRATEGY_GENERATION_PROMPT
from .search_strategy_service import SearchStrategy, SearchStrategyService


class SearchStrategyGenerationService:
    """Generate search rounds in a separate API call from the JD analysis."""

    JSON_BLOCK_PATTERN = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL)
    JSON_OBJECT_PATTERN = re.compile(r"(\{.*\})", re.DOTALL)
    NOISE_QUERY_TERMS = {
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

    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client
        self.parser = SearchStrategyService()

    def generate(self, analysis_html: str, jd_text: str) -> SearchStrategy:
        """Generate strategy JSON with the LLM, falling back to local parsing."""
        prompt = SEARCH_STRATEGY_GENERATION_PROMPT.replace(
            "{job_description}", jd_text or ""
        ).replace("{analysis_html}", analysis_html or "")
        raw_response = self.llm_client.chat(prompt)
        raw_json = self._extract_json_text(raw_response)
        if not raw_json:
            return self.build_fallback(analysis_html, jd_text)
        data = json.loads(raw_json)
        strategy = self.build_from_data(data, analysis_html=analysis_html, jd_text=jd_text)
        if strategy.executable_rounds:
            return strategy
        return self.build_fallback(analysis_html, jd_text)

    def build_fallback(self, analysis_html: str, jd_text: str) -> SearchStrategy:
        """Use the legacy parser, then remove generic-only search rounds."""
        strategy = self.parser.build_from_analysis_result(
            "{}\n{}".format(analysis_html or "", jd_text or "")
        )
        strategy.executable_rounds = self._sanitize_rounds(
            strategy.executable_rounds,
            default_position_filter=self._infer_position_filter(
                strategy.precise_keywords + strategy.synonyms
            ),
        )
        return strategy

    def build_from_data(
        self,
        data: Dict[str, object],
        analysis_html: str = "",
        jd_text: str = "",
    ) -> SearchStrategy:
        """Convert dedicated strategy JSON into the shared SearchStrategy model."""
        if not isinstance(data, dict):
            data = {}

        direct_keywords = self._normalize_terms(data.get("direct_keywords", []))
        indirect_keywords = self._normalize_terms(data.get("indirect_keywords", []))
        long_tail_keywords = self._normalize_terms(data.get("long_tail_keywords", []))
        synonyms = self._normalize_terms(data.get("synonyms", []))
        domain_terms = self._normalize_terms(data.get("domain_terms", []))
        capability_terms = self._normalize_terms(data.get("capability_terms", []))
        exclude_terms = self._normalize_terms(data.get("exclude_terms", []))
        position_filter = self._normalize_position_filter(
            str(data.get("position_filter") or "")
        ) or self._infer_position_filter(direct_keywords + synonyms)

        rounds = self._sanitize_rounds(
            data.get("recommended_rounds", []),
            default_position_filter=position_filter,
        )
        if not rounds:
            rounds = self._build_rounds_from_domain_terms(domain_terms + long_tail_keywords, position_filter)

        filters = self.parser.extract_filters_from_analysis(
            "{}\n{}".format(analysis_html or "", jd_text or "")
        )
        filters["活跃度"] = "近一周"

        return SearchStrategy(
            precise_keywords=direct_keywords[:6],
            expansion_keywords=indirect_keywords[:6],
            synonyms=(synonyms or long_tail_keywords)[:6],
            direct_keywords=direct_keywords[:6],
            indirect_keywords=indirect_keywords[:6],
            long_tail_keywords=long_tail_keywords[:6],
            exclude_keywords=exclude_terms[:6],
            source_company_hints=[],
            atomic_terms={
                "domain_terms": domain_terms[:8],
                "capability_terms": capability_terms[:8],
                "process_terms": [],
                "object_terms": [],
                "exclude_terms": exclude_terms[:8],
            },
            executable_rounds=rounds[:4],
            filters=filters,
        )

    def _build_rounds_from_domain_terms(
        self, terms: List[str], position_filter: str
    ) -> List[Dict[str, object]]:
        scene_queries = self.parser._build_precise_scene_queries(
            self.parser._short_search_terms(terms)
        )
        return self._sanitize_rounds(
            [
                {
                    "label": "第{}轮场景".format(index + 1),
                    "query": query,
                    "intent": "精准行业/业务场景",
                    "position_filter": position_filter,
                }
                for index, query in enumerate(scene_queries[:4])
            ],
            default_position_filter=position_filter,
        )

    def _sanitize_rounds(
        self, raw_rounds: object, default_position_filter: str = ""
    ) -> List[Dict[str, object]]:
        if not isinstance(raw_rounds, list):
            return []
        rounds = []
        seen = set()
        for index, item in enumerate(raw_rounds, start=1):
            if isinstance(item, dict):
                raw_query = str(item.get("query") or "")
                position_filter = self._normalize_position_filter(
                    str(item.get("position_filter") or "")
                ) or default_position_filter
                label = str(item.get("label") or item.get("intent") or "第{}轮场景".format(index))
                intent = str(item.get("intent") or label)
                match_mode = str(item.get("match_mode") or "all")
                scope = str(item.get("scope") or "全部经历")
            else:
                raw_query = str(item or "")
                position_filter = default_position_filter
                label = "第{}轮场景".format(index)
                intent = "精准行业/业务场景"
                match_mode = "all"
                scope = "全部经历"

            query = self._normalize_search_bar_query(raw_query, position_filter)
            if not query or query in seen or self._is_noise_only_query(query):
                continue
            seen.add(query)
            rounds.append(
                {
                    "label": label,
                    "query": query,
                    "intent": intent,
                    "priority": len(rounds) + 1,
                    "match_mode": "all" if match_mode not in ("all", "any") else match_mode,
                    "scope": scope or "全部经历",
                    "position_filter": position_filter,
                }
            )
            if len(rounds) >= 4:
                break
        return rounds

    def _normalize_search_bar_query(self, query: str, position_filter: str = "") -> str:
        normalized = self.parser._normalize_liepin_query(query or "")
        if not normalized:
            return ""
        tokens = [token for token in normalized.split() if token]
        if position_filter:
            tokens = [token for token in tokens if token != position_filter]
        if any(token not in self.NOISE_QUERY_TERMS for token in tokens):
            tokens = [token for token in tokens if token not in {position_filter, "产品", "设计"}]
        return " ".join(tokens).strip()

    def _is_noise_only_query(self, query: str) -> bool:
        tokens = [token for token in (query or "").split() if token]
        if not tokens:
            return True
        return all(token in self.NOISE_QUERY_TERMS for token in tokens)

    def _normalize_terms(self, value: object) -> List[str]:
        if not isinstance(value, list):
            return []
        result = []
        for item in value:
            if not isinstance(item, str):
                continue
            normalized = self.parser._normalize_keyword(item)
            if normalized and normalized not in result:
                result.append(normalized)
        return result

    @staticmethod
    def _normalize_position_filter(value: str) -> str:
        value = (value or "").strip()
        if not value:
            return ""
        if "产品" in value:
            return "产品"
        if "运营" in value:
            return "运营"
        if "销售" in value:
            return "销售"
        if "算法" in value:
            return "算法"
        if "结构" in value:
            return "结构"
        if "研发" in value:
            return "研发"
        return value[:8]

    def _infer_position_filter(self, terms: List[str]) -> str:
        joined = " ".join(terms or [])
        if "产品" in joined:
            return "产品"
        if "运营" in joined:
            return "运营"
        if "销售" in joined:
            return "销售"
        if "算法" in joined:
            return "算法"
        if "结构" in joined:
            return "结构"
        if "研发" in joined:
            return "研发"
        return "产品"

    def _extract_json_text(self, raw_text: str) -> str:
        block = self.JSON_BLOCK_PATTERN.search(raw_text or "")
        if block:
            return block.group(1).strip()
        stripped = (raw_text or "").strip()
        if stripped.startswith("{") and stripped.endswith("}"):
            return stripped
        match = self.JSON_OBJECT_PATTERN.search(stripped)
        return match.group(1).strip() if match else ""
