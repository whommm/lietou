"""Candidate capture task console."""

import customtkinter as ctk
from tkinter import messagebox
from typing import Callable, Dict, List, Optional

from ..utils.city_data import build_default_city_scope


class CityEditDialog(ctk.CTkToplevel):
    """Small modal dialog for editing the 4-city search scope."""

    def __init__(self, master, cities: List[str]):
        super().__init__(master)
        self.title("修改搜索城市")
        self.geometry("360x280")
        self.resizable(False, False)
        self.result: Optional[List[str]] = None
        self._default_cities = list(cities or [])
        self.entries = []

        labels = ["岗位城市（必填）", "周边城市1", "周边城市2", "周边城市3"]
        for index, label in enumerate(labels):
            ctk.CTkLabel(self, text=label).grid(row=index, column=0, padx=18, pady=(16 if index == 0 else 8, 4), sticky="w")
            entry = ctk.CTkEntry(self, height=34)
            entry.grid(row=index, column=1, padx=18, pady=(16 if index == 0 else 8, 4), sticky="ew")
            if index < len(self._default_cities):
                entry.insert(0, self._default_cities[index])
            self.entries.append(entry)
        self.grid_columnconfigure(1, weight=1)

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.grid(row=4, column=0, columnspan=2, padx=18, pady=18, sticky="ew")
        row.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(row, text="确认", command=self._confirm).grid(row=0, column=0, padx=(0, 6), sticky="ew")
        ctk.CTkButton(row, text="恢复默认", command=self._restore).grid(row=0, column=1, padx=(6, 0), sticky="ew")
        self.protocol("WM_DELETE_WINDOW", self.destroy)

    def _confirm(self):
        cities = []
        for entry in self.entries:
            city = entry.get().strip()
            if city and city not in cities:
                cities.append(city)
        if not cities:
            messagebox.showwarning("提示", "岗位城市不能为空")
            return
        self.result = cities[:4]
        self.destroy()

    def _restore(self):
        primary = self.entries[0].get().strip() or (self._default_cities[0] if self._default_cities else "")
        restored = build_default_city_scope(primary) if primary else self._default_cities
        for index, entry in enumerate(self.entries):
            entry.delete(0, "end")
            if index < len(restored):
                entry.insert(0, restored[index])


class AutoGrabConfirmDialog(ctk.CTkToplevel):
    """Modal 15-second confirmation dialog before automatic capture starts."""

    def __init__(self, master, job_label: str, payload: dict, filters: Dict[str, object], auto_match_available: bool = True):
        super().__init__(master)
        self.title("自动抓取确认")
        self.geometry("620x520")
        self.resizable(False, False)
        self.result: Optional[Dict[str, object]] = None
        self._seconds = 15
        self._closed = False
        self.job_label = job_label
        self.payload = payload or {}
        self.filters = dict(filters or {})
        self.auto_match_available = auto_match_available
        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self.after(1000, self._tick)
        self.lift()
        self.attributes('-topmost', True)

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self, text="即将按以下条件自动抓取", font=ctk.CTkFont(size=20, weight="bold")).grid(row=0, column=0, padx=22, pady=(22, 8), sticky="w")
        ctk.CTkLabel(self, text=self.job_label, wraplength=560, justify="left").grid(row=1, column=0, padx=22, pady=(0, 12), sticky="w")

        self.filter_box = ctk.CTkTextbox(self, height=105, wrap="word")
        self.filter_box.grid(row=2, column=0, padx=22, pady=(0, 10), sticky="ew")
        self._refresh_filter_box()

        ctk.CTkButton(self, text="修改城市", command=self._edit_cities).grid(row=3, column=0, padx=22, pady=(0, 12), sticky="w")

        self.round_box = ctk.CTkTextbox(self, height=150, wrap="word")
        self.round_box.grid(row=4, column=0, padx=22, pady=(0, 14), sticky="ew")
        self.round_box.insert("1.0", self._build_round_text())

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.grid(row=5, column=0, padx=22, pady=(0, 8), sticky="ew")
        row.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(row, text="立即开始", command=self._confirm).grid(row=0, column=0, padx=(0, 8), sticky="ew")
        ctk.CTkButton(row, text="取消", command=self._cancel).grid(row=0, column=1, padx=(8, 0), sticky="ew")

        self.countdown_label = ctk.CTkLabel(self, text="15 秒后自动开始...")
        self.countdown_label.grid(row=6, column=0, padx=22, pady=(0, 18))

        if not self.auto_match_available:
            warning_label = ctk.CTkLabel(
                self,
                text="⚠️ 未配置有效的 LLM API，抓取后将不会自动进行批量匹配",
                text_color="#e74c3c",
                font=ctk.CTkFont(size=12, weight="bold"),
            )
            warning_label.grid(row=7, column=0, padx=22, pady=(0, 10), sticky="w")

    def _build_round_text(self) -> str:
        strategy = self.payload.get("strategy", {}) if self.payload else {}
        rounds = strategy.get("executable_rounds", []) if isinstance(strategy, dict) else []
        lines = ["搜索计划（共 {} 轮，每轮最多 30 人）：".format(len(rounds))]
        for index, item in enumerate(rounds[:8], start=1):
            lines.append("第{}轮：{}".format(index, item.get("query") or item.get("label") or "未命名搜索"))
        if not rounds:
            lines.append("暂无可执行轮次，将使用默认关键词。")
        lines.append("")
        lines.append("执行策略：每轮抓取后自动批量匹配。")
        return "\n".join(lines)

    def _refresh_filter_box(self):
        self.filter_box.configure(state="normal")
        self.filter_box.delete("1.0", "end")
        self.filter_box.insert("1.0", self._build_filter_text(self.filters))

    @staticmethod
    def _build_filter_text(filters: Dict[str, object]) -> str:
        cities = filters.get("目前城市") or []
        if isinstance(cities, str):
            cities = [cities]
        return "\n".join(
            [
                "城市：{}".format("、".join(cities) if cities else "全国"),
                "工作年限：{}".format(filters.get("工作年限") or "不限"),
                "教育经历：{}".format(filters.get("教育经历") or "不限"),
                "性别：{}".format(filters.get("性别") or "不限"),
                "活跃度：{}".format(filters.get("活跃度") or "不限"),
            ]
        )

    def _edit_cities(self):
        cities = self.filters.get("目前城市") or []
        if isinstance(cities, str):
            cities = [cities]
        dialog = CityEditDialog(self, list(cities))
        dialog.transient(self)
        dialog.grab_set()
        self.wait_window(dialog)
        if dialog.result:
            self.filters["目前城市"] = dialog.result
            self._refresh_filter_box()

    def _tick(self):
        if self._closed:
            return
        self._seconds -= 1
        if self._seconds <= 0:
            self._confirm()
            return
        self.countdown_label.configure(text="{} 秒后自动开始...".format(self._seconds))
        self.after(1000, self._tick)

    def _confirm(self):
        self._closed = True
        self.filters = self._parse_filter_text(self.filter_box.get("1.0", "end"))
        self._apply_edited_rounds()
        self.result = dict(self.filters)
        self.destroy()

    def _cancel(self):
        self._closed = True
        self.result = None
        self.destroy()

    @staticmethod
    def _parse_filter_text(text: str) -> Dict[str, object]:
        filters: Dict[str, object] = {}
        for raw_line in (text or "").splitlines():
            line = raw_line.strip()
            if not line or "：" not in line:
                continue
            key, value = [part.strip() for part in line.split("：", 1)]
            if key == "城市":
                cities = [
                    city.strip()
                    for city in value.replace(",", "、").replace("，", "、").split("、")
                    if city.strip() and city.strip() != "全国"
                ]
                if cities:
                    filters["目前城市"] = cities[:4]
            elif key == "工作年限" and value and value != "不限":
                filters["工作年限"] = value
            elif key == "教育经历" and value and value != "不限":
                filters["教育经历"] = value
            elif key == "性别" and value and value != "不限":
                filters["性别"] = value
            elif key == "性别" and value == "不限":
                filters["性别"] = value
            elif key == "活跃度" and value and value != "不限":
                filters["活跃度"] = value
        return filters

    def _apply_edited_rounds(self) -> None:
        strategy = self.payload.get("strategy", {}) if isinstance(self.payload, dict) else {}
        if not isinstance(strategy, dict):
            return
        original_rounds = strategy.get("executable_rounds", [])
        parsed_rounds = self._parse_round_text(
            self.round_box.get("1.0", "end"),
            original_rounds if isinstance(original_rounds, list) else [],
        )
        if parsed_rounds:
            strategy["executable_rounds"] = parsed_rounds

    @staticmethod
    def _parse_round_text(text: str, original_rounds: List[Dict[str, object]]) -> List[Dict[str, object]]:
        import re

        original_by_index = {
            index: dict(item)
            for index, item in enumerate(original_rounds or [], start=1)
            if isinstance(item, dict)
        }
        parsed = []
        seen = set()
        for raw_line in (text or "").splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith("搜索计划") or line.startswith("执行策略") or line.startswith("暂无"):
                continue
            match = re.match(r"^(?:-?\s*)?第\s*(\d+)\s*轮(?:[^:：]*)[:：]\s*(.+)$", line)
            if match:
                index = int(match.group(1))
                query = match.group(2).strip()
            else:
                match = re.match(r"^(?:-?\s*)?([^:：]+)[:：]\s*(.+)$", line)
                index = len(parsed) + 1
                query = match.group(2).strip() if match else line
            if not query or query in seen:
                continue
            seen.add(query)
            base = original_by_index.get(index, {})
            base.update(
                {
                    "label": base.get("label") or "第{}轮搜索".format(index),
                    "query": query,
                    "priority": base.get("priority") or index,
                    "match_mode": base.get("match_mode") or "all",
                    "scope": base.get("scope") or "全部经历",
                }
            )
            parsed.append(base)
        return parsed


class CandidateLibraryWidget(ctk.CTkFrame):
    """Candidate capture workspace focused on task control."""

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
        on_launch_browser: Callable,
        on_check_login: Callable,
        on_run_task: Callable,
        on_import_excel: Optional[Callable] = None,
        on_open_excel: Optional[Callable] = None,
        on_open_excel_dir: Optional[Callable] = None,
        on_export_debug: Optional[Callable] = None,
        on_close_browser: Optional[Callable] = None,
        on_pick_job_history: Optional[Callable] = None,
        get_auto_match_status: Optional[Callable[[], bool]] = None,
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
        self.on_close_browser = on_close_browser
        self.on_pick_job_history = on_pick_job_history
        self.get_auto_match_status = get_auto_match_status
        self.theme = theme

        self.job_options: List[str] = ["请先分析岗位"]
        self.job_data_map: Dict[str, Dict[str, object]] = {}
        self.strategy_payload: Dict[str, List[str]] = {}
        self.current_filters: Dict[str, object] = {}
        self.task_id: str = ""
        self._excel_file_path: str = ""
        self._candidate_records: List[Dict] = []
        self._current_task_id: Optional[str] = None

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
        colors = self.PALETTE
        frame = ctk.CTkFrame(
            self,
            corner_radius=22,
            fg_color=colors["panel"],
            border_width=1,
            border_color=colors["border"],
        )
        frame.grid(row=0, column=0, columnspan=2, padx=10, pady=(10, 6), sticky="ew")
        frame.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)

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

        self.close_browser_btn = ctk.CTkButton(
            frame,
            text="关闭浏览器",
            height=40,
            corner_radius=18,
            fg_color=colors["secondary"],
            hover_color=colors["secondary_hover"],
            text_color=colors["text"],
            command=self._on_close_browser_click,
        )
        self.close_browser_btn.grid(row=0, column=1, padx=6, pady=14, sticky="ew")

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
        self.check_login_btn.grid(row=0, column=2, padx=6, pady=14, sticky="ew")

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
        self.run_task_btn.grid(row=0, column=3, padx=6, pady=14, sticky="ew")

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
        self.debug_btn.grid(row=0, column=4, padx=(6, 14), pady=14, sticky="ew")

    def _build_control_panel(self):
        colors = self.PALETTE
        frame = ctk.CTkScrollableFrame(
            self,
            corner_radius=24,
            fg_color=colors["panel"],
            border_width=1,
            border_color=colors["border"],
            scrollbar_button_color=colors["accent"],
            scrollbar_button_hover_color=colors["accent_hover"],
        )
        frame.grid(row=1, column=0, padx=(10, 6), pady=(0, 10), sticky="nsew")
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(6, weight=1)

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

        self.job_display = ctk.CTkEntry(
            picker_row,
            state="readonly",
            corner_radius=16,
            height=38,
            fg_color=colors["panel_alt"],
            border_color=colors["border"],
            text_color=colors["text"],
        )
        self.job_display.grid(row=0, column=0, sticky="ew")

        self.pick_job_btn = ctk.CTkButton(
            picker_row,
            text="选择 ▼",
            width=80,
            height=38,
            corner_radius=18,
            fg_color=colors["secondary"],
            hover_color=colors["secondary_hover"],
            text_color=colors["text"],
            command=self._on_pick_job_click,
        )
        self.pick_job_btn.grid(row=0, column=1, padx=(10, 0), sticky="e")

        limit_frame = ctk.CTkFrame(frame, fg_color="transparent")
        limit_frame.grid(row=4, column=0, padx=16, pady=(0, 10), sticky="ew")
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
        self.max_candidates_entry.insert(0, "90")

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

        plan_header = ctk.CTkFrame(frame, fg_color="transparent")
        plan_header.grid(row=5, column=0, padx=16, pady=(8, 6), sticky="ew")
        plan_header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            plan_header,
            text="抓取计划",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=colors["text"],
        ).grid(row=0, column=0, sticky="w")
        self.edit_city_btn = ctk.CTkButton(
            plan_header,
            text="修改城市",
            width=86,
            height=30,
            corner_radius=14,
            fg_color=colors["secondary"],
            hover_color=colors["secondary_hover"],
            text_color=colors["text"],
            command=self._on_edit_cities_click,
        )
        self.edit_city_btn.grid(row=0, column=1, sticky="e")

        self.plan_box = ctk.CTkTextbox(
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
        self.plan_box.grid(row=6, column=0, padx=16, pady=(0, 18), sticky="nsew")
        self.plan_box.insert("1.0", "选择岗位后显示抓取计划。")


    def _build_status_panel(self):
        colors = self.PALETTE
        frame = ctk.CTkFrame(
            self,
            corner_radius=24,
            fg_color=colors["panel"],
            border_width=1,
            border_color=colors["border"],
        )
        frame.grid(row=1, column=1, padx=(6, 10), pady=(0, 10), sticky="nsew")
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(4, weight=0)
        frame.grid_rowconfigure(5, weight=1)

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
        self.info_box.grid(row=4, column=0, padx=16, pady=(0, 10), sticky="ew")
        self.info_box.insert(
            "1.0",
            "未创建搜索任务。\n抓取完成后，这里会显示处理页数、成功数、失败数和文件位置。",
        )

        self.candidate_list_box = ctk.CTkTextbox(
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
        self.candidate_list_box.grid(row=5, column=0, padx=16, pady=(0, 10), sticky="nsew")
        self.candidate_list_box.insert("1.0", "暂无候选人记录。")

        self.info_label = ctk.CTkLabel(
            frame,
            text="等待开始抓取。",
            text_color=colors["muted"],
            font=ctk.CTkFont(size=12),
            justify="left",
            wraplength=420,
        )
        self.info_label.grid(row=6, column=0, padx=16, pady=(0, 16), sticky="w")

    def _on_pick_job_click(self):
        if self.on_pick_job_history:
            self.on_pick_job_history()

    def _on_job_selected(self, value: str):
        payload = self.job_data_map.get(value)
        if not payload:
            self.strategy_payload = {}
            self.current_filters = {}
            self._set_info_text("请先从岗位分析同步搜索策略。")
            self._set_plan_text("选择岗位后显示抓取计划。")
            return
        self.strategy_payload = payload.get("strategy", {})
        self.current_filters = dict(self.strategy_payload.get("filters", {}) or {})
        self.task_id = ""
        preview = self._build_strategy_preview_text(value, payload)
        self._set_info_text(preview)
        self._set_plan_text(preview)

    def _on_run_task_click(self):
        job_label = self.job_display.get().strip()
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
        auto_match_available = True
        if callable(self.get_auto_match_status):
            auto_match_available = self.get_auto_match_status()
        filters = self._confirm_before_run(job_label, payload, auto_match_available)
        if filters is None:
            self._set_info_text("已取消自动抓取。")
            return
        self.current_filters = dict(filters)
        self._set_info_text("正在将抓取任务提交到后台队列...")
        self.on_run_task(job_label, payload, filters, max_candidates, max_pages)

    def run_selected_task(self):
        """Start the currently selected capture task, including confirmation dialog."""
        self._on_run_task_click()

    def _confirm_before_run(self, job_label: str, payload: Dict[str, object], auto_match_available: bool = True):
        dialog = AutoGrabConfirmDialog(self, job_label, payload, self.current_filters, auto_match_available)
        dialog.transient(self)
        dialog.grab_set()
        self.wait_window(dialog)
        return dialog.result

    def _on_edit_cities_click(self):
        cities = self.current_filters.get("目前城市") or []
        if isinstance(cities, str):
            cities = [cities]
        dialog = CityEditDialog(self, list(cities))
        dialog.transient(self)
        dialog.grab_set()
        self.wait_window(dialog)
        if dialog.result:
            self.current_filters["目前城市"] = dialog.result
            self._set_plan_text(
                self._build_strategy_preview_text(
                    self.job_display.get().strip(),
                    self.job_data_map.get(self.job_display.get().strip(), {}),
                )
            )

    def _on_export_debug_click(self):
        if self.on_export_debug:
            self.on_export_debug()

    def _on_close_browser_click(self):
        if self.on_close_browser:
            self.on_close_browser()

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
        if self.job_options:
            self.set_selected_job(self.job_options[0])

    def set_selected_job(self, job_label: str):
        self.job_display.configure(state="normal")
        self.job_display.delete(0, "end")
        self.job_display.insert(0, job_label)
        self.job_display.configure(state="readonly")
        self._on_job_selected(job_label)

    def set_running(self, running: bool, task_id: Optional[str] = None):
        if running and task_id:
            self._current_task_id = task_id
        self.run_task_btn.configure(
            state="disabled" if running else "normal",
            text="抓取中..." if running else "开始抓取并写入 Excel",
        )

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

    def get_current_task_id(self) -> Optional[str]:
        return self._current_task_id

    def _set_info_text(self, text: str):
        self.info_box.delete("1.0", "end")
        self.info_box.insert("1.0", text)
        self.info_label.configure(text=text.splitlines()[0] if text else "")

    def _set_plan_text(self, text: str):
        self.plan_box.configure(state="normal")
        self.plan_box.delete("1.0", "end")
        self.plan_box.insert("1.0", text)
        self.plan_box.configure(state="disabled")

    def _build_strategy_preview_text(self, job_label: str, payload: Dict[str, object]) -> str:
        strategy = payload.get("strategy", {}) if payload else {}
        rounds = strategy.get("executable_rounds", []) if isinstance(strategy, dict) else []
        atomic_terms = strategy.get("atomic_terms", {}) if isinstance(strategy, dict) else {}
        filters = dict(self.current_filters or strategy.get("filters", {}) or {})

        lines = ["已选择岗位：{}".format(job_label)]
        cities = filters.get("目前城市") or []
        if isinstance(cities, str):
            cities = [cities]
        lines.append("筛选条件：")
        lines.append("- 城市：{}".format("、".join(cities) if cities else "全国"))
        lines.append("- 工作年限：{}".format(filters.get("工作年限") or "不限"))
        lines.append("- 教育经历：{}".format(filters.get("教育经历") or "不限"))
        lines.append("- 性别：{}".format(filters.get("性别") or "不限"))
        lines.append("- 活跃度：{}".format(filters.get("活跃度") or "不限"))
        if rounds:
            lines.append("搜索轮次（{} 条）：每轮最多30人".format(len(rounds)))
            for item in rounds[:4]:
                label = item.get("label") or "搜索"
                query = item.get("query") or ""
                if query:
                    position_filter = item.get("position_filter") or ""
                    suffix = "；职位栏：{}".format(position_filter) if position_filter else ""
                    lines.append("- {}: 搜索栏：{}{}".format(label, query, suffix))
        else:
            precise = strategy.get("precise_keywords", []) if isinstance(strategy, dict) else []
            if precise:
                lines.append("首选关键词：{}".format(" / ".join(precise[:3])))

        capability_terms = atomic_terms.get("capability_terms", []) if isinstance(atomic_terms, dict) else []
        domain_terms = atomic_terms.get("domain_terms", []) if isinstance(atomic_terms, dict) else []
        if capability_terms or domain_terms:
            lines.append(
                "原子词：能力[{}] 领域[{}]".format(
                    " / ".join(capability_terms[:3]) or "无",
                    " / ".join(domain_terms[:3]) or "无",
                )
            )
        lines.append("等待开始抓取。")
        return "\n".join(lines)

    def set_candidate_records(self, records: List[Dict]):
        self._candidate_records = records or []
        self._refresh_candidate_list()

    def _refresh_candidate_list(self):
        if not self._candidate_records:
            self.candidate_list_box.delete("1.0", "end")
            self.candidate_list_box.insert("1.0", "暂无候选人记录。")
            return
        lines = [
            "候选人列表（共 {} 位）：".format(len(self._candidate_records))
        ]
        for rec in self._candidate_records:
            status = rec.get("capture_status", "未知")
            source_keyword = rec.get("source_keyword", "")
            lines.append(
                "- {} [{}]{}".format(
                    rec.get("name") or "未命名",
                    status,
                    " <{}>".format(source_keyword) if source_keyword else "",
                )
            )
        self.candidate_list_box.delete("1.0", "end")
        self.candidate_list_box.insert("1.0", "\n".join(lines))
