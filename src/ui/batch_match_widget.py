"""Batch match UI for candidate ranking and report review."""

import customtkinter as ctk
from tkinter import messagebox
from typing import Callable, Dict, List, Optional

from .html_renderer import HtmlRenderer


class BatchMatchWidget(ctk.CTkFrame):
    """Batch match workspace."""

    PALETTE = {
        "light": {
            "panel": ("#ffffff", "#ffffff"),
            "panel_alt": ("#f7faff", "#f7faff"),
            "border": ("#c7d8ff", "#c7d8ff"),
            "text": ("#10233f", "#10233f"),
            "muted": ("#60708c", "#60708c"),
            "accent": ("#4f7cff", "#4f7cff"),
            "accent_hover": ("#365df3", "#365df3"),
            "secondary": ("#eef3ff", "#eef3ff"),
            "secondary_hover": ("#dce7ff", "#dce7ff"),
        },
        "dark": {
            "panel": ("#f7faff", "#0f1d31"),
            "panel_alt": ("#ffffff", "#142640"),
            "border": ("#c7d8ff", "#294166"),
            "text": ("#10233f", "#f5f7ff"),
            "muted": ("#60708c", "#92a3c7"),
            "accent": ("#4f7cff", "#6d8cff"),
            "accent_hover": ("#365df3", "#8f63ff"),
            "secondary": ("#e6efff", "#17283e"),
            "secondary_hover": ("#d3e2ff", "#243956"),
        },
    }

    def __init__(
        self,
        master,
        on_run_batch: Callable,
        on_pick_job_history: Optional[Callable] = None,
        theme: str = "light",
        **kwargs,
    ):
        super().__init__(master, **kwargs)
        self.on_run_batch = on_run_batch
        self.on_pick_job_history = on_pick_job_history
        self.theme = theme
        self.job_options: List[str] = ["请先分析岗位"]
        self.job_data_map: Dict[str, Dict[str, object]] = {}
        self.candidate_options: List[str] = []
        self.candidate_data_map: Dict[str, Dict[str, str]] = {}
        self.result_data_map: Dict[str, Dict[str, str]] = {}

        self._setup_ui()

    def _setup_ui(self):
        self.configure(fg_color="transparent")
        self.grid_columnconfigure(0, weight=2)
        self.grid_columnconfigure(1, weight=3)
        self.grid_rowconfigure(0, weight=1)

        self._build_control_panel()
        self._build_result_panel()

    def _build_control_panel(self):
        colors = self.PALETTE[self.theme]
        frame = ctk.CTkFrame(
            self,
            corner_radius=24,
            fg_color=colors["panel"],
            border_width=1,
            border_color=colors["border"],
        )
        frame.grid(row=0, column=0, padx=(10, 5), pady=10, sticky="nsew")
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(7, weight=1)

        ctk.CTkLabel(
            frame,
            text="批量匹配工作台",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=colors["text"],
        ).grid(row=0, column=0, padx=16, pady=(16, 5), sticky="w")
        ctk.CTkLabel(
            frame,
            text="选择岗位与候选人集合，批量生成排序结果和单人匹配报告。",
            font=ctk.CTkFont(size=12),
            text_color=colors["muted"],
        ).grid(row=1, column=0, padx=16, pady=(0, 12), sticky="w")

        ctk.CTkLabel(frame, text="目标岗位:", text_color=colors["text"]).grid(
            row=2, column=0, padx=16, pady=(8, 6), sticky="w"
        )
        job_row = ctk.CTkFrame(frame, fg_color="transparent")
        job_row.grid(row=3, column=0, padx=16, pady=(0, 10), sticky="ew")
        job_row.grid_columnconfigure(0, weight=1)

        self.job_combo = ctk.CTkComboBox(
            job_row,
            values=self.job_options,
            corner_radius=16,
            height=38,
            fg_color=colors["panel_alt"],
            border_color=colors["border"],
            button_color=colors["accent"],
            button_hover_color=colors["accent_hover"],
            dropdown_fg_color=colors["panel_alt"],
            dropdown_hover_color=colors["secondary_hover"],
            dropdown_text_color=colors["text"],
            text_color=colors["text"],
        )
        self.job_combo.grid(row=0, column=0, sticky="ew")

        self.pick_job_btn = ctk.CTkButton(
            job_row,
            text="从历史选择",
            width=112,
            height=38,
            corner_radius=18,
            fg_color=colors["secondary"],
            hover_color=colors["secondary_hover"],
            text_color=colors["text"],
            command=self._on_pick_job_click,
        )
        self.pick_job_btn.grid(row=0, column=1, padx=(10, 0), sticky="e")

        ctk.CTkLabel(frame, text="候选人预览:", text_color=colors["text"]).grid(
            row=4, column=0, padx=16, pady=(6, 6), sticky="w"
        )
        self.candidate_box = ctk.CTkTextbox(
            frame,
            height=220,
            wrap="word",
            corner_radius=18,
            border_width=1,
            border_color=colors["border"],
            fg_color=colors["panel_alt"],
            text_color=colors["text"],
            scrollbar_button_color=colors["accent"],
            scrollbar_button_hover_color=colors["accent_hover"],
        )
        self.candidate_box.grid(row=5, column=0, padx=16, pady=(0, 10), sticky="nsew")

        self.run_batch_btn = ctk.CTkButton(
            frame,
            text="开始批量匹配",
            height=40,
            corner_radius=20,
            fg_color=colors["accent"],
            hover_color=colors["accent_hover"],
            text_color="#f8fbff",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._on_run_batch_click,
        )
        self.run_batch_btn.grid(row=6, column=0, padx=16, pady=(0, 12), sticky="ew")

        self.info_label = ctk.CTkLabel(
            frame,
            text="等待选择岗位与候选人集合。",
            text_color=colors["muted"],
            font=ctk.CTkFont(size=12),
            justify="left",
            wraplength=360,
        )
        self.info_label.grid(row=7, column=0, padx=16, pady=(0, 16), sticky="nw")

    def _build_result_panel(self):
        colors = self.PALETTE[self.theme]
        frame = ctk.CTkFrame(
            self,
            corner_radius=24,
            fg_color=colors["panel"],
            border_width=1,
            border_color=colors["border"],
        )
        frame.grid(row=0, column=1, padx=(5, 10), pady=10, sticky="nsew")
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=2)
        frame.grid_rowconfigure(3, weight=3)

        ctk.CTkLabel(
            frame,
            text="匹配排序结果",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=colors["text"],
        ).grid(row=0, column=0, padx=16, pady=(16, 8), sticky="w")

        self.result_box = ctk.CTkTextbox(
            frame,
            wrap="word",
            corner_radius=18,
            border_width=1,
            border_color=colors["border"],
            fg_color=colors["panel_alt"],
            text_color=colors["text"],
            scrollbar_button_color=colors["accent"],
            scrollbar_button_hover_color=colors["accent_hover"],
        )
        self.result_box.grid(row=1, column=0, padx=16, pady=(0, 12), sticky="nsew")

        ctk.CTkLabel(
            frame,
            text="单人完整报告",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=colors["text"],
        ).grid(row=2, column=0, padx=16, pady=(0, 8), sticky="w")

        self.html_renderer = HtmlRenderer(frame, theme=self.theme)
        self.html_renderer.grid(row=3, column=0, padx=16, pady=(0, 16), sticky="nsew")

        self.result_box.insert("1.0", "等待批量匹配结果...")

    def _on_pick_job_click(self):
        if self.on_pick_job_history:
            self.on_pick_job_history()

    def _on_run_batch_click(self):
        job_label = self.job_combo.get().strip()
        payload = self.job_data_map.get(job_label)
        if not payload:
            messagebox.showwarning("提示", "请先选择目标岗位")
            return
        if not self.candidate_data_map:
            messagebox.showwarning("提示", "当前没有候选人可供批量匹配")
            return

        self.set_running(True)
        self.info_label.configure(text="正在执行批量匹配，请稍候...")
        self.on_run_batch(job_label, payload)

    def update_job_options(
        self, job_options: List[str], job_data_map: Dict[str, Dict[str, object]]
    ):
        self.job_options = job_options or ["请先分析岗位"]
        self.job_data_map = job_data_map or {}
        self.job_combo.configure(values=self.job_options)
        if self.job_options:
            self.job_combo.set(self.job_options[0])

    def update_candidates(self, candidates: List[Dict[str, str]]):
        self.candidate_data_map = {
            item.get("candidate_id") or item.get("profile_url") or str(index): item
            for index, item in enumerate(candidates)
        }
        self.candidate_options = list(self.candidate_data_map.keys())
        self.candidate_box.delete("1.0", "end")
        if not candidates:
            self.candidate_box.insert(
                "1.0", "当前没有候选人，请先去候选人库将当前结果页候选人入库。"
            )
            return

        rows = []
        for index, item in enumerate(candidates, start=1):
            rows.append(
                "{}. {} | {} | {}\n来源关键词: {}\n".format(
                    index,
                    item.get("name", "未命名候选人"),
                    item.get("current_title", ""),
                    item.get("current_company", ""),
                    item.get("keyword", ""),
                )
            )
        self.candidate_box.insert("1.0", "\n".join(rows).strip())

    def set_running(self, running: bool):
        state = "disabled" if running else "normal"
        self.job_combo.configure(state=state)
        self.pick_job_btn.configure(state=state)
        self.run_batch_btn.configure(
            state=state,
            text="批量匹配中..." if running else "开始批量匹配",
        )

    def set_results(self, results: List[Dict[str, str]], info_text: str):
        self.result_data_map = {
            item.get("result_id") or str(index): item
            for index, item in enumerate(results)
        }
        self.info_label.configure(text=info_text)
        self.result_box.delete("1.0", "end")
        if not results:
            self.result_box.insert("1.0", "本次批量匹配没有产生结果。")
            self.html_renderer.clear()
            return

        rows = []
        for index, item in enumerate(results, start=1):
            rows.append(
                "{}. {} | 分数: {} | 动作: {}\n摘要: {}\n风险: {}\n".format(
                    index,
                    item.get("candidate_name", "未命名候选人"),
                    item.get("score", "待解析"),
                    item.get("recommendation", "待解析"),
                    item.get("summary", ""),
                    item.get("risks", ""),
                )
            )
        self.result_box.insert("1.0", "\n".join(rows).strip())
        self.html_renderer.set_content(results[0].get("full_report_html", ""))
