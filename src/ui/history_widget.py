"""历史记录UI组件模块"""

import customtkinter as ctk
from tkinter import messagebox
from typing import Callable, Optional, List

from ..core.history import HistoryRecord, HistoryManager


class HistoryItem(ctk.CTkFrame):
    """单条历史记录卡片"""

    CARD_FG = ("#ffffff", "#142640")
    CARD_BORDER = ("#c7d8ff", "#294166")
    TEXT = ("#10233f", "#f5f7ff")
    MUTED = ("#60708c", "#92a3c7")

    def __init__(
        self,
        master,
        record: HistoryRecord,
        on_click: Callable,
        on_delete: Callable,
        **kwargs,
    ):
        super().__init__(
            master,
            corner_radius=18,
            border_width=1,
            border_color=self.CARD_BORDER,
            fg_color=self.CARD_FG,
            cursor="hand2",
            **kwargs,
        )

        self.record = record
        self.on_click = on_click
        self.on_delete = on_delete

        self._build_ui()
        self._bind_events()

    def _build_ui(self):
        """构建UI"""
        # 标题行
        title_frame = ctk.CTkFrame(self, fg_color="transparent")
        title_frame.pack(fill="x", padx=10, pady=(8, 0))

        title_label = ctk.CTkLabel(
            title_frame,
            text=self.record.title,
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w",
            text_color=self.TEXT,
        )
        title_label.pack(side="left", fill="x", expand=True)

        tag_label = ctk.CTkLabel(
            title_frame,
            text=self.record.record_type.replace("_", " "),
            corner_radius=999,
            padx=10,
            pady=4,
            fg_color=("#edf3ff", "#1b3150"),
            text_color=self.MUTED,
            font=ctk.CTkFont(size=10, weight="bold"),
        )
        tag_label.pack(side="right", padx=(0, 8))

        # 删除按钮
        delete_btn = ctk.CTkButton(
            title_frame,
            text="×",
            width=28,
            height=28,
            corner_radius=14,
            fg_color="transparent",
            hover_color=("#ffd9e0", "#4a1c2b"),
            text_color=self.MUTED,
            font=ctk.CTkFont(size=16),
            command=self._on_delete_click,
        )
        delete_btn.pack(side="right")

        # 时间
        time_label = ctk.CTkLabel(
            self,
            text=self.record.created_at,
            font=ctk.CTkFont(size=12),
            text_color=self.MUTED,
            anchor="w",
        )
        time_label.pack(fill="x", padx=10, pady=(2, 8))

        preview_label = ctk.CTkLabel(
            self,
            text=(self.record.jd_text or self.record.result or "").replace("\n", " ")[
                :96
            ],
            text_color=self.MUTED,
            justify="left",
            anchor="w",
            wraplength=420,
            font=ctk.CTkFont(size=12),
        )
        preview_label.pack(fill="x", padx=10, pady=(0, 10))

    def _bind_events(self):
        """绑定点击事件"""

        def handle_click(event):
            # 点击删除按钮时不触发
            try:
                if event.widget.cget("text") == "×":
                    return
            except Exception:
                pass
            self.on_click(self.record)

        self.bind("<Button-1>", handle_click)
        for child in self.winfo_children():
            if isinstance(child, ctk.CTkLabel):
                child.bind("<Button-1>", handle_click)
            for subchild in child.winfo_children():
                if isinstance(subchild, ctk.CTkLabel):
                    subchild.bind("<Button-1>", handle_click)

    def _on_delete_click(self):
        """删除按钮点击"""
        self.on_delete(self.record)


class HistoryPanel(ctk.CTkScrollableFrame):
    """历史记录面板"""

    PAGE_SIZE = 20

    def __init__(
        self,
        master,
        history_manager: HistoryManager,
        on_load_record: Callable,
        on_history_changed: Optional[Callable] = None,
        **kwargs,
    ):
        super().__init__(
            master,
            corner_radius=22,
            fg_color=("#f7faff", "#0f1d31"),
            border_width=1,
            border_color=("#c7d8ff", "#294166"),
            **kwargs,
        )

        self.history_manager = history_manager
        self.on_load_record = on_load_record
        self.on_history_changed = on_history_changed
        self.items: List[HistoryItem] = []
        self._records: List[HistoryRecord] = []
        self._rendered_count = 0

        self._build_ui()
        self.refresh()

    def _build_ui(self):
        """构建UI"""
        # 标题栏
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=5, pady=(5, 10))

        ctk.CTkLabel(
            header_frame,
            text="历史记录",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=("#10233f", "#f5f7ff"),
        ).pack(side="left")

        # 清空按钮
        clear_btn = ctk.CTkButton(
            header_frame,
            text="清空全部",
            width=86,
            height=32,
            corner_radius=16,
            fg_color=("#eef3ff", "#17283e"),
            hover_color=("#ffd9e0", "#4a1c2b"),
            text_color=("#10233f", "#f5f7ff"),
            font=ctk.CTkFont(size=12),
            command=self._on_clear_all,
        )
        clear_btn.pack(side="right")

        # 空状态提示
        self.empty_label = ctk.CTkLabel(
            self,
            text="暂无历史记录\n新的分析和调研会自动保存在这里。",
            font=ctk.CTkFont(size=13),
            text_color=("#60708c", "#92a3c7"),
        )

        self.load_more_btn = ctk.CTkButton(
            self,
            text="加载更多",
            width=100,
            height=34,
            corner_radius=17,
            fg_color=("#eef3ff", "#17283e"),
            hover_color=("#dde8ff", "#243956"),
            text_color=("#10233f", "#f5f7ff"),
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._load_next_page,
        )

    def refresh(self):
        """刷新历史记录列表"""
        # 清空现有项目
        for item in self.items:
            item.destroy()
        self.items.clear()
        self.load_more_btn.pack_forget()
        self._rendered_count = 0

        # 获取最新记录
        self._records = list(self.history_manager.get_all())

        if not self._records:
            self.empty_label.pack(expand=True, pady=50)
            return

        self.empty_label.pack_forget()
        self._load_next_page()

    def _load_next_page(self):
        """按批次渲染更多历史卡片。"""
        next_records = self._records[
            self._rendered_count : self._rendered_count + self.PAGE_SIZE
        ]

        for record in next_records:
            item = HistoryItem(
                self,
                record=record,
                on_click=self._on_item_click,
                on_delete=self._on_item_delete,
            )
            item.pack(fill="x", padx=5, pady=4)
            self.items.append(item)

        self._rendered_count += len(next_records)

        if self._rendered_count < len(self._records):
            self.load_more_btn.pack(pady=(8, 10))
        else:
            self.load_more_btn.pack_forget()

    def _on_item_click(self, record: HistoryRecord):
        """点击历史记录"""
        self.on_load_record(record)

    def _on_item_delete(self, record: HistoryRecord):
        """删除单条记录"""
        if messagebox.askyesno("确认删除", f"确定要删除「{record.title}」吗？"):
            self.history_manager.delete(record.id)
            self.refresh()
            if self.on_history_changed:
                self.on_history_changed()

    def _on_clear_all(self):
        """清空全部记录"""
        if not self.history_manager.get_all():
            messagebox.showinfo("提示", "暂无历史记录")
            return
        if messagebox.askyesno(
            "确认清空", "确定要清空所有历史记录吗？\n此操作不可恢复！"
        ):
            self.history_manager.clear()
            self.refresh()
            if self.on_history_changed:
                self.on_history_changed()
