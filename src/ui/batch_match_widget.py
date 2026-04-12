"""Batch match task console."""

import customtkinter as ctk
from tkinter import messagebox
from typing import Callable, Dict, List, Optional


class BatchMatchWidget(ctk.CTkFrame):
    """Batch match workspace focused on Excel task execution."""

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
        on_run_batch: Callable,
        on_cancel_batch: Optional[Callable] = None,
        on_load_recent_batch: Optional[Callable] = None,
        on_open_excel: Optional[Callable] = None,
        on_open_excel_dir: Optional[Callable] = None,
        on_pick_job_history: Optional[Callable] = None,
        theme: str = "light",
        **kwargs,
    ):
        super().__init__(master, **kwargs)
        self.on_run_batch = on_run_batch
        self.on_cancel_batch = on_cancel_batch
        self.on_load_recent_batch = on_load_recent_batch
        self.on_open_excel = on_open_excel
        self.on_open_excel_dir = on_open_excel_dir
        self.on_pick_job_history = on_pick_job_history
        self.theme = theme
        self.job_options: List[str] = ["请先分析岗位"]
        self.job_data_map: Dict[str, Dict[str, object]] = {}
        self._excel_file_path: str = ""

        self._setup_ui()

    def _setup_ui(self):
        self.configure(fg_color="transparent")
        self.grid_columnconfigure(0, weight=2)
        self.grid_columnconfigure(1, weight=3)
        self.grid_rowconfigure(0, weight=1)

        self._build_control_panel()
        self._build_status_panel()

    def _build_control_panel(self):
        colors = self.PALETTE
        frame = ctk.CTkFrame(
            self,
            corner_radius=24,
            fg_color=colors["panel"],
            border_width=1,
            border_color=colors["border"],
        )
        frame.grid(row=0, column=0, padx=(10, 5), pady=10, sticky="nsew")
        frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            frame,
            text="批量匹配",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=colors["text"],
        ).grid(row=0, column=0, padx=16, pady=(16, 4), sticky="w")
        ctk.CTkLabel(
            frame,
            text="选择岗位并导入 Excel 后，程序会批量处理可匹配候选人并将结果回写到原文件。",
            font=ctk.CTkFont(size=12),
            text_color=colors["muted"],
            justify="left",
            wraplength=280,
        ).grid(row=1, column=0, padx=16, pady=(0, 12), sticky="w")

        ctk.CTkLabel(frame, text="目标岗位", text_color=colors["text"]).grid(
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

        status_card = ctk.CTkFrame(
            frame,
            corner_radius=14,
            fg_color=colors["panel_alt"],
            border_width=1,
            border_color=colors["border"],
        )
        status_card.grid(row=4, column=0, padx=16, pady=(0, 10), sticky="ew")

        status_header = ctk.CTkFrame(status_card, fg_color="transparent")
        status_header.pack(fill="x", padx=12, pady=(10, 2))
        ctk.CTkLabel(
            status_header,
            text="Excel 状态",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=colors["text"],
        ).pack(side="left")
        self.candidate_count_label = ctk.CTkLabel(
            status_header,
            text="当前未导入 Excel",
            text_color=colors["muted"],
            font=ctk.CTkFont(size=12),
        )
        self.candidate_count_label.pack(side="right")

        self.candidate_preview_label = ctk.CTkLabel(
            status_card,
            text="导入后将自动统计可匹配候选人数量。",
            text_color=colors["muted"],
            anchor="w",
            justify="left",
            wraplength=260,
            font=ctk.CTkFont(size=11),
        )
        self.candidate_preview_label.pack(fill="x", padx=12, pady=(0, 10))

        concurrency_card = ctk.CTkFrame(
            frame,
            corner_radius=14,
            fg_color=colors["panel_alt"],
            border_width=1,
            border_color=colors["border"],
        )
        concurrency_card.grid(row=5, column=0, padx=16, pady=(0, 10), sticky="ew")

        slider_row = ctk.CTkFrame(concurrency_card, fg_color="transparent")
        slider_row.pack(fill="x", padx=12, pady=10)
        slider_row.grid_columnconfigure(2, weight=1)

        ctk.CTkLabel(
            slider_row,
            text="并发数",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=colors["text"],
        ).grid(row=0, column=0, padx=(0, 8))
        self.concurrency_label = ctk.CTkLabel(
            slider_row,
            text="5",
            width=24,
            text_color=colors["text"],
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        self.concurrency_label.grid(row=0, column=1, padx=(0, 8))
        self.concurrency_slider = ctk.CTkSlider(
            slider_row,
            from_=1,
            to=10,
            number_of_steps=9,
            width=200,
            height=16,
            corner_radius=8,
            button_color=colors["accent"],
            button_hover_color=colors["accent_hover"],
        )
        self.concurrency_slider.set(5)
        self.concurrency_slider.grid(row=0, column=2, sticky="ew")
        self.concurrency_slider.bind(
            "<ButtonRelease-1>", self._on_concurrency_change
        )
        self.concurrency_slider.bind(
            "<B1-Motion>", self._on_concurrency_change
        )

        self.import_excel_btn = ctk.CTkButton(
            frame,
            text="导入 Excel",
            height=38,
            corner_radius=18,
            fg_color=colors["secondary"],
            hover_color=colors["secondary_hover"],
            text_color=colors["text"],
            command=self._on_load_recent_batch_click,
        )
        self.import_excel_btn.grid(row=6, column=0, padx=16, pady=(0, 10), sticky="ew")

        self.run_batch_btn = ctk.CTkButton(
            frame,
            text="开始批量匹配",
            height=42,
            corner_radius=20,
            fg_color=colors["accent"],
            hover_color=colors["accent_hover"],
            text_color="#f8fbff",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._on_run_batch_click,
        )
        self.run_batch_btn.grid(row=7, column=0, padx=16, pady=(0, 10), sticky="ew")

        self.cancel_batch_btn = ctk.CTkButton(
            frame,
            text="取消当前批量匹配",
            height=38,
            corner_radius=18,
            fg_color=colors["secondary"],
            hover_color=colors["secondary_hover"],
            text_color=colors["text"],
            command=self._on_cancel_batch_click,
            state="disabled",
        )
        self.cancel_batch_btn.grid(row=8, column=0, padx=16, pady=(0, 16), sticky="ew")

    def _build_status_panel(self):
        colors = self.PALETTE
        frame = ctk.CTkFrame(
            self,
            corner_radius=24,
            fg_color=colors["panel"],
            border_width=1,
            border_color=colors["border"],
        )
        frame.grid(row=0, column=1, padx=(5, 10), pady=10, sticky="nsew")
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(4, weight=1)

        ctk.CTkLabel(
            frame,
            text="任务结果",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=colors["text"],
        ).grid(row=0, column=0, padx=16, pady=(16, 4), sticky="w")
        ctk.CTkLabel(
            frame,
            text="这里显示当前文件路径、执行进度和回写结果摘要。",
            font=ctk.CTkFont(size=12),
            text_color=colors["muted"],
            justify="left",
            wraplength=420,
        ).grid(row=1, column=0, padx=16, pady=(0, 12), sticky="w")

        action_row = ctk.CTkFrame(frame, fg_color="transparent")
        action_row.grid(row=2, column=0, padx=16, pady=(0, 10), sticky="ew")
        action_row.grid_columnconfigure((0, 1), weight=1)

        self.open_excel_btn = ctk.CTkButton(
            action_row,
            text="打开当前 Excel",
            height=36,
            corner_radius=16,
            fg_color=colors["secondary"],
            hover_color=colors["secondary_hover"],
            text_color=colors["text"],
            command=self._on_open_excel_click,
        )
        self.open_excel_btn.grid(row=0, column=0, padx=(0, 6), sticky="ew")

        self.open_excel_dir_btn = ctk.CTkButton(
            action_row,
            text="打开 Excel 文件目录",
            height=36,
            corner_radius=16,
            fg_color=colors["secondary"],
            hover_color=colors["secondary_hover"],
            text_color=colors["text"],
            command=self._on_open_excel_dir_click,
        )
        self.open_excel_dir_btn.grid(row=0, column=1, padx=(6, 0), sticky="ew")

        self.excel_path_box = ctk.CTkTextbox(
            frame,
            height=90,
            wrap="word",
            corner_radius=18,
            border_width=1,
            border_color=colors["border"],
            fg_color=colors["panel_alt"],
            text_color=colors["text"],
            scrollbar_button_color=colors["accent"],
            scrollbar_button_hover_color=colors["accent_hover"],
        )
        self.excel_path_box.grid(row=3, column=0, padx=16, pady=(0, 10), sticky="ew")
        self.excel_path_box.insert("1.0", "当前未导入 Excel 文件。")

        self.summary_box = ctk.CTkTextbox(
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
        self.summary_box.grid(row=4, column=0, padx=16, pady=(0, 10), sticky="nsew")
        self.summary_box.insert(
            "1.0",
            "等待导入 Excel。\n开始批量匹配后，这里会显示处理进度和结果摘要。",
        )

        self.info_label = ctk.CTkLabel(
            frame,
            text="等待选择岗位并导入 Excel。",
            text_color=colors["muted"],
            font=ctk.CTkFont(size=12),
            justify="left",
            wraplength=420,
        )
        self.info_label.grid(row=5, column=0, padx=16, pady=(0, 16), sticky="w")

    def _on_pick_job_click(self):
        if self.on_pick_job_history:
            self.on_pick_job_history()

    def _on_run_batch_click(self):
        job_label = self.job_combo.get().strip()
        payload = self.job_data_map.get(job_label)
        if not payload:
            messagebox.showwarning("提示", "请先选择目标岗位")
            return
        if not self._excel_file_path:
            messagebox.showwarning("提示", "请先导入候选人 Excel")
            return
        self.set_running(True)
        self._set_summary_text("正在执行批量匹配，请稍候...")
        self.on_run_batch(job_label, payload)

    def _on_cancel_batch_click(self):
        if self.on_cancel_batch:
            self.on_cancel_batch()

    def _on_load_recent_batch_click(self):
        if self.on_load_recent_batch:
            self.on_load_recent_batch()

    def _on_open_excel_click(self):
        if self.on_open_excel:
            self.on_open_excel()

    def _on_open_excel_dir_click(self):
        if self.on_open_excel_dir:
            self.on_open_excel_dir()

    def _on_concurrency_change(self, _event=None):
        val = int(round(self.concurrency_slider.get()))
        self.concurrency_label.configure(text=str(val))

    def get_concurrency(self) -> int:
        return int(round(self.concurrency_slider.get()))

    def update_job_options(
        self, job_options: List[str], job_data_map: Dict[str, Dict[str, object]]
    ):
        self.job_options = job_options or ["请先分析岗位"]
        self.job_data_map = job_data_map or {}
        self.job_combo.configure(values=self.job_options)
        if self.job_options:
            self.job_combo.set(self.job_options[0])

    def set_running(self, running: bool):
        state = "disabled" if running else "normal"
        self.job_combo.configure(state=state)
        self.pick_job_btn.configure(state=state)
        self.import_excel_btn.configure(state=state)
        self.open_excel_btn.configure(state=state)
        self.open_excel_dir_btn.configure(state=state)
        self.concurrency_slider.configure(state=state)
        self.run_batch_btn.configure(
            state=state,
            text="批量匹配中..." if running else "开始批量匹配",
        )
        self.cancel_batch_btn.configure(state="normal" if running else "disabled")

    def set_results(self, info_text: str):
        self._set_summary_text(info_text)

    def set_match_results(self, results: List[dict]):
        """Display batch match results with tier classification."""
        TIER_LABELS = {
            "S": "🟢 S（强推）",
            "A": "🔵 A（深聊）",
            "B": "🟡 B（观望）",
            "C": "🔴 C（放弃）",
        }
        lines = ["批量匹配完成，结果摘要：\n"]
        for r in results:
            name = r.get("candidate_name", "未命名候选人")
            tier = r.get("tier")
            core_met = r.get("core_met_count", 0)
            core_total = r.get("core_total", 0)
            recommendation = r.get("recommendation", "")
            risks = r.get("risks", "")
            summary = r.get("summary", "")
            dealbreaker = r.get("dealbreaker_hit", False)

            tier_text = TIER_LABELS.get(tier, tier) if tier else "待解析"
            lines.append(f"{name} — {tier_text}")
            if dealbreaker:
                lines.append("  ⚠️ 命中一票否决项")
            if core_total > 0:
                lines.append(f"  ├─ 核心要求符合：{core_met}/{core_total}")
            if recommendation:
                lines.append(f"  ├─ 建议：{recommendation}")
            if risks:
                lines.append(f"  ├─ 关键风险：{risks}")
            if summary:
                lines.append(f"  └─ 结论：{summary}")
            lines.append("")

        self._set_summary_text("\n".join(lines))

    def set_progress(self, current: int, total: int, candidate_name: str):
        text = "批量匹配进行中：{}/{}，当前处理 {}。".format(
            current,
            total,
            candidate_name or "未命名候选人",
        )
        self._set_summary_text(text)

    def set_excel_file(self, file_path: str, matchable_count: int = 0):
        self._excel_file_path = file_path or ""
        self.excel_path_box.delete("1.0", "end")
        self.excel_path_box.insert("1.0", file_path or "当前未导入 Excel 文件。")
        if file_path:
            self.candidate_count_label.configure(
                text="可匹配候选人 {} 位".format(matchable_count)
            )
            self.candidate_preview_label.configure(
                text="结果将直接回写到该 Excel 文件。"
            )
        else:
            self.candidate_count_label.configure(text="当前未导入 Excel")
            self.candidate_preview_label.configure(
                text="导入后将自动统计可匹配候选人数量。"
            )

    def get_excel_file(self) -> str:
        return self._excel_file_path

    def _set_summary_text(self, text: str):
        self.summary_box.delete("1.0", "end")
        self.summary_box.insert("1.0", text)
        self.info_label.configure(text=text.splitlines()[0] if text else "")
