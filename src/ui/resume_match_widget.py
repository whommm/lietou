"""简历匹配组件"""

import customtkinter as ctk
from tkinter import messagebox
from typing import Callable, Dict, Optional

from .html_renderer import HtmlRenderer
from ..utils.helpers import copy_to_clipboard


class ResumeMatchWidget(ctk.CTkFrame):
    """简历匹配界面组件"""

    PALETTE = {
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
    }

    def __init__(
        self,
        master,
        on_match: Callable,
        job_list: list,
        on_pick_history: Optional[Callable] = None,
        theme: str = "light",
        **kwargs,
    ):
        super().__init__(master, **kwargs)
        self.on_match = on_match
        self.on_pick_history = on_pick_history
        self.job_list = job_list
        self.job_data_map: Dict[str, str] = {}
        self.theme = theme

        self._setup_ui()

    def _setup_ui(self):
        """设置UI布局 - 左右分栏"""
        self.configure(fg_color="transparent")
        self.grid_columnconfigure(0, weight=2)
        self.grid_columnconfigure(1, weight=3)
        self.grid_rowconfigure(0, weight=1)

        self._build_input_panel()
        self._build_result_panel()

    def _build_input_panel(self):
        """构建左侧输入面板"""
        colors = self.PALETTE[self.theme]
        input_frame = ctk.CTkFrame(
            self,
            corner_radius=24,
            fg_color=colors["panel"],
            border_width=1,
            border_color=colors["border"],
        )
        input_frame.grid(row=0, column=0, padx=(10, 5), pady=10, sticky="nsew")
        input_frame.grid_columnconfigure(0, weight=1)
        input_frame.grid_rowconfigure(5, weight=1)

        # 标题
        title_label = ctk.CTkLabel(
            input_frame,
            text="简历匹配分析",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=colors["text"],
        )
        title_label.grid(row=0, column=0, padx=16, pady=(16, 5), sticky="w")

        # 描述
        desc_label = ctk.CTkLabel(
            input_frame,
            text="选择岗位后输入候选人简历，系统会产出推进结论与验证问题。",
            font=ctk.CTkFont(size=12),
            text_color=colors["muted"],
        )
        desc_label.grid(row=1, column=0, padx=16, pady=(0, 12), sticky="w")

        # 岗位选择
        ctk.CTkLabel(input_frame, text="选择岗位:", text_color=colors["text"]).grid(
            row=2, column=0, padx=16, pady=(10, 6), sticky="w"
        )
        picker_row = ctk.CTkFrame(input_frame, fg_color="transparent")
        picker_row.grid(row=3, column=0, padx=16, pady=(0, 10), sticky="ew")
        picker_row.grid_columnconfigure(0, weight=1)

        self.job_combo = ctk.CTkComboBox(
            picker_row,
            values=self.job_list,
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

        self.job_picker_btn = ctk.CTkButton(
            picker_row,
            text="从历史选择",
            width=112,
            height=38,
            corner_radius=18,
            fg_color=colors["secondary"],
            hover_color=colors["secondary_hover"],
            text_color=colors["text"],
            command=self._on_open_job_picker,
        )
        self.job_picker_btn.grid(row=0, column=1, padx=(10, 0), sticky="e")

        # 简历输入
        ctk.CTkLabel(input_frame, text="候选人简历:", text_color=colors["text"]).grid(
            row=4, column=0, padx=16, pady=(10, 6), sticky="w"
        )
        self.resume_text = ctk.CTkTextbox(
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
        self.resume_text.grid(row=5, column=0, padx=16, pady=(0, 10), sticky="nsew")

        # 按钮区
        btn_frame = ctk.CTkFrame(input_frame, fg_color="transparent")
        btn_frame.grid(row=6, column=0, padx=16, pady=(0, 16), sticky="ew")
        btn_frame.grid_columnconfigure(0, weight=1)

        self.clear_btn = ctk.CTkButton(
            btn_frame,
            text="清空",
            width=60,
            height=38,
            corner_radius=18,
            fg_color=colors["secondary"],
            hover_color=colors["secondary_hover"],
            text_color=colors["text"],
            command=self._on_clear_click,
        )
        self.clear_btn.grid(row=0, column=0, padx=5, sticky="w")

        self.match_btn = ctk.CTkButton(
            btn_frame,
            text="开始匹配分析",
            height=40,
            corner_radius=20,
            fg_color=colors["accent"],
            hover_color=colors["accent_hover"],
            text_color="#f8fbff",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._on_match_click,
        )
        self.match_btn.grid(row=0, column=1, padx=5, sticky="e")

    def _build_result_panel(self):
        """构建右侧结果面板"""
        colors = self.PALETTE[self.theme]
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

        # 标题栏
        header_frame = ctk.CTkFrame(result_frame, fg_color="transparent")
        header_frame.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="ew")
        header_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header_frame,
            text="匹配结果",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=colors["text"],
        ).pack(side="left")

        # 按钮区
        btn_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        btn_frame.pack(side="right")

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

        # HTML渲染器
        self.html_renderer = HtmlRenderer(result_frame, theme=self.theme)
        self.html_renderer.grid(row=1, column=0, padx=10, pady=(5, 10), sticky="nsew")

        # 结果缓冲区
        self._result_buffer = ""

    def _on_match_click(self):
        """匹配按钮点击事件"""
        job_title = self.job_combo.get()
        resume = self.resume_text.get("1.0", "end-1c").strip()

        if not job_title or job_title == "请先分析岗位":
            messagebox.showwarning("提示", "请先选择一个岗位")
            return

        if not resume:
            messagebox.showwarning("提示", "请输入候选人简历")
            return

        job_desc = self.job_data_map.get(job_title, "")
        if not job_desc:
            messagebox.showwarning("提示", "无法获取岗位信息")
            return

        self.set_matching(True)
        self.show_loading()
        self.on_match(job_desc, resume)

    def _on_open_job_picker(self):
        """打开岗位历史选择器。"""
        if self.on_pick_history:
            self.on_pick_history()

    def _on_clear_click(self):
        """清空输入"""
        self.resume_text.delete("1.0", "end")

    def _on_clear_result_click(self):
        """清空结果"""
        self.clear_result()

    def _on_copy_all_click(self):
        """复制全部"""
        content = self._result_buffer
        if not content:
            messagebox.showinfo("提示", "没有可复制的内容")
            return

        if copy_to_clipboard(content):
            messagebox.showinfo("成功", "已复制到剪贴板")
        else:
            messagebox.showerror("错误", "复制失败")

    def set_matching(self, matching: bool):
        """设置匹配状态"""
        if matching:
            self.match_btn.configure(state="disabled", text="分析中...")
            self.clear_btn.configure(state="disabled")
            self.job_picker_btn.configure(state="disabled")
            self.copy_all_btn.configure(state="disabled")
            self.clear_result_btn.configure(state="disabled")
            self.job_combo.configure(state="disabled")
            self.resume_text.configure(state="disabled")
        else:
            self.match_btn.configure(state="normal", text="开始匹配分析")
            self.clear_btn.configure(state="normal")
            self.job_picker_btn.configure(state="normal")
            self.copy_all_btn.configure(state="normal")
            self.clear_result_btn.configure(state="normal")
            self.job_combo.configure(state="normal")
            self.resume_text.configure(state="normal")

    def update_job_list(self, job_list: list, job_data_map: Dict[str, str] = None):
        """更新岗位列表"""
        self.job_list = job_list
        if job_data_map:
            self.job_data_map = job_data_map
        self.job_combo.configure(values=job_list)
        if job_list:
            self.job_combo.set(job_list[0])

    def show_loading(self):
        """显示加载状态。"""
        self._result_buffer = ""
        self.html_renderer.show_loading("resume_match")

    def clear_result(self):
        """清空结果。"""
        self._result_buffer = ""
        self.html_renderer.clear()

    def get_result(self) -> str:
        """获取结果内容。"""
        return self._result_buffer

    def set_result(self, text: str):
        """设置完整结果并渲染"""
        self._result_buffer = text
        self.html_renderer.set_content(text)

    def set_theme(self, theme: str):
        """设置主题"""
        self.theme = theme
        self.html_renderer.set_theme(theme)
