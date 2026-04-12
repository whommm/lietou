"""Excel read/write service for candidate workflow."""

from __future__ import annotations

import os
import re
from datetime import datetime
from typing import Dict, List, Optional

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill

from ..models import CandidateExcelRecord


class CandidateExcelError(Exception):
    """Raised when Excel read/write fails."""


class CandidateExcelService:
    """Manage workbook creation, row updates, and match result writes."""

    SHEET_NAME = "候选人"
    EXPORT_DIR = os.path.join("exports", "candidates")
    CAPTURE_STATUS_PENDING = "待抓取"
    CAPTURE_STATUS_SUCCESS = "抓取成功"
    CAPTURE_STATUS_FAILED = "抓取失败"
    CAPTURE_STATUS_PARTIAL = "部分成功"
    MATCHABLE_CAPTURE_STATUSES = {CAPTURE_STATUS_SUCCESS, CAPTURE_STATUS_PARTIAL}
    HEADERS = [
        "序号",
        "姓名",
        "年龄",
        "页码",
        "排名",
        "简历链接",
        "简历抓取状态",
        "简历详情",
        "匹配度分数",
        "匹配详情",
        "抓取时间",
        "匹配时间",
    ]
    COLUMN_WIDTHS = {
        "A": 8,
        "B": 14,
        "C": 8,
        "D": 8,
        "E": 8,
        "F": 38,
        "G": 14,
        "H": 80,
        "I": 12,
        "J": 80,
        "K": 20,
        "L": 20,
    }
    HEADER_INDEX = {name: index + 1 for index, name in enumerate(HEADERS)}

    def __init__(self, workspace_root: Optional[str] = None):
        self.workspace_root = workspace_root or os.getcwd()

    @staticmethod
    def now_text() -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def build_filename(job_name: str) -> str:
        normalized = re.sub(r'[\\/:*?"<>|]+', "_", (job_name or "候选人").strip())
        normalized = normalized.strip(" .") or "候选人"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return "{}_{}.xlsx".format(normalized, timestamp)

    def build_export_path(self, job_name: str) -> str:
        export_dir = os.path.join(self.workspace_root, self.EXPORT_DIR)
        os.makedirs(export_dir, exist_ok=True)
        return os.path.join(export_dir, self.build_filename(job_name))

    def create_workbook(self, job_name: str) -> str:
        path = self.build_export_path(job_name)
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = self.SHEET_NAME
        sheet.append(self.HEADERS)
        self._apply_layout(sheet)
        workbook.save(path)
        workbook.close()
        return path

    def append_candidate_row(self, file_path: str, row_data: Dict[str, object]) -> int:
        try:
            workbook = load_workbook(file_path)
            sheet = workbook[self.SHEET_NAME]
            row_index = sheet.max_row + 1
            values = [row_data.get(header, "") for header in self.HEADERS]
            sheet.append(values)
            self._apply_row_style(sheet, row_index)
            workbook.save(file_path)
            workbook.close()
            return row_index
        except PermissionError as exc:
            raise CandidateExcelError(
                "Excel 文件被占用，请关闭后重试：{}".format(file_path)
            ) from exc
        except Exception as exc:
            raise CandidateExcelError(
                "写入 Excel 失败：{}".format(exc)
            ) from exc

    def update_candidate_detail(
        self,
        file_path: str,
        row_index: int,
        resume_text: str,
        capture_status: str,
    ) -> None:
        try:
            workbook = load_workbook(file_path)
            sheet = workbook[self.SHEET_NAME]
            sheet.cell(row=row_index, column=self.HEADER_INDEX["简历详情"]).value = (
                resume_text or ""
            )
            sheet.cell(
                row=row_index, column=self.HEADER_INDEX["简历抓取状态"]
            ).value = capture_status
            workbook.save(file_path)
            workbook.close()
        except PermissionError as exc:
            raise CandidateExcelError(
                "Excel 文件被占用，请关闭后重试：{}".format(file_path)
            ) from exc
        except Exception as exc:
            raise CandidateExcelError(
                "更新 Excel 失败：{}".format(exc)
            ) from exc

    def write_match_result(
        self,
        file_path: str,
        row_index: int,
        tier: Optional[str],
        detail: str,
        matched_at: Optional[str] = None,
    ) -> None:
        try:
            workbook = load_workbook(file_path)
            sheet = workbook[self.SHEET_NAME]
            sheet.cell(row=row_index, column=self.HEADER_INDEX["匹配度分数"]).value = tier
            sheet.cell(row=row_index, column=self.HEADER_INDEX["匹配详情"]).value = (
                detail or ""
            )
            sheet.cell(row=row_index, column=self.HEADER_INDEX["匹配时间"]).value = (
                matched_at or self.now_text()
            )
            workbook.save(file_path)
            workbook.close()
        except PermissionError as exc:
            raise CandidateExcelError(
                "Excel 文件被占用，请关闭后重试：{}".format(file_path)
            ) from exc
        except Exception as exc:
            raise CandidateExcelError(
                "回写匹配结果到 Excel 失败：{}".format(exc)
            ) from exc

    def load_candidates(self, file_path: str) -> List[CandidateExcelRecord]:
        workbook = load_workbook(file_path)
        sheet = workbook[self.SHEET_NAME]
        records = []
        for row_index in range(2, sheet.max_row + 1):
            values = self._row_to_dict(sheet, row_index)
            if not any(
                str(values.get(header) or "").strip() for header in self.HEADERS
            ):
                continue
            records.append(self._build_record(row_index, values))
        workbook.close()
        return records

    def load_matchable_candidates(self, file_path: str) -> List[CandidateExcelRecord]:
        records = []
        for record in self.load_candidates(file_path):
            if (
                record.resume_text or ""
            ).strip() and record.capture_status in self.MATCHABLE_CAPTURE_STATUSES:
                records.append(record)
        return records

    def count_matchable_candidates(self, file_path: str) -> int:
        return len(self.load_matchable_candidates(file_path))

    def _build_record(
        self, row_index: int, values: Dict[str, object]
    ) -> CandidateExcelRecord:
        score_value = values.get("匹配度分数")
        match_score = None
        if score_value not in (None, ""):
            try:
                match_score = int(float(score_value))
            except (TypeError, ValueError):
                match_score = None
        return CandidateExcelRecord(
            row_index=row_index,
            sequence=self._to_int(values.get("序号"), fallback=row_index - 1),
            name=str(values.get("姓名") or ""),
            age=str(values.get("年龄") or ""),
            page_number=self._to_int(values.get("页码")),
            rank_index=self._to_int(values.get("排名")),
            profile_url=str(values.get("简历链接") or ""),
            capture_status=str(values.get("简历抓取状态") or ""),
            resume_text=str(values.get("简历详情") or ""),
            match_score=match_score,
            match_detail=str(values.get("匹配详情") or ""),
            captured_at=str(values.get("抓取时间") or ""),
            matched_at=str(values.get("匹配时间") or ""),
        )

    @staticmethod
    def _to_int(value, fallback: Optional[int] = None) -> Optional[int]:
        if value in (None, ""):
            return fallback
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return fallback

    def _row_to_dict(self, sheet, row_index: int) -> Dict[str, object]:
        data = {}
        for header, column_index in self.HEADER_INDEX.items():
            data[header] = sheet.cell(row=row_index, column=column_index).value
        return data

    def _apply_layout(self, sheet) -> None:
        sheet.freeze_panes = "A2"
        header_fill = PatternFill("solid", fgColor="DCE7FF")
        for cell in sheet[1]:
            cell.font = Font(bold=True)
            cell.fill = header_fill
            cell.alignment = Alignment(vertical="center")
        for column, width in self.COLUMN_WIDTHS.items():
            sheet.column_dimensions[column].width = width

    def _apply_row_style(self, sheet, row_index: int) -> None:
        wrap_columns = [self.HEADER_INDEX["简历详情"], self.HEADER_INDEX["匹配详情"]]
        for column_index in wrap_columns:
            sheet.cell(row=row_index, column=column_index).alignment = Alignment(
                wrap_text=True, vertical="top"
            )
