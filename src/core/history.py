"""历史记录管理模块"""

import json
import os
import re
import random
import sys
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import List, Optional


@dataclass
class HistoryRecord:
    """历史记录数据类"""

    id: str = ""
    title: str = ""
    jd_text: str = ""
    result: str = ""
    created_at: str = ""
    record_type: str = "job_analysis"  # job_analysis, resume_match, company_research


class HistoryManager:
    """历史记录管理器"""

    # 缓存正则表达式，避免重复编译
    TITLE_PATTERNS = [
        re.compile(r"岗位名称[：:]\s*(.+?)(?:\n|$)"),
        re.compile(r"职位名称[：:]\s*(.+?)(?:\n|$)"),
        re.compile(r"招聘岗位[：:]\s*(.+?)(?:\n|$)"),
        re.compile(r"岗位[：:]\s*(.+?)(?:\n|$)"),
        re.compile(r"职位[：:]\s*(.+?)(?:\n|$)"),
    ]
    HTML_TEXT_PATTERN = re.compile(r"<[^>]+>")
    HTML_JOB_TITLE_PATTERNS = [
        re.compile(r"<h2>[^<]*岗位名称[：:]\s*([^<]+)</h2>"),
        re.compile(r"<p><strong>岗位名称：</strong>\s*([^<]+)</p>"),
        re.compile(r"<p><strong>职位名称：</strong>\s*([^<]+)</p>"),
    ]
    TEXT_JOB_TITLE_PATTERNS = [
        re.compile(r"【岗位名称】(.+?)(?:\n|$)"),
        re.compile(r"岗位名称[：:]\s*(.+?)(?:\n|$)"),
        re.compile(r"职位名称[：:]\s*(.+?)(?:\n|$)"),
    ]
    JOB_TITLE_NOISE_PATTERN = re.compile(
        r"^(岗位职责|职位描述|职位亮点|岗位亮点|任职要求|岗位要求|工作职责|工作内容|公司介绍|公司简介|我们希望你|你将负责)",
        re.IGNORECASE,
    )

    def __init__(self, record_type: str = "job_analysis", max_records: int = 50):
        self.record_type = record_type
        self.history_path = self._get_history_path(record_type)
        self.max_records = max_records
        self.records: List[HistoryRecord] = self._load_history()
        self._enforce_limit()

    def _get_history_path(self, record_type: str) -> str:
        """根据类型获取历史记录文件路径"""
        if getattr(sys, "frozen", False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )

        filename_map = {
            "job_analysis": "history_job_analysis.json",
            "resume_match": "history_resume_match.json",
            "company_research": "history_company_research.json",
        }
        filename = filename_map.get(record_type, "history.json")
        return os.path.join(base_dir, filename)

    def _load_history(self) -> List[HistoryRecord]:
        """从文件加载历史记录"""
        if os.path.exists(self.history_path):
            try:
                with open(self.history_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return [HistoryRecord(**item) for item in data]
            except (json.JSONDecodeError, TypeError, KeyError):
                return []
        return []

    def _save_history(self) -> bool:
        """保存历史记录到文件"""
        try:
            with open(self.history_path, "w", encoding="utf-8") as f:
                json.dump(
                    [asdict(r) for r in self.records], f, ensure_ascii=False, indent=2
                )
            return True
        except IOError:
            return False

    def _enforce_limit(self) -> None:
        """强制执行记录数量限制"""
        if len(self.records) > self.max_records:
            # 保留最新的记录
            self.records = self.records[: self.max_records]
            self._save_history()

    def _truncate_text(self, text: str, limit: int = 30) -> str:
        """截断文本并补省略号。"""
        text = text.strip()
        if len(text) > limit:
            return text[:limit] + "..."
        return text

    def _strip_html(self, text: str) -> str:
        """去除 HTML 标签，保留可读文本。"""
        text = self.HTML_TEXT_PATTERN.sub(" ", text)
        return re.sub(r"\s+", " ", text).strip()

    def _clean_title_candidate(self, text: str) -> str:
        """清洗标题候选值，避免把说明性文本当作岗位名称。"""
        if not text:
            return ""

        cleaned = self._strip_html(text)
        cleaned = re.sub(r"^[\-•*#\s]+", "", cleaned)
        cleaned = re.sub(r"[：:]$", "", cleaned).strip()

        if not cleaned:
            return ""
        if self.JOB_TITLE_NOISE_PATTERN.match(cleaned):
            return ""
        if len(cleaned) > 60:
            return ""
        return cleaned

    def _extract_job_title_from_jd(self, jd_text: str) -> str:
        """优先从原始 JD 中提取岗位名称。"""
        if not jd_text:
            return ""

        for pattern in self.TITLE_PATTERNS:
            match = pattern.search(jd_text)
            if match:
                cleaned = self._clean_title_candidate(match.group(1))
                if cleaned:
                    return self._truncate_text(cleaned, 30)

        lines = [line.strip() for line in jd_text.strip().split("\n") if line.strip()]
        if not lines:
            return ""

        first_line = self._clean_title_candidate(lines[0])
        if first_line and len(first_line) <= 30:
            return first_line

        return ""

    def _extract_job_title_from_result(self, result: str) -> str:
        """从分析结果中提取岗位名称，作为 JD 提取失败后的兜底。"""
        if not result:
            return ""

        for pattern in self.HTML_JOB_TITLE_PATTERNS:
            match = pattern.search(result)
            if match:
                cleaned = self._clean_title_candidate(match.group(1))
                if cleaned:
                    return self._truncate_text(cleaned, 30)

        plain_text = self._strip_html(result)
        for pattern in self.TEXT_JOB_TITLE_PATTERNS:
            match = pattern.search(plain_text)
            if match:
                cleaned = self._clean_title_candidate(match.group(1))
                if cleaned:
                    return self._truncate_text(cleaned, 30)

        return ""

    def _extract_title(self, jd_text: str, result: str = "") -> str:
        """从结果或JD文本中提取标题。"""
        if self.record_type == "company_research":
            if jd_text.startswith("[公司调研] "):
                return self._truncate_text(jd_text.replace("[公司调研] ", "", 1), 30)
            return self._truncate_text(jd_text or "未命名公司", 30)

        if self.record_type == "resume_match":
            title = self._extract_resume_title(jd_text, result)
            if title:
                return title
            return "简历匹配记录"

        title = self._extract_job_title_from_jd(jd_text)
        if title:
            return title

        title = self._extract_job_title_from_result(result)
        if title:
            return title

        if jd_text:
            lines = jd_text.strip().split("\n")
            for line in lines:
                cleaned = self._clean_title_candidate(line)
                if cleaned and len(cleaned) > 2:
                    return self._truncate_text(cleaned, 30)

        return "未命名岗位"

    def _extract_resume_title(self, jd_text: str, result: str = "") -> str:
        """提取简历匹配标题。"""
        match = re.search(r"岗位:\s*(.+?)(?:\.\.\.|\n|$)", jd_text)
        if match:
            return "简历匹配 - {}".format(self._truncate_text(match.group(1), 22))

        stripped = self._strip_html(result)
        if stripped:
            return "简历匹配 - {}".format(self._truncate_text(stripped, 22))
        return ""

    def save_record(self, jd_text: str, result: str) -> HistoryRecord:
        """保存一条新记录"""
        now = datetime.now()
        record = HistoryRecord(
            id=now.strftime("%Y%m%d_%H%M%S_") + str(random.randint(100, 999)),
            title=self._extract_title(jd_text, result),
            jd_text=jd_text,
            result=result,
            created_at=now.strftime("%Y-%m-%d %H:%M:%S"),
            record_type=self.record_type,
        )
        self.records.insert(0, record)
        self._enforce_limit()
        self._save_history()
        return record

    def get_all(self) -> List[HistoryRecord]:
        """获取所有历史记录"""
        return self.records

    def get_by_id(self, record_id: str) -> Optional[HistoryRecord]:
        """按ID获取记录"""
        for record in self.records:
            if record.id == record_id:
                return record
        return None

    def delete(self, record_id: str) -> bool:
        """删除单条记录"""
        for i, record in enumerate(self.records):
            if record.id == record_id:
                self.records.pop(i)
                self._save_history()
                return True
        return False

    def clear(self) -> bool:
        """清空所有历史记录"""
        self.records.clear()
        return self._save_history()

    def export_txt(self, filepath: str) -> bool:
        """导出所有历史记录为TXT文件"""
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                for record in self.records:
                    f.write(f"{'=' * 60}\n")
                    f.write(f"岗位：{record.title}\n")
                    f.write(f"时间：{record.created_at}\n")
                    f.write(f"{'=' * 60}\n\n")
                    f.write(f"【原始JD】\n{record.jd_text}\n\n")
                    f.write(f"【分析结果】\n{record.result}\n\n\n")
            return True
        except IOError:
            return False
