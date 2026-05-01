"""Batch match orchestration service."""

import html
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Callable, Iterable, List, Optional

from .llm_client import LLMClient
from .prompt import BATCH_MATCH_PROMPT, RESUME_MATCH_PROMPT
from ..models import (
    BatchMatchJob,
    BatchMatchResult,
    Candidate,
    CandidateExcelRecord,
    MatchCriteria,
)


@dataclass
class BatchMatchTextResult:
    """Lightweight batch match result for Excel workflow (tier-based)."""

    row_index: int
    candidate_name: str
    tier: Optional[str]
    core_met_count: int
    core_total: int
    dealbreaker_hit: bool
    detail: str
    recommendation: str = ""
    summary: str = ""
    risks: str = ""
    inferred_abilities: str = ""


class BatchMatchService:
    """Coordinate batch match jobs over stored candidates.

    This service intentionally starts as a thin orchestration layer so the data
    flow is fixed early. Later phases can add progress callbacks, cancellation,
    retries, and partial resume without changing its public contract.
    """

    MAX_WORKERS = 10
    DEFAULT_WORKERS = 5

    def __init__(
        self,
        repository=None,
        llm_client: Optional[LLMClient] = None,
        llm_client_factory: Optional[Callable[[], LLMClient]] = None,
        max_workers: int = DEFAULT_WORKERS,
    ):
        self.repository = repository
        self.llm_client = llm_client
        self.llm_client_factory = llm_client_factory
        self.max_workers = max(1, min(self.MAX_WORKERS, max_workers))

    JSON_BLOCK_PATTERN = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL)
    JSON_OBJECT_PATTERN = re.compile(r"(\{.*\})", re.DOTALL)
    RECOMMENDATION_TEXT_PATTERN = re.compile(r"(?:建议动作|推荐结论)[:：]\s*(.+)")
    SUMMARY_TEXT_PATTERN = re.compile(r"(?:一句话结论|总体结论)[:：]\s*(.+)")
    RISKS_TEXT_PATTERN = re.compile(
        r"(?:明确短板|明显短板|关键风险|风险提示)[:：]\s*(.+)"
    )
    TIER_TEXT_PATTERN = re.compile(r"档位判定[：:]\s*([ABCD])")
    CORE_MET_TEXT_PATTERN = re.compile(r"(?:核心要求符合数|核心命中数)[：:]\s*(\d+)\s*/\s*(\d+)")
    PRE_CODE_PATTERN = re.compile(r"<(?:pre|code)[^>]*>(.*?)</(?:pre|code)>", re.DOTALL | re.IGNORECASE)

    def create_job(
        self,
        job_history_id: str,
        candidates: Iterable[Candidate],
        search_task_id: Optional[str] = None,
    ) -> BatchMatchJob:
        """Create a persisted batch job for the provided candidate set."""
        candidate_list = list(candidates)
        if self.repository is None:
            return BatchMatchJob(
                id="memory-job",
                job_history_id=job_history_id,
                search_task_id=search_task_id,
                candidate_count=len(candidate_list),
                status="pending",
            )
        return self.repository.create_job(
            job_history_id=job_history_id,
            candidate_ids=[candidate.id for candidate in candidate_list],
            search_task_id=search_task_id,
            candidate_count=len(candidate_list),
        )

    def run_job(
        self,
        batch_job: BatchMatchJob,
        job_description: str,
        candidates: Iterable[Candidate],
        match_criteria: Optional[MatchCriteria] = None,
        progress_callback: Optional[Callable[[int, int, Candidate], None]] = None,
    ) -> List[BatchMatchResult]:
        """Run matching for all candidates in sequence."""
        if self.llm_client is None:
            raise RuntimeError("BatchMatchService requires an LLM client to run jobs")

        results = []
        candidate_list = list(candidates)
        try:
            if self.repository is not None:
                self.repository.update_job_status(
                    batch_job.id, "running", mark_started=True
                )
            total = len(candidate_list)
            for index, candidate in enumerate(candidate_list, start=1):
                if progress_callback is not None:
                    progress_callback(index, total, candidate)
                result = self._match_candidate(
                    batch_job.id, job_description, candidate, match_criteria
                )
                if self.repository is not None:
                    result = self.repository.save_result(result)
                results.append(result)
            if self.repository is not None:
                self.repository.update_job_status(
                    batch_job.id, "completed", mark_finished=True
                )
            return results
        except Exception as exc:
            if self.repository is not None:
                self.repository.update_job_status(
                    batch_job.id,
                    "failed",
                    error_message=str(exc),
                    mark_finished=True,
                )
            raise

    @staticmethod
    def _is_resume_effectively_empty(resume: str) -> bool:
        """Quick heuristic to detect truly empty/invalid resumes."""
        if not resume:
            return True
        stripped = resume.strip()
        if len(stripped) < 50:
            return True

        # Liepin navigation noise markers (common in failed extractions)
        nav_markers = [
            "我的主页", "个人中心", "安全中心", "账户资源",
            "用户规则", "通话管理", "安全退出", "候选人基础信息",
        ]
        nav_hits = sum(1 for marker in nav_markers if marker in stripped)

        # Career-related keywords
        career_keywords = [
            "工作", "经历", "公司", "任职", "职责", "业绩", "项目",
            "学历", "学校", "大学", "专业", "毕业", "本科", "大专", "硕士", "博士",
            "技能", "熟悉", "掌握", "精通", "开发", "设计", "负责",
            "职位", "岗位", "行业", "产品", "技术", "研发", "工程师",
        ]
        career_hits = sum(1 for kw in career_keywords if kw in stripped)

        # Heavy on navigation noise but light on career substance -> invalid
        if nav_hits >= 3 and career_hits <= 2:
            return True

        if career_hits == 0:
            return True

        return False

    def _build_invalid_match_result(self, candidate) -> BatchMatchTextResult:
        """Return a tier-C result for an invalid resume without calling LLM."""
        return BatchMatchTextResult(
            row_index=getattr(candidate, "row_index", 0),
            candidate_name=getattr(candidate, "name", "未命名候选人") or "未命名候选人",
            tier="C",
            core_met_count=0,
            core_total=0,
            dealbreaker_hit=True,
            detail="候选人简历信息缺失或抓取失败，无法进行有效评估。",
            recommendation="暂不建议推进",
            summary="简历内容无效，不满足基本评估条件",
            risks="简历为空或仅包含页面无关信息",
            inferred_abilities="",
        )

    def _match_candidate(
        self,
        batch_job_id: str,
        job_description: str,
        candidate: Candidate,
        match_criteria: Optional[MatchCriteria] = None,
    ) -> BatchMatchResult:
        """Generate a full match report for one candidate."""
        if self._is_resume_effectively_empty(candidate.resume_text):
            return BatchMatchResult(
                id="",
                batch_job_id=batch_job_id,
                candidate_id=candidate.id,
                score=None,
                tier="C",
                core_met_count=0,
                core_total=0,
                dealbreaker_hit=True,
                recommendation="暂不建议推进",
                summary="简历内容无效，不满足基本评估条件",
                risks="简历为空或仅包含页面无关信息",
                detail="候选人简历信息缺失或抓取失败，无法进行有效评估。",
                status="completed",
            )
        prompt = self._build_batch_match_prompt(
            job_description=job_description,
            resume=candidate.resume_text,
            match_criteria=match_criteria,
        )
        raw_response = self.llm_client.chat(prompt)
        parsed = self._parse_report(raw_response)
        return BatchMatchResult(
            id="",
            batch_job_id=batch_job_id,
            candidate_id=candidate.id,
            score=None,
            tier=parsed.get("tier"),
            core_met_count=parsed.get("core_met_count", 0),
            core_total=parsed.get("core_total", 0),
            dealbreaker_hit=parsed.get("dealbreaker_hit", False),
            recommendation=parsed.get("recommendation", ""),
            summary=parsed.get("summary", ""),
            risks=parsed.get("risks", ""),
            detail=parsed.get("detail", ""),
            status="completed",
        )

    def _build_batch_match_prompt(
        self,
        job_description: str,
        resume: str,
        match_criteria: Optional[MatchCriteria] = None,
    ) -> str:
        """Ask the model for structured output using MatchCriteria when available."""
        if match_criteria is not None:
            rendered = "{}\n\n{}".format(
                self._render_criteria(match_criteria),
                self._render_keyword_prescan(match_criteria, resume),
            )
            return BATCH_MATCH_PROMPT.format(
                rendered_criteria=rendered,
                resume=resume,
            )

        # Fallback to legacy prompt for backward compatibility
        base_prompt = RESUME_MATCH_PROMPT.format(
            job_description=job_description,
            resume=resume,
        )
        return "{}\n\n{}".format(
            base_prompt,
            (
                "【额外输出要求】\n"
                "你必须只输出纯文本，不要输出 JSON、HTML、Markdown 代码块、表格或任何富文本标签。"
                "请严格按以下格式输出：\n"
                "建议动作：<一句话>\n"
                "一句话结论：<一句话>\n"
                "关键风险：<一句话>\n"
                "档位判定：<A/B/C/D 之一>\n"
                "核心命中数：<数字>/<数字>\n"
                "详细分析：<多行纯文本分析>"
                "严禁输出 HTML、Markdown 代码块、表格或任何富文本标签。"
                "如果某项信息不足，也必须保留字段名并给出简短说明。"
            ),
        )

    @staticmethod
    def _render_criteria(match_criteria: MatchCriteria) -> str:
        """Render MatchCriteria into a human-readable text block for the prompt."""
        lines: List[str] = []

        lines.append("<排除词 / 负向方向>")
        if match_criteria.dealbreakers:
            for item in match_criteria.dealbreakers:
                flag = "启用" if item.enabled else "禁用"
                lines.append(f"- [{'x' if item.enabled else ' '}] {item.text} [{flag}]")
        else:
            lines.append("- 无")

        lines.append("\n<核心命中词>")
        active_core = [c for c in match_criteria.core_requirements if c.enabled]
        if active_core:
            for item in active_core:
                lines.append(f"- {item.text}")
        else:
            lines.append("- 无")

        lines.append("\n<相邻相关词>")
        if match_criteria.basic_requirements:
            for item in match_criteria.basic_requirements:
                lines.append(f"- {item.text}")
        else:
            lines.append("- 无")

        lines.append("\n<泛能力/职位参考词>")
        if match_criteria.bonuses:
            for item in match_criteria.bonuses:
                lines.append(f"- {item.text}")
        else:
            lines.append("- 无")

        lines.append("\n<常见误判提醒 - 匹配时严格遵守>")
        if match_criteria.misjudgment_reminders:
            for reminder in match_criteria.misjudgment_reminders:
                lines.append(f"- {reminder}")
        else:
            lines.append("- 无")

        return "\n".join(lines)

    @classmethod
    def _render_keyword_prescan(cls, match_criteria: MatchCriteria, resume: str) -> str:
        """Render deterministic keyword hits as a hint for the LLM."""
        resume = resume or ""
        sections = [
            ("排除词命中", match_criteria.dealbreakers),
            ("核心命中词命中", match_criteria.core_requirements),
            ("相邻相关词命中", match_criteria.basic_requirements),
            ("泛能力/职位参考词命中", match_criteria.bonuses),
        ]
        lines = ["<系统预扫描命中 - 仅供参考，最终仍需结合上下文判断>"]
        for title, items in sections:
            hits = []
            for item in items or []:
                if not item.enabled:
                    continue
                for keyword in cls._split_keyword_item(item.text):
                    if keyword and keyword in resume and keyword not in hits:
                        hits.append(keyword)
            lines.append("- {}：{}".format(title, " / ".join(hits) if hits else "未发现"))
        return "\n".join(lines)

    @staticmethod
    def _split_keyword_item(text: str) -> List[str]:
        parts = re.split(r"[/／、,，;；\s]+", text or "")
        result = []
        for part in parts:
            value = part.strip(" ：:()（）[]【】")
            if len(value) >= 2 and value not in result:
                result.append(value)
        return result

    @staticmethod
    def _strip_legacy_score_lines(text: str) -> str:
        """Remove legacy total-score/tier lines that the LLM may still emit."""
        text = re.sub(
            r"^[ \t]*(?:匹配度分数|综合匹配度|总分|分数)[：:]?\s*\d+.*?\n",
            "",
            text,
            flags=re.MULTILINE,
        )
        text = re.sub(
            r"^[ \t]*档位判定[：:]?\s*[ABCD].*?\n",
            "",
            text,
            flags=re.MULTILINE,
        )
        text = re.sub(
            r"^[ \t]*(?:核心要求符合数|核心命中数)[：:]?\s*\d+\s*/\s*\d+.*?\n",
            "",
            text,
            flags=re.MULTILINE,
        )
        return text

    @staticmethod
    def _normalize_tier(value) -> Optional[str]:
        if value is None:
            return None
        text = str(value).strip().upper()
        if text in ("A", "B", "C", "D"):
            return text
        return None

    def _parse_report(self, report_text: str) -> dict:
        """Extract tier and summary fields from text or JSON payloads."""
        parsed_json = self._parse_json_payload(report_text)
        if parsed_json is not None:
            # Sanitize detail before returning
            parsed_json["detail"] = self._strip_legacy_score_lines(
                parsed_json["detail"]
            ).strip()
            return parsed_json

        source_text = self._normalize_plain_text(report_text or "")
        tier_match = self.TIER_TEXT_PATTERN.search(source_text)
        core_met_match = self.CORE_MET_TEXT_PATTERN.search(source_text)
        action_match = self.RECOMMENDATION_TEXT_PATTERN.search(source_text)
        summary_match = self.SUMMARY_TEXT_PATTERN.search(source_text)
        risks_match = self.RISKS_TEXT_PATTERN.search(source_text)

        tier = self._normalize_tier(tier_match.group(1)) if tier_match else None
        core_met_count = 0
        core_total = 0
        if core_met_match:
            try:
                core_met_count = int(core_met_match.group(1))
                core_total = int(core_met_match.group(2))
            except ValueError:
                pass

        recommendation = (action_match.group(1).strip() if action_match else "").strip()
        summary = (summary_match.group(1).strip() if summary_match else "").strip()
        risks = (risks_match.group(1).strip() if risks_match else "").strip()

        detail = self._strip_legacy_score_lines(source_text).strip()
        if not detail:
            detail = self._build_fallback_text(tier, recommendation, summary, risks)

        return {
            "tier": tier,
            "core_met_count": core_met_count,
            "core_total": core_total,
            "dealbreaker_hit": tier in ("C", "D") if tier else False,
            "recommendation": recommendation,
            "summary": summary,
            "risks": risks,
            "detail": detail,
            "inferred_abilities": "",
        }

    def _parse_json_payload(self, raw_response: str) -> Optional[dict]:
        """Parse a structured JSON response when the model returns one."""
        payload = self._extract_json_text(raw_response or "")
        if not payload:
            return None

        # Try to locate the extracted JSON in the original response so we can
        # keep the free-form analysis text that precedes it.
        json_start = raw_response.find(payload)
        preceding_text = ""
        if json_start != -1:
            preceding_text = raw_response[:json_start].strip()

        try:
            data = json.loads(payload)
        except (TypeError, ValueError):
            return None

        tier = self._normalize_tier(data.get("tier"))
        dealbreaker_hit = bool(data.get("dealbreaker_hit"))
        core_met_count = data.get("core_met_count", 0)
        core_total = data.get("core_total", 0)
        if isinstance(core_met_count, str):
            try:
                core_met_count = int(core_met_count)
            except ValueError:
                core_met_count = 0
        if isinstance(core_total, str):
            try:
                core_total = int(core_total)
            except ValueError:
                core_total = 0
        recommendation = str(data.get("recommendation") or "").strip()
        summary = str(data.get("summary") or "").strip()
        risks = str(data.get("risks") or "").strip()
        detail = self._normalize_plain_text(str(data.get("detail") or "").strip())
        inferred_abilities = str(data.get("inferred_abilities") or "").strip()
        if not detail and preceding_text:
            detail = self._normalize_plain_text(preceding_text)
        if not detail:
            detail = self._build_fallback_text(tier, recommendation, summary, risks)

        return {
            "tier": tier,
            "core_met_count": core_met_count,
            "core_total": core_total,
            "dealbreaker_hit": dealbreaker_hit,
            "recommendation": recommendation,
            "summary": summary,
            "risks": risks,
            "detail": detail,
            "inferred_abilities": inferred_abilities,
        }

    def _match_single_excel_candidate(
        self,
        candidate: CandidateExcelRecord,
        job_description: str,
        match_criteria: Optional[MatchCriteria],
    ) -> BatchMatchTextResult:
        """Match one candidate using an isolated LLM client instance."""
        if self._is_resume_effectively_empty(candidate.resume_text):
            return self._build_invalid_match_result(candidate)

        client = (
            self.llm_client_factory()
            if self.llm_client_factory
            else self.llm_client
        )
        if client is None:
            raise RuntimeError("BatchMatchService requires an LLM client to run jobs")

        prompt = self._build_batch_match_prompt(
            job_description=job_description,
            resume=candidate.resume_text,
            match_criteria=match_criteria,
        )
        raw_response = client.chat(prompt)
        parsed = self._parse_report(raw_response)
        return BatchMatchTextResult(
            row_index=candidate.row_index,
            candidate_name=candidate.name or "未命名候选人",
            tier=parsed.get("tier"),
            core_met_count=parsed.get("core_met_count", 0),
            core_total=parsed.get("core_total", 0),
            dealbreaker_hit=parsed.get("dealbreaker_hit", False),
            detail=parsed.get("detail") or "",
            recommendation=parsed.get("recommendation") or "",
            summary=parsed.get("summary") or "",
            risks=parsed.get("risks") or "",
            inferred_abilities=parsed.get("inferred_abilities") or "",
        )

    def match_excel_candidates(
        self,
        job_description: str,
        candidates: Iterable[CandidateExcelRecord],
        match_criteria: Optional[MatchCriteria] = None,
        progress_callback: Optional[
            Callable[[int, int, CandidateExcelRecord], None]
        ] = None,
    ) -> List[BatchMatchTextResult]:
        candidate_list = list(candidates)
        total = len(candidate_list)
        if total == 0:
            return []

        # Validate client availability upfront
        if self.llm_client is None and self.llm_client_factory is None:
            raise RuntimeError("BatchMatchService requires an LLM client to run jobs")

        results: List[Optional[BatchMatchTextResult]] = [None] * total
        completed_count = 0

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_index = {
                executor.submit(
                    self._match_single_excel_candidate,
                    candidate,
                    job_description,
                    match_criteria,
                ): idx
                for idx, candidate in enumerate(candidate_list)
            }

            for future in as_completed(future_to_index):
                idx = future_to_index[future]
                try:
                    result = future.result()
                except Exception as exc:
                    # Gracefully wrap worker exceptions into a failed result
                    candidate = candidate_list[idx]
                    result = BatchMatchTextResult(
                        row_index=candidate.row_index,
                        candidate_name=candidate.name or "未命名候选人",
                        tier=None,
                        core_met_count=0,
                        core_total=0,
                        dealbreaker_hit=False,
                        detail=f"处理失败：{exc}",
                        recommendation="处理失败",
                        summary="",
                        risks="",
                        inferred_abilities="",
                    )
                results[idx] = result
                completed_count += 1
                if progress_callback is not None:
                    progress_callback(completed_count, total, candidate_list[idx])

        return [r for r in results if r is not None]

    def _extract_json_text(self, raw_response: str) -> str:
        block_match = self.JSON_BLOCK_PATTERN.search(raw_response)
        if block_match:
            return block_match.group(1).strip()

        pre_match = self.PRE_CODE_PATTERN.search(raw_response)
        if pre_match:
            candidate = pre_match.group(1).strip()
            if candidate.startswith("{") and candidate.endswith("}"):
                return candidate

        stripped = raw_response.strip()
        if stripped.startswith("{") and stripped.endswith("}"):
            return stripped

        object_match = self.JSON_OBJECT_PATTERN.search(raw_response)
        if object_match:
            return object_match.group(1).strip()
        return ""

    @staticmethod
    def _normalize_plain_text(text: str) -> str:
        normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
        if not normalized:
            return ""
        normalized = re.sub(
            r"```(?:json|text|markdown|html)?", "", normalized, flags=re.IGNORECASE
        )
        normalized = normalized.replace("```", "")
        normalized = re.sub(r"<br\s*/?>", "\n", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"</p\s*>", "\n", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"<[^>]+>", "", normalized)
        normalized = html.unescape(normalized)
        normalized = re.sub(r"\n{3,}", "\n\n", normalized)
        return normalized.strip()

    @staticmethod
    def _build_fallback_text(
        tier: Optional[str], recommendation: str, summary: str, risks: str
    ) -> str:
        return ("档位判定：{}\n建议动作：{}\n一句话结论：{}\n关键风险：{}").format(
            tier or "待解析",
            recommendation or "待解析",
            summary or "待解析",
            risks or "待解析",
        )
