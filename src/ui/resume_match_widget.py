"""简历匹配组件"""
import customtkinter as ctk
from typing import Callable, Optional, Dict


class ResumeMatchWidget(ctk.CTkFrame):
    """简历匹配界面组件"""

    def __init__(self, master, on_match: Callable, job_list: list, **kwargs):
        super().__init__(master, **kwargs)
        self.on_match = on_match
        self.job_list = job_list
        self.job_data_map: Dict[str, str] = {}  # 标题 -> 完整JD文本的映射

        self._setup_ui()

    def _setup_ui(self):
        """设置UI布局"""
        # 岗位选择区域
        job_frame = ctk.CTkFrame(self)
        job_frame.pack(fill="x", padx=10, pady=(10, 5))

        ctk.CTkLabel(job_frame, text="选择岗位:", font=("", 14)).pack(side="left", padx=5)
        self.job_combo = ctk.CTkComboBox(job_frame, values=self.job_list, width=300)
        self.job_combo.pack(side="left", padx=5)

        # 简历输入区域
        resume_label = ctk.CTkLabel(self, text="候选人简历:", font=("", 14))
        resume_label.pack(anchor="w", padx=10, pady=(10, 5))

        self.resume_text = ctk.CTkTextbox(self, height=250)
        self.resume_text.pack(fill="both", expand=True, padx=10, pady=5)

        # 匹配按钮
        self.match_btn = ctk.CTkButton(
            self, text="开始匹配分析", command=self._on_match_click, height=35
        )
        self.match_btn.pack(pady=10)

        # 结果展示区域
        result_label = ctk.CTkLabel(self, text="匹配结果:", font=("", 14))
        result_label.pack(anchor="w", padx=10, pady=(10, 5))

        self.result_text = ctk.CTkTextbox(self, height=300)
        self.result_text.pack(fill="both", expand=True, padx=10, pady=(5, 10))

    def _on_match_click(self):
        """匹配按钮点击事件"""
        job_title = self.job_combo.get()
        resume = self.resume_text.get("1.0", "end-1c").strip()

        if not job_title or job_title == "请先分析岗位":
            self.result_text.delete("1.0", "end")
            self.result_text.insert("1.0", "请先选择一个岗位")
            return

        if not resume:
            self.result_text.delete("1.0", "end")
            self.result_text.insert("1.0", "请输入候选人简历")
            return

        # 从映射中获取完整的JD文本
        job_desc = self.job_data_map.get(job_title, "")
        if not job_desc:
            self.result_text.delete("1.0", "end")
            self.result_text.insert("1.0", "无法获取岗位信息")
            return

        self.match_btn.configure(state="disabled", text="分析中...")
        self.result_text.delete("1.0", "end")
        self.on_match(job_desc, resume)

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

    def enable_match_button(self):
        """启用匹配按钮"""
        self.match_btn.configure(state="normal", text="开始匹配分析")

