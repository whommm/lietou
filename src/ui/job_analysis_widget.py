"""岗位分析 UI 组件。"""

import customtkinter as ctk
from tkinter import messagebox
from typing import Callable, List, Optional

from ..core.history import HistoryManager
from ..utils.helpers import copy_to_clipboard
from .history_widget import HistoryPanel
from .html_renderer import HtmlRenderer


class JobAnalysisWidget(ctk.CTkFrame):
    """岗位分析页面组件。"""

    def __init__(
        self,
        master,
        on_analyze: Callable,
        history_manager: HistoryManager,
        company_options: List[str],
        theme: str = "light",
        **kwargs,
    ):
        super().__init__(master, **kwargs)
        self.on_analyze = on_analyze
        self.history_manager = history_manager
        self.theme = theme

        self.history_panel: Optional[HistoryPanel] = None
        self._showing_history = False
        self._result_buffer = ""

        self._setup_ui(company_options)

    def _setup_ui(self, company_options: List[str]):
        """设置 UI 布局。"""
        self.grid_columnconfigure(0, weight=2)
        self.grid_columnconfigure(1, weight=3)
        self.grid_rowconfigure(0, weight=1)

        self._build_input_panel(company_options)
        self._build_result_panel()

    def _build_input_panel(self, company_options: List[str]):
        """构建左侧输入面板。"""
        input_frame = ctk.CTkFrame(self)
        input_frame.grid(row=0, column=0, padx=(10, 5), pady=10, sticky="nsew")
        input_frame.grid_columnconfigure(0, weight=1)
        input_frame.grid_rowconfigure(4, weight=1)

        ctk.CTkLabel(
            input_frame,
            text="原始岗位描述 (JD)",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).grid(row=0, column=0, padx=10, pady=(10, 5), sticky="w")

        ctk.CTkLabel(
            input_frame,
            text="输入岗位描述，AI将自动分析并生成结构化报告",
            font=ctk.CTkFont(size=12),
            text_color=("gray50", "gray60"),
        ).grid(row=1, column=0, padx=10, pady=(0, 10), sticky="w")

        ctk.CTkLabel(input_frame, text="参考公司调研（可选）:").grid(
            row=2, column=0, padx=10, pady=(5, 5), sticky="w"
        )
        self.company_combo = ctk.CTkComboBox(input_frame, values=company_options)
        self.company_combo.grid(row=3, column=0, padx=10, pady=(0, 5), sticky="ew")
        if company_options:
            self.company_combo.set(company_options[0])

        self.jd_textbox = ctk.CTkTextbox(input_frame, wrap="word")
        self.jd_textbox.grid(row=4, column=0, padx=10, pady=5, sticky="nsew")

        btn_frame = ctk.CTkFrame(input_frame, fg_color="transparent")
        btn_frame.grid(row=5, column=0, padx=10, pady=10, sticky="ew")
        btn_frame.grid_columnconfigure(0, weight=1)

        self.clear_input_btn = ctk.CTkButton(
            btn_frame,
            text="清空",
            width=80,
            fg_color="gray",
            command=self._on_clear_input_click,
        )
        self.clear_input_btn.grid(row=0, column=0, padx=5, sticky="w")

        self.analyze_btn = ctk.CTkButton(
            btn_frame,
            text="开始分析",
            width=150,
            command=self._on_analyze_click,
        )
        self.analyze_btn.grid(row=0, column=1, padx=5, sticky="e")

    def _build_result_panel(self):
        """构建右侧结果面板。"""
        result_frame = ctk.CTkFrame(self)
        result_frame.grid(row=0, column=1, padx=(5, 10), pady=10, sticky="nsew")
        result_frame.grid_columnconfigure(0, weight=1)
        result_frame.grid_rowconfigure(1, weight=1)

        header_frame = ctk.CTkFrame(result_frame, fg_color="transparent")
        header_frame.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="ew")
        header_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header_frame,
            text="分析结果",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(side="left")

        btn_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        btn_frame.pack(side="right")

        self.history_btn = ctk.CTkButton(
            btn_frame,
            text="历史",
            width=60,
            height=28,
            command=self._on_history_click,
        )
        self.history_btn.pack(side="right", padx=5)

        self.copy_all_btn = ctk.CTkButton(
            btn_frame,
            text="复制全部",
            width=80,
            height=28,
            command=self._on_copy_all_click,
        )
        self.copy_all_btn.pack(side="right", padx=5)

        self.clear_result_btn = ctk.CTkButton(
            btn_frame,
            text="清空",
            width=60,
            height=28,
            fg_color="gray",
            command=self._on_clear_result_click,
        )
        self.clear_result_btn.pack(side="right", padx=5)

        self.html_renderer = HtmlRenderer(result_frame, theme=self.theme)
        self.html_renderer.grid(row=1, column=0, padx=10, pady=(5, 10), sticky="nsew")
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

    def _show_history(self):
        """显示历史面板。"""
        self.html_renderer.grid_forget()

        if self.history_panel is None:
            self.history_panel = HistoryPanel(
                self._result_parent,
                history_manager=self.history_manager,
                on_load_record=self._on_load_history,
            )
        else:
            self.history_panel.refresh()

        self.history_panel.grid(row=1, column=0, padx=10, pady=(5, 10), sticky="nsew")
        self._showing_history = True
        self.history_btn.configure(text="返回")

    def _hide_history(self):
        """隐藏历史面板。"""
        if self.history_panel:
            self.history_panel.grid_forget()
        self.html_renderer.grid(row=1, column=0, padx=10, pady=(5, 10), sticky="nsew")
        self._showing_history = False
        self.history_btn.configure(text="历史")

    def _on_load_history(self, record):
        """加载历史记录。"""
        self._hide_history()
        self.set_jd_text(record.jd_text)
        self.set_result(record.result)

    def get_jd_text(self) -> str:
        """获取 JD 输入内容。"""
        return self.jd_textbox.get("1.0", "end").strip()

    def set_jd_text(self, text: str):
        """设置 JD 输入内容。"""
        self.jd_textbox.delete("1.0", "end")
        self.jd_textbox.insert("1.0", text)

    def get_selected_company(self) -> str:
        """获取选中的公司调研项。"""
        return self.company_combo.get().strip()

    def update_company_options(self, values: List[str]):
        """更新公司调研选项。"""
        self.company_combo.configure(values=values)
        if values:
            self.company_combo.set(values[0])

    def show_loading(self):
        """显示加载状态。"""
        if self._showing_history:
            self._hide_history()
        self._result_buffer = ""
        self.html_renderer.show_loading("job_analysis")

    def clear_result(self):
        """清空结果。"""
        if self._showing_history:
            self._hide_history()
        self._result_buffer = ""
        self.html_renderer.clear()

    def set_result(self, text: str):
        """设置结果内容。"""
        if self._showing_history:
            self._hide_history()
        self._result_buffer = text
        self.html_renderer.set_content(text)

    def get_result(self) -> str:
        """获取结果内容。"""
        return self._result_buffer

    def set_analyzing(self, analyzing: bool):
        """设置分析状态。"""
        if analyzing:
            self.analyze_btn.configure(state="disabled", text="AI 正在思考中...")
            self.clear_input_btn.configure(state="disabled")
            self.copy_all_btn.configure(state="disabled")
            self.clear_result_btn.configure(state="disabled")
            self.history_btn.configure(state="disabled")
            self.company_combo.configure(state="disabled")
            self.jd_textbox.configure(state="disabled")
        else:
            self.analyze_btn.configure(state="normal", text="开始分析")
            self.clear_input_btn.configure(state="normal")
            self.copy_all_btn.configure(state="normal")
            self.clear_result_btn.configure(state="normal")
            self.history_btn.configure(state="normal")
            self.company_combo.configure(state="normal")
            self.jd_textbox.configure(state="normal")

    def set_theme(self, theme: str):
        """设置主题。"""
        self.theme = theme
        self.html_renderer.set_theme(theme)
