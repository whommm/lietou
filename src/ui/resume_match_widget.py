"""简历匹配组件"""
import customtkinter as ctk
from tkinter import messagebox
from typing import Callable, Dict


class ResumeMatchWidget(ctk.CTkFrame):
    """简历匹配界面组件"""

    def __init__(self, master, on_match: Callable, job_list: list, **kwargs):
        super().__init__(master, **kwargs)
        self.on_match = on_match
        self.job_list = job_list
        self.job_data_map: Dict[str, str] = {}

        self._setup_ui()

    def _setup_ui(self):
        """设置UI布局 - 左右分栏"""
        self.grid_columnconfigure(0, weight=2)
        self.grid_columnconfigure(1, weight=3)
        self.grid_rowconfigure(0, weight=1)

        self._build_input_panel()
        self._build_result_panel()

    def _build_input_panel(self):
        """构建左侧输入面板"""
        input_frame = ctk.CTkFrame(self)
        input_frame.grid(row=0, column=0, padx=(10, 5), pady=10, sticky="nsew")
        input_frame.grid_columnconfigure(0, weight=1)
        input_frame.grid_rowconfigure(3, weight=1)

        # 标题
        title_label = ctk.CTkLabel(
            input_frame,
            text="📋 简历匹配分析",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title_label.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="w")

        # 描述
        desc_label = ctk.CTkLabel(
            input_frame,
            text="选择已分析的岗位，输入候选人简历进行匹配分析",
            font=ctk.CTkFont(size=12),
            text_color=("gray50", "gray60")
        )
        desc_label.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="w")

        # 岗位选择
        ctk.CTkLabel(input_frame, text="选择岗位:").grid(
            row=2, column=0, padx=10, pady=(10, 5), sticky="w"
        )
        self.job_combo = ctk.CTkComboBox(input_frame, values=self.job_list)
        self.job_combo.grid(row=3, column=0, padx=10, pady=(0, 10), sticky="ew")

        # 简历输入
        ctk.CTkLabel(input_frame, text="候选人简历:").grid(
            row=4, column=0, padx=10, pady=(10, 5), sticky="w"
        )
        self.resume_text = ctk.CTkTextbox(input_frame, wrap="word")
        self.resume_text.grid(row=5, column=0, padx=10, pady=(0, 10), sticky="nsew")
        input_frame.grid_rowconfigure(5, weight=1)

        # 按钮区
        btn_frame = ctk.CTkFrame(input_frame, fg_color="transparent")
        btn_frame.grid(row=6, column=0, padx=10, pady=(0, 10), sticky="ew")
        btn_frame.grid_columnconfigure(0, weight=1)

        self.clear_btn = ctk.CTkButton(
            btn_frame, text="清空", width=60, fg_color="gray",
            command=self._on_clear_click
        )
        self.clear_btn.grid(row=0, column=0, padx=5, sticky="w")

        self.match_btn = ctk.CTkButton(
            btn_frame, text="开始匹配分析",
            command=self._on_match_click
        )
        self.match_btn.grid(row=0, column=1, padx=5, sticky="e")

    def _build_result_panel(self):
        """构建右侧结果面板"""
        result_frame = ctk.CTkFrame(self)
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
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(side="left")

        self.copy_all_btn = ctk.CTkButton(
            header_frame, text="复制全部", width=80, height=28,
            command=self._on_copy_all_click
        )
        self.copy_all_btn.pack(side="right", padx=5)

        self.clear_result_btn = ctk.CTkButton(
            header_frame, text="清空", width=60, height=28,
            fg_color="gray", command=self._on_clear_result_click
        )
        self.clear_result_btn.pack(side="right", padx=5)

        # 结果文本框
        self.result_text = ctk.CTkTextbox(
            result_frame, wrap="word", font=ctk.CTkFont(size=13)
        )
        self.result_text.grid(row=1, column=0, padx=10, pady=(5, 10), sticky="nsew")

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
        self.result_text.delete("1.0", "end")
        self.on_match(job_desc, resume)

    def _on_clear_click(self):
        """清空输入"""
        self.resume_text.delete("1.0", "end")

    def _on_clear_result_click(self):
        """清空结果"""
        self.result_text.delete("1.0", "end")

    def _on_copy_all_click(self):
        """复制全部"""
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

    def set_matching(self, matching: bool):
        """设置匹配状态"""
        if matching:
            self.match_btn.configure(state="disabled", text="分析中...")
            self.clear_btn.configure(state="disabled")
            self.job_combo.configure(state="disabled")
            self.resume_text.configure(state="disabled")
        else:
            self.match_btn.configure(state="normal", text="开始匹配分析")
            self.clear_btn.configure(state="normal")
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

    def append_result(self, text: str):
        """追加结果文本"""
        self.result_text.insert("end", text)
        self.result_text.see("end")

    def enable_match_button(self):
        """启用匹配按钮"""
        self.set_matching(False)
