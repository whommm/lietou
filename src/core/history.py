"""历史记录管理模块"""

import json
import os
import re
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


class HistoryManager:
    """历史记录管理器"""

    # 缓存正则表达式，避免重复编译
    TITLE_PATTERNS = [
        re.compile(r'岗位名称[：:]\s*(.+?)(?:\n|$)'),
        re.compile(r'职位名称[：:]\s*(.+?)(?:\n|$)'),
        re.compile(r'招聘岗位[：:]\s*(.+?)(?:\n|$)'),
        re.compile(r'岗位[：:]\s*(.+?)(?:\n|$)'),
        re.compile(r'职位[：:]\s*(.+?)(?:\n|$)'),
    ]

    def __init__(self, history_path: Optional[str] = None, max_records: int = 100):
        if history_path is None:
            self.history_path = self._get_default_history_path()
        else:
            self.history_path = history_path
        self.max_records = max_records  # 最大记录数限制
        self.records: List[HistoryRecord] = self._load_history()
        # 启动时清理超出限制的记录
        self._enforce_limit()

    def _get_default_history_path(self) -> str:
        """获取默认历史记录文件路径"""
        if getattr(os.sys, 'frozen', False):
            base_dir = os.path.dirname(os.sys.executable)
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        return os.path.join(base_dir, "history.json")

    def _load_history(self) -> List[HistoryRecord]:
        """从文件加载历史记录"""
        if os.path.exists(self.history_path):
            try:
                with open(self.history_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return [HistoryRecord(**item) for item in data]
            except (json.JSONDecodeError, TypeError, KeyError):
                return []
        return []

    def _save_history(self) -> bool:
        """保存历史记录到文件"""
        try:
            with open(self.history_path, 'w', encoding='utf-8') as f:
                json.dump([asdict(r) for r in self.records], f, ensure_ascii=False, indent=2)
            return True
        except IOError:
            return False

    def _enforce_limit(self) -> None:
        """强制执行记录数量限制"""
        if len(self.records) > self.max_records:
            # 保留最新的记录
            self.records = self.records[:self.max_records]
            self._save_history()

    def _extract_title(self, jd_text: str, result: str = "") -> str:
        """从结果或JD文本中提取标题（岗位名称）"""
        # 优先从AI结果中提取【岗位名称】
        if result:
            match = re.search(r'【岗位名称】(.+?)(?:\n|$)', result)
            if match:
                title = match.group(1).strip()
                if len(title) > 30:
                    title = title[:30] + "..."
                return title

        # 如果结果中没有，从JD文本中提取
        if not jd_text:
            return "未命名岗位"

        # 使用缓存的正则表达式
        for pattern in self.TITLE_PATTERNS:
            match = pattern.search(jd_text)
            if match:
                title = match.group(1).strip()
                if len(title) > 20:
                    title = title[:20] + "..."
                return title

        lines = jd_text.strip().split('\n')
        for line in lines:
            line = line.strip()
            if line and len(line) > 2:
                if len(line) > 20:
                    return line[:20] + "..."
                return line

        return "未命名岗位"

    def save_record(self, jd_text: str, result: str) -> HistoryRecord:
        """保存一条新记录"""
        now = datetime.now()
        record = HistoryRecord(
            id=now.strftime("%Y%m%d_%H%M%S"),
            title=self._extract_title(jd_text, result),
            jd_text=jd_text,
            result=result,
            created_at=now.strftime("%Y-%m-%d %H:%M:%S")
        )
        self.records.insert(0, record)
        # 保存后强制执行记录数量限制
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
            with open(filepath, 'w', encoding='utf-8') as f:
                for record in self.records:
                    f.write(f"{'='*60}\n")
                    f.write(f"岗位：{record.title}\n")
                    f.write(f"时间：{record.created_at}\n")
                    f.write(f"{'='*60}\n\n")
                    f.write(f"【原始JD】\n{record.jd_text}\n\n")
                    f.write(f"【分析结果】\n{record.result}\n\n\n")
            return True
        except IOError:
            return False
