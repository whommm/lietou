"""Batch match orchestration service."""

import html
import json
import re
from dataclasses import dataclass
from typing import Callable, Iterable, List, Optional

from .llm_client import LLMClient
from .prompt import RESUME_MATCH_PROMPT
from ..models import BatchMatchJob, BatchMatchResult, Candidate, CandidateExcelRecord


@dataclass
class BatchMatchTextResult:
    """Lightweight batch match result for Excel workflow."""

    row_index: int
    candidate_name: str
    score: Optional[int]
    detail: str
    recommendation: str = ""
    summary: str = ""
    risks: str = ""


class BatchMatchService:
    """Coordinate batch match jobs over stored candidates.

    This service intentionally starts as a thin orchestration layer so the data
    flow is fixed early. Later phases can add progress callbacks, cancellation,
    retries, and partial resume without changing its public contract.
    """

    def __init__(
        self,
        repository=None,
        llm_client: Optional[LLMClient] = None,
    ):
        self.repository = repository
        self.llm_client = llm_client

    SCORE_PATTERN = re.compile(r"(\d{1,3})%")
    JSON_BLOCK_PATTERN = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL)
    JSON_OBJECT_PATTERN = re.compile(r"(\{.*\})", re.DOTALL)
    SCORE_TEXT_PATTERN = re.compile(r"(?:匹配度分数|综合匹配度|分数)[:：]?\s*(\d{1,3})")
    RECOMMENDATION_TEXT_PATTERN = re.compile(r"(?:建议动作|推荐结论)[:：]\s*(.+)")
    SUMMARY_TEXT_PATTERN = re.compile(r"(?:一句话结论|总体结论)[:：]\s*(.+)")
    RISKS_TEXT_PATTERN = re.compile(
        r"(?:明确短板|明显短板|关键风险|风险提示)[:：]\s*(.+)"
    )

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
                result = self._match_candidate(batch_job.id, job_description, candidate)
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

    def _match_candidate(
        self, batch_job_id: str, job_description: str, candidate: Candidate
    ) -> BatchMatchResult:
        """Generate a full match report for one candidate."""
        prompt = self._build_batch_match_prompt(
            job_description=job_description,
            resume=candidate.resume_text,
        )
        raw_response = self.llm_client.chat(prompt)
        parsed = self._parse_report(raw_response)
        return BatchMatchResult(
            id="",
            batch_job_id=batch_job_id,
            candidate_id=candidate.id,
            score=parsed["score"],
            recommendation=parsed["recommendation"],
            summary=parsed["summary"],
            risks=parsed["risks"],
            detail=parsed["detail"],
            status="completed",
        )

    def _build_batch_match_prompt(self, job_description: str, resume: str) -> str:
        """Ask the model for plain text structured output first."""
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
                "匹配度分数：<0-100整数>\n"
                "建议动作：<一句话>\n"
                "一句话结论：<一句话>\n"
                "关键风险：<一句话>\n"
                "详细分析：<多行纯文本分析>"
                "严禁输出 HTML、Markdown 代码块、表格或任何富文本标签。"
                "如果某项信息不足，也必须保留字段名并给出简短说明。"
            ),
        )

    def _parse_report(self, report_text: str) -> dict:
        """Extract score and summary fields from text or JSON payloads."""
        parsed_json = self._parse_json_payload(report_text)
        if parsed_json is not None:
            return parsed_json

        source_text = self._normalize_plain_text(report_text or "")
        score_match = self.SCORE_PATTERN.search(
            source_text
        ) or self.SCORE_TEXT_PATTERN.search(source_text)
        action_match = self.RECOMMENDATION_TEXT_PATTERN.search(source_text)
        summary_match = self.SUMMARY_TEXT_PATTERN.search(source_text)
        risks_match = self.RISKS_TEXT_PATTERN.search(source_text)

        score = None
        if score_match:
            try:
                score = max(0, min(100, int(score_match.group(1))))
            except ValueError:
                score = None

        recommendation = (action_match.group(1).strip() if action_match else "").strip()
        summary = (summary_match.group(1).strip() if summary_match else "").strip()
        risks = (risks_match.group(1).strip() if risks_match else "").strip()

        return {
            "score": score,
            "recommendation": recommendation,
            "summary": summary,
            "risks": risks,
            "detail": source_text.strip()
            or self._build_fallback_text(score, recommendation, summary, risks),
        }

    def _parse_json_payload(self, raw_response: str) -> Optional[dict]:
        """Parse a structured JSON response when the model returns one."""
        payload = self._extract_json_text(raw_response or "")
        if not payload:
            return None

        try:
            data = json.loads(payload)
        except (TypeError, ValueError):
            return None

        score = self._normalize_score(data.get("score"))
        recommendation = str(data.get("recommendation") or "").strip()
        summary = str(data.get("summary") or "").strip()
        risks = str(data.get("risks") or "").strip()
        detail = self._normalize_plain_text(str(data.get("detail") or "").strip())
        if not detail:
            detail = self._build_fallback_text(score, recommendation, summary, risks)

        return {
            "score": score,
            "recommendation": recommendation,
            "summary": summary,
            "risks": risks,
            "detail": detail,
        }

    def match_excel_candidates(
        self,
        job_description: str,
        candidates: Iterable[CandidateExcelRecord],
        progress_callback: Optional[
            Callable[[int, int, CandidateExcelRecord], None]
        ] = None,
    ) -> List[BatchMatchTextResult]:
        if self.llm_client is None:
            raise RuntimeError("BatchMatchService requires an LLM client to run jobs")

        candidate_list = list(candidates)
        results = []
        total = len(candidate_list)
        for index, candidate in enumerate(candidate_list, start=1):
            if progress_callback is not None:
                progress_callback(index, total, candidate)
            prompt = self._build_batch_match_prompt(
                job_description=job_description,
                resume=candidate.resume_text,
            )
            raw_response = self.llm_client.chat(prompt)
            parsed = self._parse_report(raw_response)
            results.append(
                BatchMatchTextResult(
                    row_index=candidate.row_index,
                    candidate_name=candidate.name or "未命名候选人",
                    score=parsed.get("score"),
                    detail=parsed.get("detail") or "",
                    recommendation=parsed.get("recommendation") or "",
                    summary=parsed.get("summary") or "",
                    risks=parsed.get("risks") or "",
                )
            )
        return results

    def _extract_json_text(self, raw_response: str) -> str:
        block_match = self.JSON_BLOCK_PATTERN.search(raw_response)
        if block_match:
            return block_match.group(1).strip()

        stripped = raw_response.strip()
        if stripped.startswith("{") and stripped.endswith("}"):
            return stripped

        object_match = self.JSON_OBJECT_PATTERN.search(raw_response)
        if object_match:
            return object_match.group(1).strip()
        return ""

    @staticmethod
    def _normalize_score(value) -> Optional[int]:
        if value is None:
            return None
        text = str(value).strip().rstrip("%")
        if not text:
            return None
        try:
            return max(0, min(100, int(float(text))))
        except ValueError:
            return None

    @staticmethod
    def _normalize_plain_text(text: str) -> str:
        normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
        if not normalized:
            return ""
        normalized = re.sub(
            r"```(?:text|markdown|html)?", "", normalized, flags=re.IGNORECASE
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
        score: Optional[int], recommendation: str, summary: str, risks: str
    ) -> str:
        score_value = score if score is not None else 0
        return ("匹配度分数：{}\n建议动作：{}\n一句话结论：{}\n关键风险：{}").format(
            score_value,
            recommendation or "待解析",
            summary or "待解析",
            risks or "待解析",
        )
