"""Match criteria generation and parsing service."""

import json
import re
from datetime import datetime
from typing import List, Optional

from .llm_client import LLMClient
from .prompt import MATCH_CRITERIA_GENERATION_PROMPT
from ..models import MatchCriteria, MatchCriterionItem


class MatchCriteriaService:
    """Generate stable match criteria from JD and analysis output."""

    JSON_BLOCK_PATTERN = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL)
    JSON_OBJECT_PATTERN = re.compile(r"(\{.*\})", re.DOTALL)

    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    def extract_from_analysis(self, analysis_html: str) -> Optional[MatchCriteria]:
        """Extract a trailing match criteria JSON object from analysis output."""
        raw_json = self._extract_json_text(analysis_html or "")
        if not raw_json:
            return None
        try:
            data = json.loads(raw_json)
            if isinstance(data, dict) and "core_requirements" in data:
                return MatchCriteria.from_dict(data)
        except (TypeError, ValueError):
            return None
        return None

    def generate(self, analysis_html: str, jd_text: str) -> MatchCriteria:
        """Generate criteria with a dedicated LLM call, with a conservative fallback."""
        prompt = (
            MATCH_CRITERIA_GENERATION_PROMPT.replace(
                "{job_description}", jd_text or ""
            ).replace("{analysis_html}", analysis_html or "")
        )
        raw_response = self.llm_client.chat(prompt)
        raw_json = self._extract_json_text(raw_response)
        if raw_json:
            data = json.loads(raw_json)
            criteria = MatchCriteria.from_dict(data)
            errors = criteria.validate()
            if not errors:
                return criteria
        return self.build_fallback(jd_text)

    @staticmethod
    def build_fallback(jd_text: str) -> MatchCriteria:
        """Build keyword-style fallback criteria when API output is malformed."""
        jd_text = (jd_text or "").strip()
        now = datetime.now().isoformat(timespec="seconds")
        core = MatchCriteriaService._pick_terms(
            jd_text,
            ["IP", "潮玩", "文创", "文创衍生品", "衍生品", "玩具", "益智玩具", "科普", "博物馆", "展馆", "展品"],
        )
        adjacent = MatchCriteriaService._pick_terms(
            jd_text,
            ["消费品", "礼品", "儿童产品", "教育产品", "手办", "实体产品", "工业设计", "结构设计", "供应链", "量产"],
        )
        role = MatchCriteriaService._pick_terms(
            jd_text,
            ["产品", "产品设计", "设计总监", "产品总监", "产品负责人", "研发负责人", "设计经理"],
        )
        if not core:
            core = ["目标行业/产品形态关键词", "岗位核心业务场景关键词"]
        if not adjacent:
            adjacent = ["相邻行业产品经验", "实体产品或项目经验"]
        if not role:
            role = ["目标岗位相关职位名或职责词"]
        return MatchCriteria(
            dealbreakers=[
                MatchCriterionItem(
                    id="db_1",
                    text="APP / SaaS / UI / 网页 / 建筑 / 室内 / 服装",
                    enabled=True,
                    weight=0,
                )
            ],
            core_requirements=[
                MatchCriterionItem(
                    id="cr_1",
                    text=" / ".join(core[:6]),
                    enabled=True,
                    weight=0,
                ),
            ],
            basic_requirements=[
                MatchCriterionItem(
                    id="br_1",
                    text=" / ".join(adjacent[:6]),
                    enabled=True,
                    weight=0,
                ),
            ],
            bonuses=[
                MatchCriterionItem(
                    id="bo_1",
                    text=" / ".join(role[:6]),
                    enabled=True,
                    weight=0,
                ),
            ],
            misjudgment_reminders=[
                "没有核心场景词时，不要因为职位名相同就给高档。",
                "相邻相关词只能支持 B 类待验证，不能单独支撑 A。",
                "简历未体现不等于不匹配，标为待验证并给出追问。",
            ],
            version=2,
            confirmed_at=now,
        )

    @staticmethod
    def _pick_terms(text: str, candidates: List[str]) -> List[str]:
        picked = []
        for term in candidates:
            if term and term in text and term not in picked:
                picked.append(term)
        return picked

    def to_rendered_text(self, criteria: MatchCriteria) -> str:
        """Render criteria into text suitable for batch match prompts."""
        if criteria is None:
            return ""
        lines = []
        for title, items in (
            ("排除词 / 负向方向", criteria.dealbreakers),
            ("核心命中词", criteria.core_requirements),
            ("相邻相关词", criteria.basic_requirements),
            ("泛能力/职位参考词", criteria.bonuses),
        ):
            active = [item for item in items if item.enabled]
            if not active:
                continue
            lines.append("【{}】".format(title))
            for item in active:
                suffix = "（权重{}%）".format(item.weight) if item.weight else ""
                lines.append("- {}{}".format(item.text, suffix))
        if criteria.misjudgment_reminders:
            lines.append("【常见误判提醒】")
            lines.extend("- {}".format(item) for item in criteria.misjudgment_reminders)
        return "\n".join(lines)

    def _extract_json_text(self, raw_text: str) -> str:
        block = self.JSON_BLOCK_PATTERN.search(raw_text or "")
        if block:
            return block.group(1).strip()
        stripped = (raw_text or "").strip()
        if stripped.startswith("{") and stripped.endswith("}"):
            return stripped
        match = self.JSON_OBJECT_PATTERN.search(stripped)
        return match.group(1).strip() if match else ""
