"""Greeting text generator widget."""

import customtkinter as ctk
from tkinter import messagebox
from typing import Callable, Dict, List, Optional


class GreetingGeneratorWidget(ctk.CTkFrame):
    """Widget for generating猎头 greeting messages using LLM."""

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
        on_generate: Callable,
        on_generate_batch: Optional[Callable] = None,
        on_copy: Optional[Callable] = None,
        on_use_for_auto: Optional[Callable[[str], None]] = None,
        on_pick_job_history: Optional[Callable] = None,
        theme: str = "light",
        **kwargs,
    ):
        super().__init__(master, **kwargs)
        self.on_generate = on_generate
        self.on_generate_batch = on_generate_batch
        self.on_copy = on_copy
        self.on_use_for_auto = on_use_for_auto
        self.on_pick_job_history = on_pick_job_history
        self.theme = theme
        self.job_options: List[str] = ["请先分析岗位"]
        self.job_data_map: Dict[str, Dict[str, object]] = {}

        self._setup_ui()

    def _setup_ui(self):
        self.configure(fg_color="transparent")
        self.grid_columnconfigure(0, weight=2)
        self.grid_columnconfigure(1, weight=3)
        self.grid_rowconfigure(0, weight=1)

        self._build_control_panel()
        self._build_result_panel()

    def _build_control_panel(self):
        colors = self.PALETTE
        frame = ctk.CTkFrame(
            self,
            corner_radius=24,
            fg_color=colors["panel"],
            border_width=1,
            border_color=colors["border"],
        )
        frame.grid(row=0, column=0, padx=(10, 5), pady=10, sticky="nsew")
        frame.grid_columnconfigure(0, weight=1)

        # Title
        ctk.CTkLabel(
            frame,
            text="打招呼生成器",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=colors["text"],
        ).grid(row=0, column=0, padx=16, pady=(16, 4), sticky="w")
        
        ctk.CTkLabel(
            frame,
            text="基于岗位信息，自动生成标准化的猎头打招呼消息。",
            font=ctk.CTkFont(size=12),
            text_color=colors["muted"],
            justify="left",
            wraplength=280,
        ).grid(row=1, column=0, padx=16, pady=(0, 12), sticky="w")

        # Job selection
        ctk.CTkLabel(frame, text="目标岗位", text_color=colors["text"]).grid(
            row=2, column=0, padx=16, pady=(8, 6), sticky="w"
        )
        job_row = ctk.CTkFrame(frame, fg_color="transparent")
        job_row.grid(row=3, column=0, padx=16, pady=(0, 10), sticky="ew")
        job_row.grid_columnconfigure(0, weight=1)

        self.job_display = ctk.CTkEntry(
            job_row,
            state="readonly",
            corner_radius=16,
            height=38,
            fg_color=colors["panel_alt"],
            border_color=colors["border"],
            text_color=colors["text"],
        )
        self.job_display.grid(row=0, column=0, sticky="ew")

        self.pick_job_btn = ctk.CTkButton(
            job_row,
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

        # Job info preview
        self.job_info_card = ctk.CTkFrame(
            frame,
            corner_radius=14,
            fg_color=colors["panel_alt"],
            border_width=1,
            border_color=colors["border"],
        )
        self.job_info_card.grid(row=4, column=0, padx=16, pady=(0, 10), sticky="ew")

        self.job_title_label = ctk.CTkLabel(
            self.job_info_card,
            text="职位：未选择",
            font=ctk.CTkFont(size=12),
            text_color=colors["text"],
        )
        self.job_title_label.pack(anchor="w", padx=12, pady=(10, 4))

        self.job_city_label = ctk.CTkLabel(
            self.job_info_card,
            text="城市：-",
            font=ctk.CTkFont(size=12),
            text_color=colors["muted"],
        )
        self.job_city_label.pack(anchor="w", padx=12, pady=(0, 4))

        self.job_salary_label = ctk.CTkLabel(
            self.job_info_card,
            text="薪资：-",
            font=ctk.CTkFont(size=12),
            text_color=colors["muted"],
        )
        self.job_salary_label.pack(anchor="w", padx=12, pady=(0, 10))

        # Generate buttons
        btn_row = ctk.CTkFrame(frame, fg_color="transparent")
        btn_row.grid(row=5, column=0, padx=16, pady=(0, 10), sticky="ew")
        btn_row.grid_columnconfigure((0, 1), weight=1)

        self.generate_btn = ctk.CTkButton(
            btn_row,
            text="生成打招呼文本",
            height=42,
            corner_radius=20,
            fg_color=colors["accent"],
            hover_color=colors["accent_hover"],
            text_color="#f8fbff",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._on_generate_click,
        )
        self.generate_btn.grid(row=0, column=0, padx=(0, 5), sticky="ew")

        self.generate_batch_btn = ctk.CTkButton(
            btn_row,
            text="批量生成5个",
            height=42,
            corner_radius=20,
            fg_color=colors["secondary"],
            hover_color=colors["secondary_hover"],
            text_color=colors["text"],
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._on_generate_batch_click,
        )
        self.generate_batch_btn.grid(row=0, column=1, padx=(5, 0), sticky="ew")

        # Batch variant selection
        self.variant_frame = ctk.CTkFrame(frame, fg_color="transparent")
        self.variant_frame.grid(row=6, column=0, padx=16, pady=(0, 10), sticky="ew")
        self.variant_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(
            self.variant_frame,
            text="选择版本：",
            font=ctk.CTkFont(size=11),
            text_color=colors["muted"],
        ).grid(row=0, column=0, sticky="w")

        self.variant_buttons: List[ctk.CTkButton] = []
        self.variant_texts: List[str] = []
        self.selected_variant_index: int = -1

        # Status
        self.status_label = ctk.CTkLabel(
            frame,
            text="请选择岗位后生成打招呼文本",
            text_color=colors["muted"],
            font=ctk.CTkFont(size=12),
            justify="left",
            wraplength=280,
        )
        self.status_label.grid(row=7, column=0, padx=16, pady=(0, 16), sticky="w")

    def _build_result_panel(self):
        colors = self.PALETTE
        frame = ctk.CTkFrame(
            self,
            corner_radius=24,
            fg_color=colors["panel"],
            border_width=1,
            border_color=colors["border"],
        )
        frame.grid(row=0, column=1, padx=(5, 10), pady=10, sticky="nsew")
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(2, weight=1)

        # Title
        ctk.CTkLabel(
            frame,
            text="生成结果",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=colors["text"],
        ).grid(row=0, column=0, padx=16, pady=(16, 4), sticky="w")
        
        ctk.CTkLabel(
            frame,
            text="生成的打招呼文本将显示在这里，可直接复制使用。",
            font=ctk.CTkFont(size=12),
            text_color=colors["muted"],
            justify="left",
            wraplength=420,
        ).grid(row=1, column=0, padx=16, pady=(0, 12), sticky="w")

        # Result text box
        self.result_box = ctk.CTkTextbox(
            frame,
            wrap="word",
            corner_radius=18,
            border_width=1,
            border_color=colors["border"],
            fg_color=colors["panel_alt"],
            text_color=colors["text"],
            font=ctk.CTkFont(size=13),
            height=300,
        )
        self.result_box.grid(row=2, column=0, padx=16, pady=(0, 10), sticky="nsew")
        self.result_box.insert(
            "1.0",
            "等待生成...\n\n"
            "点击左侧\"生成打招呼文本\"按钮，\n"
            "系统将基于岗位信息自动生成标准化的打招呼消息。",
        )

        # Copy button
        self.copy_btn = ctk.CTkButton(
            frame,
            text="一键复制",
            height=42,
            corner_radius=20,
            fg_color=colors["accent"],
            hover_color=colors["accent_hover"],
            text_color="#f8fbff",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._on_copy_click,
        )
        self.copy_btn.grid(row=3, column=0, padx=16, pady=(0, 10), sticky="ew")

        # Action buttons
        action_row = ctk.CTkFrame(frame, fg_color="transparent")
        action_row.grid(row=4, column=0, padx=16, pady=(0, 16), sticky="ew")
        action_row.grid_columnconfigure((0, 1), weight=1)

        self.use_for_auto_btn = ctk.CTkButton(
            action_row,
            text="设为自动打招呼模板",
            height=36,
            corner_radius=18,
            fg_color=colors["secondary"],
            hover_color=colors["secondary_hover"],
            text_color=colors["text"],
            command=self._on_use_for_auto,
        )
        self.use_for_auto_btn.grid(row=0, column=0, padx=(0, 5), sticky="ew")

        self.clear_btn = ctk.CTkButton(
            action_row,
            text="清空",
            height=36,
            corner_radius=18,
            fg_color=colors["secondary"],
            hover_color=colors["secondary_hover"],
            text_color=colors["text"],
            command=self._on_clear_click,
        )
        self.clear_btn.grid(row=0, column=1, padx=(5, 0), sticky="ew")

    def _on_pick_job_click(self):
        if self.on_pick_job_history:
            self.on_pick_job_history()

    def _on_generate_click(self):
        job_label = self.job_display.get().strip()
        payload = self.job_data_map.get(job_label)
        if not payload:
            messagebox.showwarning("提示", "请先选择目标岗位")
            return
        self._set_result_text("正在生成打招呼文本，请稍候...")
        self.on_generate(job_label, payload)

    def _on_generate_batch_click(self):
        job_label = self.job_display.get().strip()
        payload = self.job_data_map.get(job_label)
        if not payload:
            messagebox.showwarning("提示", "请先选择目标岗位")
            return
        self._set_result_text("正在批量生成5个版本，请稍候...")
        if self.on_generate_batch:
            self.on_generate_batch(job_label, payload)

    def _on_copy_click(self):
        text = self.result_box.get("1.0", "end").strip()
        if text and text != "等待生成...":
            try:
                import pyperclip
                pyperclip.copy(text)
                messagebox.showinfo("成功", "已复制到剪贴板")
            except ImportError:
                messagebox.showwarning("提示", "请安装 pyperclip 库以支持复制功能")
        else:
            messagebox.showwarning("提示", "没有可复制的内容")

    def _on_use_for_auto(self):
        text = self.result_box.get("1.0", "end").strip()
        if text and text != "等待生成...":
            if self.on_use_for_auto:
                self.on_use_for_auto(text)
            else:
                messagebox.showinfo(
                    "设置成功",
                    "已将当前文本设为自动打招呼默认模板。"
                )
        else:
            messagebox.showwarning("提示", "请先生成打招呼文本")

    def _on_clear_click(self):
        self.result_box.delete("1.0", "end")
        self.result_box.insert("1.0", "等待生成...")
        self.status_label.configure(text="已清空，请重新生成")
        self.variant_buttons.clear()
        self.variant_texts.clear()
        self.selected_variant_index = -1

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
        payload = self.job_data_map.get(job_label, {})
        if payload:
            self.set_job_info(
                payload.get("job_title", "") or payload.get("title", ""),
                payload.get("city", ""),
                payload.get("salary_range", ""),
            )

    def set_job_info(self, job_title: str, city: str, salary: str):
        self.job_title_label.configure(text=f"职位：{job_title or '未选择'}")
        self.job_city_label.configure(text=f"城市：{city or '-'}")
        self.job_salary_label.configure(text=f"薪资：{salary or '-'}")

    def set_result_text(self, text: str):
        self._set_result_text(text)

    def set_batch_results(self, texts: List[str]):
        """Display batch generation results with variant selection."""
        self.variant_texts = texts
        self.variant_buttons.clear()
        
        # Clear existing variant buttons
        for widget in self.variant_frame.winfo_children():
            widget.destroy()
        
        if not texts:
            return
        
        ctk.CTkLabel(
            self.variant_frame,
            text="选择版本：",
            font=ctk.CTkFont(size=11),
            text_color=self.PALETTE["muted"],
        ).grid(row=0, column=0, sticky="w")
        
        for i, text in enumerate(texts[:5]):
            btn = ctk.CTkButton(
                self.variant_frame,
                text=f"版本 {i+1}",
                width=60,
                height=28,
                corner_radius=14,
                fg_color=self.PALETTE["secondary"],
                hover_color=self.PALETTE["secondary_hover"],
                text_color=self.PALETTE["text"],
                font=ctk.CTkFont(size=10),
                command=lambda idx=i: self._on_variant_select(idx),
            )
            btn.grid(row=1, column=i, padx=(0, 4), pady=(4, 0))
            self.variant_buttons.append(btn)
        
        # Show first variant by default
        if texts:
            self._on_variant_select(0)

    def _on_variant_select(self, index: int):
        if 0 <= index < len(self.variant_texts):
            self.selected_variant_index = index
            self._set_result_text(self.variant_texts[index])
            
            # Update button colors
            for i, btn in enumerate(self.variant_buttons):
                if i == index:
                    btn.configure(
                        fg_color=self.PALETTE["accent"],
                        text_color="#f8fbff",
                    )
                else:
                    btn.configure(
                        fg_color=self.PALETTE["secondary"],
                        text_color=self.PALETTE["text"],
                    )

    def set_generating(self, generating: bool):
        state = "disabled" if generating else "normal"
        self.generate_btn.configure(state=state)
        self.generate_batch_btn.configure(state=state)
        if generating:
            self.status_label.configure(text="正在生成中...")
        else:
            self.status_label.configure(text="生成完成")

    def get_result_text(self) -> str:
        return self.result_box.get("1.0", "end").strip()

    def _set_result_text(self, text: str):
        self.result_box.delete("1.0", "end")
        self.result_box.insert("1.0", text)
