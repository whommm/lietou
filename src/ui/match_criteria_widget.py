"""Standalone match criteria confirmation tab."""

import json
import customtkinter as ctk
from tkinter import messagebox
from typing import Callable, Dict, List, Optional

from ..models import MatchCriteria
from .match_criteria_editor import MatchCriteriaEditor


class MatchCriteriaWidget(ctk.CTkFrame):
    """Let users confirm/edit match criteria before candidate capture."""

    PALETTE = {
        "panel": "#ffffff",
        "panel_alt": "#f7faff",
        "border": "#c7d8ff",
        "text": "#10233f",
        "muted": "#60708c",
        "accent": "#4f7cff",
        "accent_hover": "#365df3",
        "secondary": "#eef3ff",
        "secondary_hover": "#dce7ff",
    }

    def __init__(
        self,
        master,
        on_pick_job_history: Optional[Callable] = None,
        on_save: Optional[Callable[[str, dict, MatchCriteria], None]] = None,
        theme: str = "light",
        **kwargs,
    ):
        super().__init__(master, **kwargs)
        self.on_pick_job_history = on_pick_job_history
        self.on_save = on_save
        self.theme = theme
        self.job_options: List[str] = ["请先分析岗位"]
        self.job_data_map: Dict[str, Dict[str, object]] = {}
        self._selected_label = ""
        self._setup_ui()

    def _setup_ui(self):
        colors = self.PALETTE
        self.configure(fg_color="transparent")
        self.grid_columnconfigure(0, weight=2)
        self.grid_columnconfigure(1, weight=5)
        self.grid_rowconfigure(0, weight=1)

        left = ctk.CTkFrame(
            self,
            corner_radius=24,
            fg_color=colors["panel"],
            border_width=1,
            border_color=colors["border"],
        )
        left.grid(row=0, column=0, padx=(10, 6), pady=10, sticky="nsew")
        left.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            left,
            text="关键词匹配",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=colors["text"],
        ).grid(row=0, column=0, padx=16, pady=(16, 4), sticky="w")
        ctk.CTkLabel(
            left,
            text="先确认核心命中词、相邻相关词和排除词，再进入候选人抓取。",
            font=ctk.CTkFont(size=12),
            text_color=colors["muted"],
            justify="left",
            wraplength=300,
        ).grid(row=1, column=0, padx=16, pady=(0, 12), sticky="w")

        self.job_display = ctk.CTkEntry(
            left,
            state="readonly",
            corner_radius=16,
            height=38,
            fg_color=colors["panel_alt"],
            border_color=colors["border"],
            text_color=colors["text"],
        )
        self.job_display.grid(row=2, column=0, padx=16, pady=(8, 8), sticky="ew")

        ctk.CTkButton(
            left,
            text="选择岗位分析",
            height=38,
            corner_radius=18,
            fg_color=colors["secondary"],
            hover_color=colors["secondary_hover"],
            text_color=colors["text"],
            command=self._on_pick_job_click,
        ).grid(row=3, column=0, padx=16, pady=(0, 12), sticky="ew")

        self.status_label = ctk.CTkLabel(
            left,
            text="等待选择岗位。",
            text_color=colors["muted"],
            justify="left",
            wraplength=300,
        )
        self.status_label.grid(row=4, column=0, padx=16, pady=(0, 12), sticky="w")

        right = ctk.CTkFrame(self, fg_color="transparent")
        right.grid(row=0, column=1, padx=(6, 10), pady=10, sticky="nsew")
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(0, weight=1)
        self.editor = MatchCriteriaEditor(
            right,
            criteria=MatchCriteria(),
            on_save=self._on_editor_save,
            theme=self.theme,
        )
        self.editor.grid(row=0, column=0, sticky="nsew")

    def _on_pick_job_click(self):
        if self.on_pick_job_history:
            self.on_pick_job_history()

    def update_job_options(
        self, job_options: List[str], job_data_map: Dict[str, Dict[str, object]]
    ):
        self.job_options = job_options or ["请先分析岗位"]
        self.job_data_map = job_data_map or {}
        if self.job_options:
            self.set_selected_job(self.job_options[0])

    def set_selected_job(self, job_label: str):
        self._selected_label = job_label or ""
        self.job_display.configure(state="normal")
        self.job_display.delete(0, "end")
        self.job_display.insert(0, self._selected_label)
        self.job_display.configure(state="readonly")
        self._load_selected_criteria()

    def _load_selected_criteria(self):
        payload = self.job_data_map.get(self._selected_label, {})
        raw = payload.get("match_criteria", "") if payload else ""
        criteria = None
        if raw:
            try:
                criteria = MatchCriteria.from_dict(json.loads(raw))
            except (ValueError, TypeError):
                criteria = None
        if criteria is None:
            criteria = MatchCriteria()
            self.status_label.configure(text="该岗位还没有已确认的关键词匹配规则，可先在岗位分析页生成后再保存。")
        else:
            self.status_label.configure(text="已加载关键词匹配规则，编辑后点击底部保存。")
        self.editor.set_criteria(criteria, set_as_default=True)

    def _on_editor_save(self, criteria: MatchCriteria):
        payload = self.job_data_map.get(self._selected_label)
        if not payload:
            messagebox.showwarning("提示", "请先选择岗位分析记录")
            return
        if self.on_save:
            self.on_save(self._selected_label, payload, criteria)
        self.status_label.configure(text="关键词匹配规则已保存并确认。")
