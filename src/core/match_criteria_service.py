"""Match criteria generation and parsing service."""

import json
import re
from datetime import datetime
from typing import Optional

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
        """Build a usable default when the dedicated API output is malformed."""
        jd_text = (jd_text or "").strip()
        title_hint = jd_text[:80] if jd_text else "目标岗位"
        now = datetime.now().isoformat(timespec="seconds")
        return MatchCriteria(
            dealbreakers=[
                MatchCriterionItem(
                    id="db_1",
                    text="候选人经历与目标岗位方向明显无关",
                    enabled=True,
                    weight=0,
                )
            ],
            core_requirements=[
                MatchCriterionItem(
                    id="cr_1",
                    text="最近经历与岗位核心业务或产品领域相关：{}".format(title_hint),
                    enabled=True,
                    weight=40,
                ),
                MatchCriterionItem(
                    id="cr_2",
                    text="具备岗位要求的主要职责经验，并能在简历中看到可核验证据",
                    enabled=True,
                    weight=35,
                ),
                MatchCriterionItem(
                    id="cr_3",
                    text="年限、学历、城市等基础条件没有明显冲突",
                    enabled=True,
                    weight=25,
                ),
            ],
            basic_requirements=[
                MatchCriterionItem(
                    id="br_1",
                    text="简历信息完整，能看清最近工作经历和职责",
                    enabled=True,
                    weight=0,
                ),
                MatchCriterionItem(
                    id="br_2",
                    text="当前职级或职责范围与岗位大致匹配",
                    enabled=True,
                    weight=0,
                ),
            ],
            bonuses=[
                MatchCriterionItem(
                    id="bo_1",
                    text="有同类公司、同类产品或同类项目经验",
                    enabled=True,
                    weight=0,
                ),
                MatchCriterionItem(
                    id="bo_2",
                    text="简历中出现可量化成果或关键项目案例",
                    enabled=True,
                    weight=0,
                ),
            ],
            misjudgment_reminders=[
                "不要只看职位名称，要看最近 3-5 年实际项目和产品方向。",
                "JD 未明确的信息不要强行判定不匹配，标为待验证。",
            ],
            version=1,
            confirmed_at=now,
        )

    def to_rendered_text(self, criteria: MatchCriteria) -> str:
        """Render criteria into text suitable for batch match prompts."""
        if criteria is None:
            return ""
        lines = []
        for title, items in (
            ("一票否决", criteria.dealbreakers),
            ("核心要求", criteria.core_requirements),
            ("基础要求", criteria.basic_requirements),
            ("加分项", criteria.bonuses),
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
