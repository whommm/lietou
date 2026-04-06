"""Candidate library UI for Liepin automation."""

import customtkinter as ctk
from tkinter import messagebox
from typing import Callable, Dict, List, Optional


class CandidateLibraryWidget(ctk.CTkFrame):
    """Candidate library workspace."""

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
        on_launch_browser: Callable,
        on_check_login: Callable,
        on_run_task: Callable,
        on_export_debug: Optional[Callable] = None,
        on_pick_job_history: Optional[Callable] = None,
        theme: str = "light",
        **kwargs,
    ):
        super().__init__(master, **kwargs)
        self.on_launch_browser = on_launch_browser
        self.on_check_login = on_check_login
        self.on_run_task = on_run_task
        self.on_export_debug = on_export_debug
        self.on_pick_job_history = on_pick_job_history
        self.theme = theme

        self.job_options: List[str] = ["请先分析岗位"]
        self.job_data_map: Dict[str, Dict[str, object]] = {}
        self.strategy_payload: Dict[str, List[str]] = {}
        self.task_id: str = ""
        self._candidate_records: List[Dict[str, str]] = []

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
        frame.grid_rowconfigure(8, weight=1)

        ctk.CTkLabel(
            frame,
            text="候选人库与猎聘采集",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=colors["text"],
        ).grid(row=0, column=0, padx=16, pady=(16, 5), sticky="w")
        ctk.CTkLabel(
            frame,
            text="先同步岗位搜索词，手动在猎聘搜索出结果页，再一键将当前结果页候选人入库。",
            font=ctk.CTkFont(size=12),
            text_color=colors["muted"],
        ).grid(row=1, column=0, padx=16, pady=(0, 12), sticky="w")

        ctk.CTkLabel(frame, text="目标岗位:", text_color=colors["text"]).grid(
            row=2, column=0, padx=16, pady=(8, 6), sticky="w"
        )
        picker_row = ctk.CTkFrame(frame, fg_color="transparent")
        picker_row.grid(row=3, column=0, padx=16, pady=(0, 10), sticky="ew")
        picker_row.grid_columnconfigure(0, weight=1)

        self.job_combo = ctk.CTkComboBox(
            picker_row,
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
            command=self._on_job_selected,
        )
        self.job_combo.grid(row=0, column=0, sticky="ew")

        self.pick_job_btn = ctk.CTkButton(
            picker_row,
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

        ctk.CTkLabel(frame, text="搜索词预览:", text_color=colors["text"]).grid(
            row=4, column=0, padx=16, pady=(6, 6), sticky="w"
        )
        self.strategy_box = ctk.CTkTextbox(
            frame,
            height=140,
            wrap="word",
            corner_radius=18,
            border_width=1,
            border_color=colors["border"],
            fg_color=colors["panel_alt"],
            text_color=colors["text"],
            scrollbar_button_color=colors["accent"],
            scrollbar_button_hover_color=colors["accent_hover"],
        )
        self.strategy_box.grid(row=5, column=0, padx=16, pady=(0, 10), sticky="ew")

        limit_frame = ctk.CTkFrame(frame, fg_color="transparent")
        limit_frame.grid(row=6, column=0, padx=16, pady=(0, 10), sticky="ew")
        ctk.CTkLabel(limit_frame, text="采集人数上限:", text_color=colors["text"]).pack(
            side="left"
        )
        self.max_candidates_entry = ctk.CTkEntry(
            limit_frame,
            width=90,
            corner_radius=14,
            fg_color=colors["panel_alt"],
            border_color=colors["border"],
            text_color=colors["text"],
        )
        self.max_candidates_entry.pack(side="left", padx=(10, 18))
        self.max_candidates_entry.insert(0, "20")

        ctk.CTkLabel(limit_frame, text="最大页数:", text_color=colors["text"]).pack(
            side="left"
        )
        self.max_pages_entry = ctk.CTkEntry(
            limit_frame,
            width=90,
            corner_radius=14,
            fg_color=colors["panel_alt"],
            border_color=colors["border"],
            text_color=colors["text"],
        )
        self.max_pages_entry.pack(side="left", padx=(10, 0))
        self.max_pages_entry.insert(0, "1")

        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.grid(row=7, column=0, padx=16, pady=(0, 16), sticky="ew")
        btn_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.launch_browser_btn = ctk.CTkButton(
            btn_frame,
            text="启动猎聘浏览器",
            height=38,
            corner_radius=18,
            fg_color=colors["secondary"],
            hover_color=colors["secondary_hover"],
            text_color=colors["text"],
            command=self.on_launch_browser,
        )
        self.launch_browser_btn.grid(row=0, column=0, padx=(0, 8), sticky="ew")

        self.check_login_btn = ctk.CTkButton(
            btn_frame,
            text="检查登录状态",
            height=38,
            corner_radius=18,
            fg_color=colors["secondary"],
            hover_color=colors["secondary_hover"],
            text_color=colors["text"],
            command=self.on_check_login,
        )
        self.check_login_btn.grid(row=0, column=1, padx=4, sticky="ew")

        self.run_task_btn = ctk.CTkButton(
            btn_frame,
            text="入库当前结果页",
            height=40,
            corner_radius=20,
            fg_color=colors["accent"],
            hover_color=colors["accent_hover"],
            text_color="#f8fbff",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._on_run_task_click,
        )
        self.run_task_btn.grid(row=0, column=2, padx=(8, 0), sticky="ew")

        self.debug_btn = ctk.CTkButton(
            btn_frame,
            text="导出页面诊断",
            height=38,
            corner_radius=18,
            fg_color=colors["secondary"],
            hover_color=colors["secondary_hover"],
            text_color=colors["text"],
            command=self._on_export_debug_click,
        )
        self.debug_btn.grid(row=0, column=3, padx=(8, 0), sticky="ew")

        self.info_label = ctk.CTkLabel(
            frame,
            text="未创建搜索任务",
            text_color=colors["muted"],
            font=ctk.CTkFont(size=12),
            justify="left",
            wraplength=360,
        )
        self.info_label.grid(row=8, column=0, padx=16, pady=(0, 16), sticky="nw")

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
            text="候选人列表",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=colors["text"],
        ).grid(row=0, column=0, padx=16, pady=(16, 8), sticky="w")

        self.candidate_list = ctk.CTkTextbox(
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
        self.candidate_list.grid(row=1, column=0, padx=16, pady=(0, 12), sticky="nsew")

        ctk.CTkLabel(
            frame,
            text="候选人详情预览",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=colors["text"],
        ).grid(row=2, column=0, padx=16, pady=(0, 8), sticky="w")

        self.detail_box = ctk.CTkTextbox(
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
        self.detail_box.grid(row=3, column=0, padx=16, pady=(0, 16), sticky="nsew")

        self._set_candidates([])
        self._set_detail_text("等待候选人采集结果...")

    def _on_pick_job_click(self):
        if self.on_pick_job_history:
            self.on_pick_job_history()

    def _on_job_selected(self, value: str):
        payload = self.job_data_map.get(value)
        if not payload:
            self._set_strategy_text("请先从岗位分析同步搜索策略。")
            return
        self.strategy_payload = payload.get("strategy", {})
        self.task_id = ""
        self._set_strategy_text(self._format_strategy_text(self.strategy_payload))
        self.info_label.configure(
            text="已选择岗位：{}\n等待创建或执行搜索任务。".format(value)
        )

    def _on_run_task_click(self):
        job_label = self.job_combo.get().strip()
        payload = self.job_data_map.get(job_label)
        if not payload:
            messagebox.showwarning("提示", "请先选择一个已生成搜索策略的岗位")
            return

        try:
            max_candidates = int(self.max_candidates_entry.get().strip() or "20")
            max_pages = int(self.max_pages_entry.get().strip() or "1")
        except ValueError:
            messagebox.showwarning("提示", "采集人数上限和页数必须是整数")
            return

        if max_candidates <= 0 or max_pages <= 0:
            messagebox.showwarning("提示", "采集人数上限和页数必须大于 0")
            return

        self.set_running(True)
        self.info_label.configure(text="正在读取当前结果页并入库，请稍候...")
        self.on_run_task(job_label, payload, max_candidates, max_pages)

    def _on_export_debug_click(self):
        if self.on_export_debug:
            self.on_export_debug()

    def update_job_options(
        self, job_options: List[str], job_data_map: Dict[str, Dict[str, object]]
    ):
        self.job_options = job_options or ["请先分析岗位"]
        self.job_data_map = job_data_map or {}
        self.job_combo.configure(values=self.job_options)
        if self.job_options:
            self.job_combo.set(self.job_options[0])
            self._on_job_selected(self.job_options[0])

    def set_selected_job(self, job_label: str):
        self.job_combo.set(job_label)
        self._on_job_selected(job_label)

    def set_running(self, running: bool):
        state = "disabled" if running else "normal"
        self.launch_browser_btn.configure(state=state)
        self.check_login_btn.configure(state=state)
        self.run_task_btn.configure(
            state=state,
            text="入库中..." if running else "入库当前结果页",
        )
        self.debug_btn.configure(state=state)
        self.pick_job_btn.configure(state=state)
        self.job_combo.configure(state=state)
        self.max_candidates_entry.configure(state=state)
        self.max_pages_entry.configure(state=state)

    def set_browser_state(self, text: str):
        current = self.info_label.cget("text")
        self.info_label.configure(
            text="{}\n{}".format(text, current.split("\n", 1)[-1])
        )

    def set_task_result(
        self,
        task_id: str,
        candidates: List[Dict[str, str]],
        summary_text: str,
    ):
        self.task_id = task_id
        self._candidate_records = candidates
        self.info_label.configure(text=summary_text)
        self._set_candidates(candidates)
        if candidates:
            self._set_detail_text(candidates[0].get("resume_text", ""))
        else:
            self._set_detail_text("本次任务未采集到候选人。")

    def get_candidate_records(self) -> List[Dict[str, str]]:
        """Return the current candidate records shown in the library."""
        return list(self._candidate_records)

    def _set_strategy_text(self, text: str):
        self.strategy_box.delete("1.0", "end")
        self.strategy_box.insert("1.0", text)

    def _set_candidates(self, candidates: List[Dict[str, str]]):
        self.candidate_list.delete("1.0", "end")
        if not candidates:
            self.candidate_list.insert("1.0", "等待从当前结果页入库候选人...")
            return

        rows = []
        for index, candidate in enumerate(candidates, start=1):
            rows.append(
                "{}. {} | {} | {}\n来源关键词: {}\n链接: {}\n".format(
                    index,
                    candidate.get("name", "未命名候选人"),
                    candidate.get("current_title", ""),
                    candidate.get("current_company", ""),
                    candidate.get("keyword", ""),
                    candidate.get("profile_url", ""),
                )
            )
        self.candidate_list.insert("1.0", "\n".join(rows).strip())

    def _set_detail_text(self, text: str):
        self.detail_box.delete("1.0", "end")
        self.detail_box.insert("1.0", text or "等待候选人详情预览...")

    def _format_strategy_text(self, strategy: Dict[str, List[str]]) -> str:
        if not strategy:
            return "请先从岗位分析同步搜索策略。"
        lines = []
        mappings = [
            ("精准词", strategy.get("precise_keywords", [])),
            ("扩池词", strategy.get("expansion_keywords", [])),
            ("同义词", strategy.get("synonyms", [])),
            ("排除词", strategy.get("exclude_keywords", [])),
            ("布尔预留", strategy.get("boolean_queries", [])),
        ]
        for label, values in mappings:
            if values:
                lines.append("【{}】{}".format(label, "、".join(values)))
        return "\n\n".join(lines) if lines else "未生成可用搜索词。"
