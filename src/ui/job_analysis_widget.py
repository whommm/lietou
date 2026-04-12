"""岗位分析 UI 组件。"""

import json
import re

import customtkinter as ctk
from tkinter import messagebox
from typing import Callable, List, Optional

from ..core.history import HistoryManager
from ..models import MatchCriteria
from ..utils.helpers import copy_to_clipboard
from .history_widget import HistoryPanel
from .html_renderer import HtmlRenderer
from .match_criteria_editor import MatchCriteriaEditor


def _extract_match_criteria_from_html(html_text: str) -> Optional[MatchCriteria]:
    """Try to extract the trailing JSON match criteria from an analysis result."""
    if not html_text:
        return None
    # 1. greedy regex for trailing JSON
    m = re.search(r"\{.*\}\s*$", html_text, re.DOTALL)
    if m:
        try:
            return MatchCriteria.from_dict(json.loads(m.group(0)))
        except (ValueError, TypeError):
            pass
    # 2. markdown fenced json at end
    m = re.search(r"```json\s*(\{.*\})\s*```\s*$", html_text, re.DOTALL)
    if m:
        try:
            return MatchCriteria.from_dict(json.loads(m.group(1)))
        except (ValueError, TypeError):
            pass
    # 3. pre/code tags
    m = re.search(r"<(?:pre|code)[^>]*>(\{.*\})</(?:pre|code)>\s*$", html_text, re.DOTALL | re.IGNORECASE)
    if m:
        try:
            return MatchCriteria.from_dict(json.loads(m.group(1)))
        except (ValueError, TypeError):
            pass
    return None


class JobAnalysisWidget(ctk.CTkFrame):
    """岗位分析页面组件。"""

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
        on_analyze: Callable,
        history_manager: HistoryManager,
        company_options: List[str],
        on_send_to_candidates: Optional[Callable] = None,
        on_pick_company_history: Optional[Callable] = None,
        on_history_changed: Optional[Callable] = None,
        on_save_match_criteria: Optional[Callable[[MatchCriteria], None]] = None,
        theme: str = "light",
        **kwargs,
    ):
        super().__init__(master, **kwargs)
        self.on_analyze = on_analyze
        self.history_manager = history_manager
        self.on_send_to_candidates = on_send_to_candidates
        self.on_pick_company_history = on_pick_company_history
        self.on_history_changed = on_history_changed
        self.on_save_match_criteria = on_save_match_criteria
        self.theme = theme

        self.history_panel: Optional[HistoryPanel] = None
        self._showing_history = False
        self._result_buffer = ""
        self._current_match_criteria: Optional[MatchCriteria] = None

        self._setup_ui(company_options)

    def _setup_ui(self, company_options: List[str]):
        """设置 UI 布局。"""
        self.configure(fg_color="transparent")
        self.grid_columnconfigure(0, weight=2)
        self.grid_columnconfigure(1, weight=3)
        self.grid_rowconfigure(0, weight=1)

        self._build_input_panel(company_options)
        self._build_result_panel()

    def _build_input_panel(self, company_options: List[str]):
        """构建左侧输入面板。"""
        colors = self.PALETTE
        input_frame = ctk.CTkFrame(
            self,
            corner_radius=24,
            fg_color=colors["panel"],
            border_width=1,
            border_color=colors["border"],
        )
        input_frame.grid(row=0, column=0, padx=(10, 5), pady=10, sticky="nsew")
        input_frame.grid_columnconfigure(0, weight=1)
        input_frame.grid_rowconfigure(4, weight=1)

        ctk.CTkLabel(
            input_frame,
            text="原始岗位描述 (JD)",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=colors["text"],
        ).grid(row=0, column=0, padx=16, pady=(16, 5), sticky="w")

        ctk.CTkLabel(
            input_frame,
            text="输入岗位描述，系统会产出岗位画像、门槛拆解和搜寻建议。",
            font=ctk.CTkFont(size=12),
            text_color=colors["muted"],
        ).grid(row=1, column=0, padx=16, pady=(0, 12), sticky="w")

        ctk.CTkLabel(
            input_frame, text="参考公司调研（可选）:", text_color=colors["text"]
        ).grid(row=2, column=0, padx=16, pady=(8, 6), sticky="w")
        picker_row = ctk.CTkFrame(input_frame, fg_color="transparent")
        picker_row.grid(row=3, column=0, padx=16, pady=(0, 8), sticky="ew")
        picker_row.grid_columnconfigure(0, weight=1)

        self.company_display = ctk.CTkEntry(
            picker_row,
            state="readonly",
            corner_radius=16,
            height=38,
            fg_color=colors["panel_alt"],
            border_color=colors["border"],
            text_color=colors["text"],
        )
        self.company_display.grid(row=0, column=0, sticky="ew")

        self.company_picker_btn = ctk.CTkButton(
            picker_row,
            text="选择 ▼",
            width=80,
            height=38,
            corner_radius=18,
            fg_color=colors["secondary"],
            hover_color=colors["secondary_hover"],
            text_color=colors["text"],
            command=self._on_open_company_picker,
        )
        self.company_picker_btn.grid(row=0, column=1, padx=(10, 0), sticky="e")
        if company_options:
            self.set_selected_company(company_options[0])

        self.jd_textbox = ctk.CTkTextbox(
            input_frame,
            wrap="word",
            corner_radius=18,
            border_width=1,
            border_color=colors["border"],
            fg_color=colors["panel_alt"],
            text_color=colors["text"],
            scrollbar_button_color=colors["accent"],
            scrollbar_button_hover_color=colors["accent_hover"],
        )
        self.jd_textbox.grid(row=4, column=0, padx=16, pady=8, sticky="nsew")

        btn_frame = ctk.CTkFrame(input_frame, fg_color="transparent")
        btn_frame.grid(row=5, column=0, padx=16, pady=(4, 16), sticky="ew")
        btn_frame.grid_columnconfigure(0, weight=1)

        self.clear_input_btn = ctk.CTkButton(
            btn_frame,
            text="清空",
            width=84,
            height=38,
            corner_radius=18,
            fg_color=colors["secondary"],
            hover_color=colors["secondary_hover"],
            text_color=colors["text"],
            command=self._on_clear_input_click,
        )
        self.clear_input_btn.grid(row=0, column=0, padx=5, sticky="w")

        self.analyze_btn = ctk.CTkButton(
            btn_frame,
            text="开始分析",
            width=150,
            height=40,
            corner_radius=20,
            fg_color=colors["accent"],
            hover_color=colors["accent_hover"],
            text_color="#f8fbff",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._on_analyze_click,
        )
        self.analyze_btn.grid(row=0, column=1, padx=5, sticky="e")

        self.send_candidates_btn = ctk.CTkButton(
            btn_frame,
            text="发送到候选人库",
            width=140,
            height=38,
            corner_radius=18,
            fg_color=colors["secondary"],
            hover_color=colors["secondary_hover"],
            text_color=colors["text"],
            command=self._on_send_to_candidates_click,
        )
        self.send_candidates_btn.grid(row=0, column=2, padx=(5, 0), sticky="e")

    def _build_result_panel(self):
        """构建右侧结果面板。"""
        colors = self.PALETTE
        result_frame = ctk.CTkFrame(
            self,
            corner_radius=24,
            fg_color=colors["panel"],
            border_width=1,
            border_color=colors["border"],
        )
        result_frame.grid(row=0, column=1, padx=(5, 10), pady=10, sticky="nsew")
        result_frame.grid_columnconfigure(0, weight=1)
        result_frame.grid_rowconfigure(1, weight=1)

        header_frame = ctk.CTkFrame(result_frame, fg_color="transparent")
        header_frame.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="ew")
        header_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header_frame,
            text="分析结果",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=colors["text"],
        ).pack(side="left")

        btn_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        btn_frame.pack(side="right")

        self.history_btn = ctk.CTkButton(
            btn_frame,
            text="历史",
            width=60,
            height=32,
            corner_radius=16,
            fg_color=colors["secondary"],
            hover_color=colors["secondary_hover"],
            text_color=colors["text"],
            command=self._on_history_click,
        )
        self.history_btn.pack(side="right", padx=5)

        self.copy_all_btn = ctk.CTkButton(
            btn_frame,
            text="复制全部",
            width=80,
            height=32,
            corner_radius=16,
            fg_color=colors["secondary"],
            hover_color=colors["secondary_hover"],
            text_color=colors["text"],
            command=self._on_copy_all_click,
        )
        self.copy_all_btn.pack(side="right", padx=5)

        self.clear_result_btn = ctk.CTkButton(
            btn_frame,
            text="清空",
            width=60,
            height=32,
            corner_radius=16,
            fg_color=colors["secondary"],
            hover_color=colors["secondary_hover"],
            text_color=colors["text"],
            command=self._on_clear_result_click,
        )
        self.clear_result_btn.pack(side="right", padx=5)

        self.result_tabview = ctk.CTkTabview(
            result_frame,
            corner_radius=18,
            fg_color=colors["panel"],
            border_width=1,
            border_color=colors["border"],
            segmented_button_fg_color=colors["secondary"],
            segmented_button_selected_color=colors["accent"],
            segmented_button_selected_hover_color=colors["accent_hover"],
            segmented_button_unselected_color=colors["secondary"],
            segmented_button_unselected_hover_color=colors["secondary_hover"],
            text_color=colors["text"],
        )
        self.result_tabview.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")

        tab_result = self.result_tabview.add("分析结果")
        tab_criteria = self.result_tabview.add("匹配条件")

        self.html_renderer = HtmlRenderer(tab_result, theme=self.theme)
        self.html_renderer.pack(fill="both", expand=True, padx=5, pady=5)

        self.match_criteria_editor = MatchCriteriaEditor(
            tab_criteria,
            criteria=MatchCriteria(),
            on_save=self._on_match_criteria_save,
            theme=self.theme,
        )
        self.match_criteria_editor.pack(fill="both", expand=True, padx=5, pady=5)

        self._result_parent = result_frame

    def _on_analyze_click(self):
        """分析按钮点击事件。"""
        jd_text = self.get_jd_text()
        if not jd_text:
            messagebox.showwarning("提示", "请先输入岗位描述")
            return
        self.on_analyze(jd_text, self.get_selected_company())

    def _on_clear_input_click(self):
        """清空输入。"""
        self.jd_textbox.delete("1.0", "end")

    def _on_open_company_picker(self):
        """打开公司调研历史选择器。"""
        if self.on_pick_company_history:
            self.on_pick_company_history()

    def _on_company_record_selected(self, record):
        """选择公司历史后更新快捷选择。"""
        self.set_selected_company(record.title)

    def _on_clear_result_click(self):
        """清空结果。"""
        self.clear_result()

    def _on_copy_all_click(self):
        """复制结果。"""
        content = self.get_result()
        if not content:
            messagebox.showwarning("提示", "没有可复制的内容")
            return

        if copy_to_clipboard(content):
            messagebox.showinfo("成功", "已复制到剪贴板")
        else:
            messagebox.showerror("错误", "复制失败")

    def _on_history_click(self):
        """历史按钮点击事件。"""
        if self._showing_history:
            self._hide_history()
        else:
            self._show_history()

    def _on_send_to_candidates_click(self):
        """发送当前岗位分析到候选人库。"""
        if not self.on_send_to_candidates:
            return
        jd_text = self.get_jd_text()
        result = self.get_result()
        if not jd_text or not result:
            messagebox.showwarning("提示", "请先完成岗位分析后再发送到候选人库")
            return
        self.on_send_to_candidates(jd_text, result)

    def _show_history(self):
        """显示历史面板。"""
        self.result_tabview.grid_forget()

        if self.history_panel is None:
            self.history_panel = HistoryPanel(
                self._result_parent,
                history_manager=self.history_manager,
                on_load_record=self._on_load_history,
                on_history_changed=self.on_history_changed,
            )
        else:
            self.history_panel.refresh()

        self.history_panel.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")
        self._showing_history = True
        self.history_btn.configure(text="返回")

    def _hide_history(self):
        """隐藏历史面板。"""
        if self.history_panel:
            self.history_panel.grid_forget()
        self.result_tabview.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")
        self._showing_history = False
        self.history_btn.configure(text="历史")

    def _on_load_history(self, record):
        """加载历史记录。"""
        self._hide_history()
        self.set_jd_text(record.jd_text)
        self.set_result(record.result)
        # Also restore match criteria if persisted
        if record.match_criteria_json:
            try:
                mc = MatchCriteria.from_dict(json.loads(record.match_criteria_json))
                self.set_match_criteria(mc)
            except (ValueError, TypeError):
                pass

    def _on_match_criteria_save(self, criteria: MatchCriteria):
        if self.on_save_match_criteria:
            self.on_save_match_criteria(criteria)

    def get_jd_text(self) -> str:
        """获取 JD 输入内容。"""
        return self.jd_textbox.get("1.0", "end").strip()

    def set_jd_text(self, text: str):
        """设置 JD 输入内容。"""
        self.jd_textbox.delete("1.0", "end")
        self.jd_textbox.insert("1.0", text)

    def show_loading(self):
        """显示加载状态。"""
        if self._showing_history:
            self._hide_history()
        self._result_buffer = ""
        self.result_tabview.set("分析结果")
        self.html_renderer.show_loading("job_analysis")

    def clear_result(self):
        """清空结果。"""
        if self._showing_history:
            self._hide_history()
        self._result_buffer = ""
        self._current_match_criteria = None
        self.html_renderer.clear()
        self.match_criteria_editor.set_criteria(MatchCriteria())

    def set_result(self, text: str):
        """设置结果内容。"""
        if self._showing_history:
            self._hide_history()
        self._result_buffer = text
        self.result_tabview.set("分析结果")
        self.html_renderer.set_content(text)

        # Try to extract match criteria from the trailing JSON
        criteria = _extract_match_criteria_from_html(text)
        if criteria is not None:
            self._current_match_criteria = criteria
            self.match_criteria_editor.set_criteria(criteria, set_as_default=True)
            self.result_tabview.set("匹配条件")
        else:
            self._current_match_criteria = None
            self.match_criteria_editor.set_criteria(MatchCriteria())

    def get_result(self) -> str:
        """获取结果内容。"""
        return self._result_buffer

    def get_match_criteria(self) -> Optional[MatchCriteria]:
        return self.match_criteria_editor.get_criteria()

    def set_match_criteria(self, criteria: MatchCriteria):
        self._current_match_criteria = criteria
        self.match_criteria_editor.set_criteria(criteria, set_as_default=True)

    def set_analyzing(self, analyzing: bool):
        """设置分析状态。"""
        if analyzing:
            self.analyze_btn.configure(state="disabled", text="AI 正在思考中...")
            self.clear_input_btn.configure(state="disabled")
            self.company_picker_btn.configure(state="disabled")
            self.copy_all_btn.configure(state="disabled")
            self.clear_result_btn.configure(state="disabled")
            self.history_btn.configure(state="disabled")
            self.send_candidates_btn.configure(state="disabled")
            self.company_display.configure(state="disabled")
            self.jd_textbox.configure(state="disabled")
        else:
            self.analyze_btn.configure(state="normal", text="开始分析")
            self.clear_input_btn.configure(state="normal")
            self.company_picker_btn.configure(state="normal")
            self.copy_all_btn.configure(state="normal")
            self.clear_result_btn.configure(state="normal")
            self.history_btn.configure(state="normal")
            self.send_candidates_btn.configure(state="normal")
            self.company_display.configure(state="normal")
            self.jd_textbox.configure(state="normal")

    def set_theme(self, theme: str):
        """设置主题（当前仅支持 light）。"""
        self.html_renderer.set_theme(theme)
