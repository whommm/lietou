"""公司深度调研UI组件模块"""

import customtkinter as ctk
from tkinter import messagebox
from typing import Callable, Optional, List, Dict


class CompanyResearchWidget(ctk.CTkFrame):
    """公司深度调研界面组件"""

    def __init__(self, master, on_research: Callable, **kwargs):
        """初始化组件"""
        super().__init__(master, **kwargs)
        self.on_research = on_research
        self.history_list = []
        self.history_data_map = {}
        self._setup_ui()

    def _setup_ui(self):
        """设置UI布局"""
        self.grid_columnconfigure(0, weight=2)
        self.grid_columnconfigure(1, weight=3)
        self.grid_rowconfigure(0, weight=1)

        self._build_input_panel()
        self._build_result_panel()

    def _build_input_panel(self):
        """构建搜索输入面板"""
        input_frame = ctk.CTkFrame(self)
        input_frame.grid(row=0, column=0, padx=(10, 5), pady=10, sticky="nsew")
        input_frame.grid_columnconfigure(0, weight=1)
        input_frame.grid_rowconfigure(4, weight=1)

        title_label = ctk.CTkLabel(
            input_frame,
            text="🔍 公司深度调研",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title_label.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="w")

        desc_label = ctk.CTkLabel(
            input_frame,
            text="输入公司名称，自动搜索并生成深度调研报告",
            font=ctk.CTkFont(size=12),
            text_color=("gray50", "gray60")
        )
        desc_label.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="w")

        # 历史记录选择
        ctk.CTkLabel(input_frame, text="历史记录:").grid(
            row=2, column=0, padx=10, pady=(10, 5), sticky="w"
        )

        self.history_combo = ctk.CTkComboBox(
            input_frame,
            values=["暂无历史记录"],
            command=self._on_history_select
        )
        self.history_combo.grid(row=3, column=0, padx=10, pady=(0, 10), sticky="ew")

        # 公司名称输入
        ctk.CTkLabel(input_frame, text="公司名称:").grid(
            row=4, column=0, padx=10, pady=(10, 5), sticky="w"
        )

        self.company_entry = ctk.CTkEntry(
            input_frame,
            placeholder_text="请输入公司名称，如：华为、字节跳动、Tesla"
        )
        self.company_entry.grid(row=5, column=0, padx=10, pady=(0, 10), sticky="ew")

        # 按钮区
        btn_frame = ctk.CTkFrame(input_frame, fg_color="transparent")
        btn_frame.grid(row=6, column=0, padx=10, pady=(0, 10), sticky="ew")

        self.research_btn = ctk.CTkButton(
            btn_frame,
            text="开始深度调研",
            command=self._on_research_click
        )
        self.research_btn.pack(side="left", padx=(0, 5))

        self.clear_btn = ctk.CTkButton(
            btn_frame,
            text="清空",
            width=60,
            fg_color="gray",
            command=self._on_clear_click
        )
        self.clear_btn.pack(side="left")

    def _build_result_panel(self):
        """构建结果展示面板"""
        result_frame = ctk.CTkFrame(self)
        result_frame.grid(row=0, column=1, padx=(5, 10), pady=10, sticky="nsew")
        result_frame.grid_columnconfigure(0, weight=1)
        result_frame.grid_rowconfigure(1, weight=1)

        header_frame = ctk.CTkFrame(result_frame, fg_color="transparent")
        header_frame.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="ew")
        header_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header_frame,
            text="调研报告",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(side="left")

        self.copy_btn = ctk.CTkButton(
            header_frame,
            text="复制全部",
            width=80,
            height=28,
            command=self._on_copy_click
        )
        self.copy_btn.pack(side="right", padx=5)

        self.result_text = ctk.CTkTextbox(
            result_frame,
            wrap="word",
            font=ctk.CTkFont(size=13)
        )
        self.result_text.grid(row=1, column=0, padx=10, pady=(5, 10), sticky="nsew")

    def _on_research_click(self):
        """调研按钮点击事件"""
        company_name = self.company_entry.get().strip()

        if not company_name:
            messagebox.showwarning("提示", "请输入公司名称")
            return

        self.set_researching(True)
        self.result_text.delete("1.0", "end")
        self.on_research(company_name)

    def _on_clear_click(self):
        """清空按钮点击事件"""
        self.company_entry.delete(0, "end")
        self.result_text.delete("1.0", "end")

    def _on_copy_click(self):
        """复制按钮点击事件"""
        content = self.result_text.get("1.0", "end").strip()
        if not content:
            messagebox.showinfo("提示", "没有可复制的内容")
            return

        try:
            import pyperclip
            pyperclip.copy(content)
            messagebox.showinfo("成功", "已复制到剪贴板")
        except Exception:
            messagebox.showerror("错误", "复制失败")

    def set_researching(self, researching: bool):
        """设置调研状态"""
        if researching:
            self.research_btn.configure(state="disabled", text="调研中...")
            self.company_entry.configure(state="disabled")
            self.clear_btn.configure(state="disabled")
        else:
            self.research_btn.configure(state="normal", text="开始深度调研")
            self.company_entry.configure(state="normal")
            self.clear_btn.configure(state="normal")

    def append_result(self, text: str):
        """追加结果文本"""
        self.result_text.insert("end", text)
        self.result_text.see("end")

    def get_result(self) -> str:
        """获取完整结果"""
        return self.result_text.get("1.0", "end").strip()

    def _on_history_select(self, choice: str):
        """历史记录选择事件"""
        if choice in self.history_data_map:
            result = self.history_data_map[choice]
            self.result_text.delete("1.0", "end")
            self.result_text.insert("1.0", result)

    def update_history_list(self, history_list: List[str], history_data_map: Dict[str, str]):
        """更新历史记录列表"""
        self.history_list = history_list
        self.history_data_map = history_data_map
        if history_list:
            self.history_combo.configure(values=history_list)
            self.history_combo.set(history_list[0])
        else:
            self.history_combo.configure(values=["暂无历史记录"])
            self.history_combo.set("暂无历史记录")


