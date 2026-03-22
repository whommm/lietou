"""历史记录UI组件模块"""

import customtkinter as ctk
from tkinter import messagebox
from typing import Callable, Optional, List

from ..core.history import HistoryRecord, HistoryManager


class HistoryItem(ctk.CTkFrame):
    """单条历史记录卡片"""

    def __init__(self, master, record: HistoryRecord, on_click: Callable, on_delete: Callable, **kwargs):
        super().__init__(
            master,
            corner_radius=8,
            border_width=1,
            border_color=("gray75", "gray35"),
            fg_color=("gray95", "gray20"),
            cursor="hand2",
            **kwargs
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
            anchor="w"
        )
        title_label.pack(side="left", fill="x", expand=True)

        # 删除按钮
        delete_btn = ctk.CTkButton(
            title_frame,
            text="×",
            width=24,
            height=24,
            corner_radius=12,
            fg_color="transparent",
            hover_color=("gray80", "gray35"),
            text_color=("gray50", "gray60"),
            font=ctk.CTkFont(size=16),
            command=self._on_delete_click
        )
        delete_btn.pack(side="right")

        # 时间
        time_label = ctk.CTkLabel(
            self,
            text=self.record.created_at,
            font=ctk.CTkFont(size=12),
            text_color=("gray50", "gray60"),
            anchor="w"
        )
        time_label.pack(fill="x", padx=10, pady=(2, 8))

    def _bind_events(self):
        """绑定点击事件"""
        def handle_click(event):
            # 点击删除按钮时不触发
            if event.widget.cget("text") != "×":
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

    def __init__(self, master, history_manager: HistoryManager, on_load_record: Callable, **kwargs):
        super().__init__(master, **kwargs)

        self.history_manager = history_manager
        self.on_load_record = on_load_record
        self.items: List[HistoryItem] = []

        self._build_ui()
        self.refresh()

    def _build_ui(self):
        """构建UI"""
        # 标题栏
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=5, pady=(5, 10))

        ctk.CTkLabel(
            header_frame,
            text="📋 历史记录",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(side="left")

        # 清空按钮
        clear_btn = ctk.CTkButton(
            header_frame,
            text="清空全部",
            width=70,
            height=26,
            corner_radius=6,
            fg_color=("gray75", "gray35"),
            hover_color=("red", "darkred"),
            font=ctk.CTkFont(size=12),
            command=self._on_clear_all
        )
        clear_btn.pack(side="right")

        # 空状态提示
        self.empty_label = ctk.CTkLabel(
            self,
            text="暂无历史记录\n分析岗位后将自动保存",
            font=ctk.CTkFont(size=13),
            text_color=("gray50", "gray60")
        )

    def refresh(self):
        """刷新历史记录列表"""
        # 清空现有项目
        for item in self.items:
            item.destroy()
        self.items.clear()

        # 获取最新记录
        records = self.history_manager.get_all()

        if not records:
            self.empty_label.pack(expand=True, pady=50)
            return

        self.empty_label.pack_forget()

        # 创建记录卡片
        for record in records:
            item = HistoryItem(
                self,
                record=record,
                on_click=self._on_item_click,
                on_delete=self._on_item_delete
            )
            item.pack(fill="x", padx=5, pady=4)
            self.items.append(item)

    def _on_item_click(self, record: HistoryRecord):
        """点击历史记录"""
        self.on_load_record(record)

    def _on_item_delete(self, record: HistoryRecord):
        """删除单条记录"""
        if messagebox.askyesno("确认删除", f"确定要删除「{record.title}」吗？"):
            self.history_manager.delete(record.id)
            self.refresh()

    def _on_clear_all(self):
        """清空全部记录"""
        if not self.history_manager.get_all():
            messagebox.showinfo("提示", "暂无历史记录")
            return
        if messagebox.askyesno("确认清空", "确定要清空所有历史记录吗？\n此操作不可恢复！"):
            self.history_manager.clear()
            self.refresh()
