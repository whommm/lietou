"""Standalone search strategy confirmation tab."""

import copy
import customtkinter as ctk
from tkinter import messagebox
from typing import Callable, Dict, List, Optional


class SearchStrategyWidget(ctk.CTkFrame):
    """Let users inspect/edit generated Liepin search rounds."""

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
        on_save: Optional[Callable[[str, dict, dict], None]] = None,
        on_regenerate: Optional[Callable[[str, dict], None]] = None,
        theme: str = "light",
        **kwargs,
    ):
        super().__init__(master, **kwargs)
        self.on_pick_job_history = on_pick_job_history
        self.on_save = on_save
        self.on_regenerate = on_regenerate
        self.theme = theme
        self.job_options: List[str] = ["请先分析岗位"]
        self.job_data_map: Dict[str, Dict[str, object]] = {}
        self._selected_label = ""
        self._current_strategy: Dict[str, object] = {}
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
            text="搜索关键词",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=colors["text"],
        ).grid(row=0, column=0, padx=16, pady=(16, 4), sticky="w")
        ctk.CTkLabel(
            left,
            text="单独确认猎聘搜索栏、职位栏和每轮意图，再进入候选人抓取。",
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
        ).grid(row=3, column=0, padx=16, pady=(0, 10), sticky="ew")

        ctk.CTkButton(
            left,
            text="重新生成关键词",
            height=38,
            corner_radius=18,
            fg_color=colors["accent"],
            hover_color=colors["accent_hover"],
            text_color="#f8fbff",
            command=self._on_regenerate_click,
        ).grid(row=4, column=0, padx=16, pady=(0, 10), sticky="ew")

        ctk.CTkButton(
            left,
            text="保存当前策略",
            height=38,
            corner_radius=18,
            fg_color=colors["secondary"],
            hover_color=colors["secondary_hover"],
            text_color=colors["text"],
            command=self._on_save_click,
        ).grid(row=5, column=0, padx=16, pady=(0, 12), sticky="ew")

        self.status_label = ctk.CTkLabel(
            left,
            text="等待选择岗位。",
            text_color=colors["muted"],
            justify="left",
            wraplength=300,
        )
        self.status_label.grid(row=6, column=0, padx=16, pady=(0, 12), sticky="w")

        right = ctk.CTkFrame(self, fg_color="transparent")
        right.grid(row=0, column=1, padx=(6, 10), pady=10, sticky="nsew")
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(1, weight=1)

        self.meta_box = ctk.CTkTextbox(
            right,
            height=112,
            wrap="word",
            fg_color=colors["panel"],
            border_width=1,
            border_color=colors["border"],
            text_color=colors["text"],
        )
        self.meta_box.grid(row=0, column=0, sticky="ew", pady=(0, 8))

        self.round_box = ctk.CTkTextbox(
            right,
            wrap="word",
            fg_color=colors["panel"],
            border_width=1,
            border_color=colors["border"],
            text_color=colors["text"],
        )
        self.round_box.grid(row=1, column=0, sticky="nsew")

    def _on_pick_job_click(self):
        if self.on_pick_job_history:
            self.on_pick_job_history()

    def _on_regenerate_click(self):
        payload = self.job_data_map.get(self._selected_label)
        if not payload:
            messagebox.showwarning("提示", "请先选择岗位分析记录")
            return
        if self.on_regenerate:
            self.status_label.configure(text="正在重新生成搜索关键词...")
            self.on_regenerate(self._selected_label, payload)

    def _on_save_click(self):
        payload = self.job_data_map.get(self._selected_label)
        if not payload:
            messagebox.showwarning("提示", "请先选择岗位分析记录")
            return
        strategy = copy.deepcopy(self._current_strategy or {})
        strategy["executable_rounds"] = self._parse_round_text(
            self.round_box.get("1.0", "end"),
            strategy.get("executable_rounds", []),
        )
        if not strategy["executable_rounds"]:
            messagebox.showwarning("提示", "至少保留一轮可执行搜索")
            return
        if self.on_save:
            self.on_save(self._selected_label, payload, strategy)
        self.status_label.configure(text="搜索关键词已保存。")

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
        self._load_selected_strategy()

    def _load_selected_strategy(self):
        payload = self.job_data_map.get(self._selected_label, {})
        strategy = payload.get("strategy", {}) if payload else {}
        self.set_strategy(strategy if isinstance(strategy, dict) else {})

    def set_strategy(self, strategy: Dict[str, object]):
        self._current_strategy = copy.deepcopy(strategy or {})
        rounds = self._current_strategy.get("executable_rounds", [])
        filters = self._current_strategy.get("filters", {})
        if rounds:
            self.status_label.configure(text="已加载搜索关键词，可编辑后保存。")
        else:
            self.status_label.configure(text="该岗位还没有可执行搜索轮次，可点击重新生成。")

        self.meta_box.configure(state="normal")
        self.meta_box.delete("1.0", "end")
        self.meta_box.insert("1.0", self._build_meta_text(filters))
        self.meta_box.configure(state="disabled")

        self.round_box.delete("1.0", "end")
        self.round_box.insert("1.0", self._build_round_text(rounds))

    @staticmethod
    def _build_meta_text(filters: Dict[str, object]) -> str:
        filters = filters or {}
        cities = filters.get("目前城市") or []
        if isinstance(cities, str):
            cities = [cities]
        return "\n".join(
            [
                "执行筛选：",
                "城市：{}".format("、".join(cities) if cities else "全国"),
                "工作年限：{}".format(filters.get("工作年限") or "不限"),
                "教育经历：{}".format(filters.get("教育经历") or "不限"),
                "活跃度：{}".format(filters.get("活跃度") or "近一周"),
                "每轮人数：最多 30 人",
            ]
        )

    @staticmethod
    def _build_round_text(rounds: List[Dict[str, object]]) -> str:
        lines = []
        for index, item in enumerate(rounds or [], start=1):
            query = item.get("query") or ""
            position_filter = item.get("position_filter") or ""
            intent = item.get("intent") or ""
            if not query:
                continue
            line = "第{}轮：搜索栏：{}".format(index, query)
            if position_filter:
                line += "；职位栏：{}".format(position_filter)
            if intent:
                line += "；{}".format(intent)
            lines.append(line)
        return "\n".join(lines) if lines else "暂无可执行搜索轮次"

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
            if not line or line.startswith("暂无"):
                continue
            match = re.match(r"^第\s*(\d+)\s*轮[:：]\s*(.+)$", line)
            index = len(parsed) + 1
            body = line
            if match:
                index = int(match.group(1))
                body = match.group(2).strip()

            query = ""
            position_filter = ""
            intent = ""
            parts = [part.strip() for part in re.split(r"[；;]", body) if part.strip()]
            for part in parts:
                if part.startswith("搜索栏：") or part.startswith("搜索栏:"):
                    query = part.split("：", 1)[-1] if "：" in part else part.split(":", 1)[-1]
                elif part.startswith("职位栏：") or part.startswith("职位栏:"):
                    position_filter = part.split("：", 1)[-1] if "：" in part else part.split(":", 1)[-1]
                elif not intent:
                    intent = part
            if not query and parts:
                query = parts[0]
            query = query.strip()
            if not query or query in seen:
                continue
            seen.add(query)
            base = original_by_index.get(index, {})
            base.update(
                {
                    "label": base.get("label") or "第{}轮场景".format(index),
                    "query": query,
                    "intent": intent or base.get("intent") or "精准行业/业务场景",
                    "priority": len(parsed) + 1,
                    "match_mode": base.get("match_mode") or "all",
                    "scope": base.get("scope") or "全部经历",
                    "position_filter": position_filter or base.get("position_filter") or "产品",
                }
            )
            parsed.append(base)
        return parsed[:4]
