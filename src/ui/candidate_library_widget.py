"""Candidate capture task console."""

import customtkinter as ctk
from tkinter import messagebox
from typing import Callable, Dict, List, Optional


class CandidateLibraryWidget(ctk.CTkFrame):
    """Candidate capture workspace focused on task control."""

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
        on_import_excel: Optional[Callable] = None,
        on_open_excel: Optional[Callable] = None,
        on_open_excel_dir: Optional[Callable] = None,
        on_export_debug: Optional[Callable] = None,
        on_pick_job_history: Optional[Callable] = None,
        theme: str = "light",
        **kwargs,
    ):
        super().__init__(master, **kwargs)
        self.on_launch_browser = on_launch_browser
        self.on_check_login = on_check_login
        self.on_run_task = on_run_task
        self.on_import_excel = on_import_excel
        self.on_open_excel = on_open_excel
        self.on_open_excel_dir = on_open_excel_dir
        self.on_export_debug = on_export_debug
        self.on_pick_job_history = on_pick_job_history
        self.theme = theme

        self.job_options: List[str] = ["请先分析岗位"]
        self.job_data_map: Dict[str, Dict[str, object]] = {}
        self.strategy_payload: Dict[str, List[str]] = {}
        self.task_id: str = ""
        self._excel_file_path: str = ""

        self._setup_ui()

    def _setup_ui(self):
        self.configure(fg_color="transparent")
        self.grid_columnconfigure(0, weight=4)
        self.grid_columnconfigure(1, weight=5)
        self.grid_rowconfigure(1, weight=1)

        self._build_top_action_bar()
        self._build_control_panel()
        self._build_status_panel()

    def _build_top_action_bar(self):
        colors = self.PALETTE[self.theme]
        frame = ctk.CTkFrame(
            self,
            corner_radius=22,
            fg_color=colors["panel"],
            border_width=1,
            border_color=colors["border"],
        )
        frame.grid(row=0, column=0, columnspan=2, padx=10, pady=(10, 6), sticky="ew")
        frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.launch_browser_btn = ctk.CTkButton(
            frame,
            text="启动猎聘浏览器",
            height=40,
            corner_radius=18,
            fg_color=colors["secondary"],
            hover_color=colors["secondary_hover"],
            text_color=colors["text"],
            command=self.on_launch_browser,
        )
        self.launch_browser_btn.grid(
            row=0, column=0, padx=(14, 6), pady=14, sticky="ew"
        )

        self.check_login_btn = ctk.CTkButton(
            frame,
            text="检查登录状态",
            height=40,
            corner_radius=18,
            fg_color=colors["secondary"],
            hover_color=colors["secondary_hover"],
            text_color=colors["text"],
            command=self.on_check_login,
        )
        self.check_login_btn.grid(row=0, column=1, padx=6, pady=14, sticky="ew")

        self.run_task_btn = ctk.CTkButton(
            frame,
            text="开始抓取并写入 Excel",
            height=42,
            corner_radius=20,
            fg_color=colors["accent"],
            hover_color=colors["accent_hover"],
            text_color="#f8fbff",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._on_run_task_click,
        )
        self.run_task_btn.grid(row=0, column=2, padx=6, pady=14, sticky="ew")

        self.debug_btn = ctk.CTkButton(
            frame,
            text="导出页面诊断",
            height=40,
            corner_radius=18,
            fg_color=colors["secondary"],
            hover_color=colors["secondary_hover"],
            text_color=colors["text"],
            command=self._on_export_debug_click,
        )
        self.debug_btn.grid(row=0, column=3, padx=(6, 14), pady=14, sticky="ew")

    def _build_control_panel(self):
        colors = self.PALETTE[self.theme]
        frame = ctk.CTkScrollableFrame(
            self,
            corner_radius=24,
            fg_color=colors["panel"],
            border_width=1,
            border_color=colors["border"],
        )
        frame.grid(row=1, column=0, padx=(10, 6), pady=(0, 10), sticky="nsew")
        frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            frame,
            text="候选人抓取",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=colors["text"],
        ).grid(row=0, column=0, padx=16, pady=(16, 4), sticky="w")
        ctk.CTkLabel(
            frame,
            text="选择岗位后，从猎聘当前结果页抓取候选人并实时写入 Excel。",
            font=ctk.CTkFont(size=12),
            text_color=colors["muted"],
            justify="left",
            wraplength=280,
        ).grid(row=1, column=0, padx=16, pady=(0, 12), sticky="w")

        ctk.CTkLabel(frame, text="目标岗位", text_color=colors["text"]).grid(
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

        ctk.CTkLabel(frame, text="搜索词预览", text_color=colors["text"]).grid(
            row=4, column=0, padx=16, pady=(6, 6), sticky="w"
        )
        self.strategy_box = ctk.CTkTextbox(
            frame,
            height=160,
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

        self.save_strategy_btn = ctk.CTkButton(
            frame,
            text="保存搜索词修改",
            height=34,
            corner_radius=16,
            fg_color=colors["secondary"],
            hover_color=colors["secondary_hover"],
            text_color=colors["text"],
            command=self._save_strategy_changes,
        )
        self.save_strategy_btn.grid(row=6, column=0, padx=16, pady=(0, 10), sticky="e")

        limit_frame = ctk.CTkFrame(frame, fg_color="transparent")
        limit_frame.grid(row=7, column=0, padx=16, pady=(0, 12), sticky="ew")
        limit_frame.grid_columnconfigure((0, 1), weight=1)

        limit_card_left = ctk.CTkFrame(
            limit_frame,
            corner_radius=16,
            fg_color=colors["panel_alt"],
            border_width=1,
            border_color=colors["border"],
        )
        limit_card_left.grid(row=0, column=0, padx=(0, 6), sticky="ew")
        ctk.CTkLabel(
            limit_card_left,
            text="抓取人数上限",
            text_color=colors["muted"],
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=12, pady=(10, 2))
        self.max_candidates_entry = ctk.CTkEntry(
            limit_card_left,
            corner_radius=12,
            fg_color=colors["panel"],
            border_color=colors["border"],
            text_color=colors["text"],
        )
        self.max_candidates_entry.pack(fill="x", padx=12, pady=(0, 10))
        self.max_candidates_entry.insert(0, "20")

        limit_card_right = ctk.CTkFrame(
            limit_frame,
            corner_radius=16,
            fg_color=colors["panel_alt"],
            border_width=1,
            border_color=colors["border"],
        )
        limit_card_right.grid(row=0, column=1, padx=(6, 0), sticky="ew")
        ctk.CTkLabel(
            limit_card_right,
            text="抓取页数上限",
            text_color=colors["muted"],
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=12, pady=(10, 2))
        self.max_pages_entry = ctk.CTkEntry(
            limit_card_right,
            corner_radius=12,
            fg_color=colors["panel"],
            border_color=colors["border"],
            text_color=colors["text"],
        )
        self.max_pages_entry.pack(fill="x", padx=12, pady=(0, 10))
        self.max_pages_entry.insert(0, "1")

    def _build_status_panel(self):
        colors = self.PALETTE[self.theme]
        frame = ctk.CTkFrame(
            self,
            corner_radius=24,
            fg_color=colors["panel"],
            border_width=1,
            border_color=colors["border"],
        )
        frame.grid(row=1, column=1, padx=(6, 10), pady=(0, 10), sticky="nsew")
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(4, weight=1)

        ctk.CTkLabel(
            frame,
            text="任务状态",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=colors["text"],
        ).grid(row=0, column=0, padx=16, pady=(16, 4), sticky="w")
        ctk.CTkLabel(
            frame,
            text="这里显示当前 Excel 文件、任务摘要和下一步操作入口。",
            font=ctk.CTkFont(size=12),
            text_color=colors["muted"],
            justify="left",
            wraplength=420,
        ).grid(row=1, column=0, padx=16, pady=(0, 12), sticky="w")

        action_row = ctk.CTkFrame(frame, fg_color="transparent")
        action_row.grid(row=2, column=0, padx=16, pady=(0, 10), sticky="ew")
        action_row.grid_columnconfigure((0, 1, 2), weight=1)

        self.import_excel_btn = ctk.CTkButton(
            action_row,
            text="导入 Excel",
            height=36,
            corner_radius=16,
            fg_color=colors["secondary"],
            hover_color=colors["secondary_hover"],
            text_color=colors["text"],
            command=self._on_import_excel_click,
        )
        self.import_excel_btn.grid(row=0, column=0, padx=(0, 6), sticky="ew")

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
        self.open_excel_btn.grid(row=0, column=1, padx=6, sticky="ew")

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
        self.open_excel_dir_btn.grid(row=0, column=2, padx=(6, 0), sticky="ew")

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
        self.excel_path_box.insert("1.0", "当前还没有候选人 Excel 文件。")

        self.info_box = ctk.CTkTextbox(
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
        self.info_box.grid(row=4, column=0, padx=16, pady=(0, 10), sticky="nsew")
        self.info_box.insert(
            "1.0",
            "未创建搜索任务。\n抓取完成后，这里会显示处理页数、成功数、失败数和文件位置。",
        )

        self.info_label = ctk.CTkLabel(
            frame,
            text="等待开始抓取。",
            text_color=colors["muted"],
            font=ctk.CTkFont(size=12),
            justify="left",
            wraplength=420,
        )
        self.info_label.grid(row=5, column=0, padx=16, pady=(0, 16), sticky="w")

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
        self._set_info_text("已选择岗位：{}\n等待开始抓取。".format(value))

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
            messagebox.showwarning("提示", "抓取人数上限和页数必须是整数")
            return
        if max_candidates <= 0 or max_pages <= 0:
            messagebox.showwarning("提示", "抓取人数上限和页数必须大于 0")
            return
        self.set_running(True)
        self._set_info_text("正在抓取猎聘当前结果页并写入 Excel，请稍候...")
        self.on_run_task(job_label, payload, max_candidates, max_pages)

    def _on_export_debug_click(self):
        if self.on_export_debug:
            self.on_export_debug()

    def _on_import_excel_click(self):
        if self.on_import_excel:
            self.on_import_excel()

    def _on_open_excel_click(self):
        if self.on_open_excel:
            self.on_open_excel()

    def _on_open_excel_dir_click(self):
        if self.on_open_excel_dir:
            self.on_open_excel_dir()

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
            text="抓取中..." if running else "开始抓取并写入 Excel",
        )
        self.import_excel_btn.configure(state=state)
        self.open_excel_btn.configure(state=state)
        self.open_excel_dir_btn.configure(state=state)
        self.debug_btn.configure(state=state)
        self.pick_job_btn.configure(state=state)
        self.job_combo.configure(state=state)
        self.max_candidates_entry.configure(state=state)
        self.max_pages_entry.configure(state=state)

    def set_browser_state(self, text: str):
        self.info_label.configure(text=text)

    def set_task_result(self, task_id: str, summary_text: str):
        self.task_id = task_id
        self._set_info_text(summary_text)

    def set_excel_file(self, file_path: str):
        self._excel_file_path = file_path or ""
        self.excel_path_box.delete("1.0", "end")
        self.excel_path_box.insert("1.0", file_path or "当前还没有候选人 Excel 文件。")

    def set_library_candidates(self, summary_text: str, task_id: str = ""):
        self.task_id = task_id
        self._set_info_text(summary_text)

    def get_excel_file(self) -> str:
        return self._excel_file_path

    def _set_strategy_text(self, text: str):
        self.strategy_box.delete("1.0", "end")
        self.strategy_box.insert("1.0", text)

    def _set_info_text(self, text: str):
        self.info_box.delete("1.0", "end")
        self.info_box.insert("1.0", text)
        self.info_label.configure(text=text.splitlines()[0] if text else "")

    def _save_strategy_changes(self):
        job_label = self.job_combo.get().strip()
        payload = self.job_data_map.get(job_label)
        if not payload:
            messagebox.showwarning("提示", "请先选择岗位后再保存搜索词")
            return
        parsed = self._parse_strategy_text(self.strategy_box.get("1.0", "end"))
        if not any(parsed.values()):
            messagebox.showwarning("提示", "当前没有可保存的搜索词内容")
            return
        self.strategy_payload = parsed
        payload["strategy"] = parsed
        self.job_data_map[job_label] = payload
        self._set_strategy_text(self._format_strategy_text(parsed))
        self._set_info_text("已保存当前岗位的搜索策略修改，可直接继续抓取。")
        messagebox.showinfo("成功", "搜索策略已保存")

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

    def _parse_strategy_text(self, text: str) -> Dict[str, List[str]]:
        label_map = {
            "精准词": "precise_keywords",
            "扩池词": "expansion_keywords",
            "同义词": "synonyms",
            "排除词": "exclude_keywords",
            "布尔预留": "boolean_queries",
            "来源公司": "source_company_hints",
            "来源线索": "source_company_hints",
        }
        parsed = {
            "precise_keywords": [],
            "expansion_keywords": [],
            "synonyms": [],
            "exclude_keywords": [],
            "boolean_queries": [],
            "source_company_hints": [],
        }
        for block in text.splitlines():
            line = block.strip()
            if not line.startswith("【") or "】" not in line:
                continue
            label = line[1 : line.index("】")].strip()
            value_text = line[line.index("】") + 1 :].strip()
            target_key = label_map.get(label)
            if not target_key:
                continue
            values = [
                item.strip()
                for item in value_text.replace("，", "、").split("、")
                if item.strip()
            ]
            parsed[target_key] = values
        return parsed
