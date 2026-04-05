"""公司深度调研UI组件模块"""

import customtkinter as ctk
from tkinter import messagebox
from typing import Callable, Optional

from .history_widget import HistoryPanel
from .html_renderer import HtmlRenderer
from ..core.history import HistoryManager
from ..utils.helpers import copy_to_clipboard


class CompanyResearchWidget(ctk.CTkFrame):
    """公司深度调研界面组件"""

    def __init__(
        self,
        master,
        on_research: Callable,
        history_manager: HistoryManager,
        theme: str = "light",
        **kwargs,
    ):
        """初始化组件"""
        super().__init__(master, **kwargs)
        self.on_research = on_research
        self.history_manager = history_manager
        self.theme = theme
        self._setup_ui()

    def _setup_ui(self):
        """设置UI布局"""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_input_bar()
        self._build_result_panel()

    def _build_input_bar(self):
        """构建顶部输入栏"""
        input_bar = ctk.CTkFrame(self, fg_color="transparent")
        input_bar.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="ew")
        input_bar.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(input_bar, text="公司名称:", font=ctk.CTkFont(size=13)).grid(
            row=0, column=0, padx=(0, 8)
        )

        self.company_entry = ctk.CTkEntry(
            input_bar, placeholder_text="请输入公司名称，如：华为、字节跳动、Tesla"
        )
        self.company_entry.grid(row=0, column=1, sticky="ew")

        self.research_btn = ctk.CTkButton(
            input_bar, text="开始调研", width=100, command=self._on_research_click
        )
        self.research_btn.grid(row=0, column=2, padx=(8, 0))

        self.copy_btn = ctk.CTkButton(
            input_bar,
            text="复制",
            width=60,
            fg_color="gray",
            command=self._on_copy_click,
        )
        self.copy_btn.grid(row=0, column=3, padx=(8, 0))

        self.clear_btn = ctk.CTkButton(
            input_bar,
            text="清空",
            width=60,
            fg_color="gray",
            command=self._on_clear_click,
        )
        self.clear_btn.grid(row=0, column=4, padx=(8, 0))

        self.history_btn = ctk.CTkButton(
            input_bar,
            text="历史",
            width=60,
            fg_color="gray",
            command=self._on_history_click,
        )
        self.history_btn.grid(row=0, column=5, padx=(8, 0))

    def _build_result_panel(self):
        """构建结果展示面板 - 使用HTML渲染器"""
        self.html_renderer = HtmlRenderer(self, theme=self.theme)
        self.html_renderer.grid(row=1, column=0, padx=10, pady=(5, 10), sticky="nsew")

        self.history_panel = None
        self._showing_history = False
        self._result_buffer = ""

    def _on_history_click(self):
        """历史按钮点击事件"""
        if self._showing_history:
            self._hide_history()
        else:
            self._show_history()

    def _show_history(self):
        """显示历史面板"""
        self.html_renderer.grid_forget()

        if self.history_panel is None:
            self.history_panel = HistoryPanel(
                self,
                history_manager=self.history_manager,
                on_load_record=self._on_load_history,
            )
        else:
            self.history_panel.refresh()

        self.history_panel.grid(row=1, column=0, padx=10, pady=(5, 10), sticky="nsew")
        self._showing_history = True
        self.history_btn.configure(text="返回")

    def _hide_history(self):
        """隐藏历史面板"""
        if self.history_panel:
            self.history_panel.grid_forget()

        self.html_renderer.grid(row=1, column=0, padx=10, pady=(5, 10), sticky="nsew")
        self._showing_history = False
        self.history_btn.configure(text="历史")

    def _on_load_history(self, record):
        """加载历史记录"""
        self._hide_history()
        self._result_buffer = record.result
        self.html_renderer.set_content(record.result)

    def _on_research_click(self):
        """调研按钮点击事件"""
        company_name = self.company_entry.get().strip()

        if not company_name:
            messagebox.showwarning("提示", "请输入公司名称")
            return

        if self._showing_history:
            self._hide_history()

        self.set_researching(True)
        self._result_buffer = ""
        self.html_renderer.start_stream()
        self.on_research(company_name)

    def _on_clear_click(self):
        """清空按钮点击事件"""
        self._result_buffer = ""
        self.html_renderer.clear()

    def _on_copy_click(self):
        """复制按钮点击事件"""
        content = self._result_buffer
        if not content:
            messagebox.showinfo("提示", "没有可复制的内容")
            return

        if copy_to_clipboard(content):
            messagebox.showinfo("成功", "已复制到剪贴板")
        else:
            messagebox.showerror("错误", "复制失败")

    def set_researching(self, researching: bool):
        """设置调研状态"""
        if researching:
            self.research_btn.configure(state="disabled", text="调研中...")
            self.company_entry.configure(state="disabled")
        else:
            self.research_btn.configure(state="normal", text="开始调研")
            self.company_entry.configure(state="normal")

    def append_result(self, text: str):
        """追加结果文本"""
        self._result_buffer += text
        self.html_renderer.append_chunk(text)

    def finish_stream(self):
        """完成流式输出"""
        self.html_renderer.finish_stream()

    def get_result(self) -> str:
        """获取完整结果"""
        return self._result_buffer

    def refresh_history(self):
        """刷新历史记录"""
        if self.history_panel:
            self.history_panel.refresh()

    def set_theme(self, theme: str):
        """设置主题"""
        self.theme = theme
        self.html_renderer.set_theme(theme)
