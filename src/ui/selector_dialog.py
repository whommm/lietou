"""通用轻量选择器弹窗，用于替代 CTkComboBox。"""

from typing import Callable, List, Optional

import customtkinter as ctk


class SelectorDialog(ctk.CTkToplevel):
    """轻量记录选择弹窗，卡片式列表，支持搜索与分页。"""

    PAGE_SIZE = 12

    COLORS = {
        "window": "#edf4ff",
        "panel": "#ffffff",
        "border": "#d9e5ff",
        "text": "#13233d",
        "muted": "#64748f",
        "accent": "#4f7cff",
        "accent_hover": "#3f68e6",
        "item": "#ffffff",
        "item_hover": "#eef4ff",
        "item_active": "#d6e4ff",
    }

    def __init__(
        self,
        master,
        title: str,
        records: list,
        on_select: Callable[[object], None],
        empty_text: str = "暂无记录",
        get_display_text: Optional[Callable[[object], str]] = None,
    ):
        super().__init__(master)
        self.records = records
        self.on_select = on_select
        self.empty_text = empty_text
        self.get_display_text = get_display_text or (lambda r: str(r))

        self.filtered_records: list = list(records)
        self._selected_record: Optional[object] = None
        self._rendered_count = 0
        self._item_pool: List[tuple] = []

        self._setup_window(title)
        self._build_ui()
        self._render_records()

    def _setup_window(self, title: str):
        self.configure(fg_color=self.COLORS["window"])
        self.title(title)
        self.geometry("520x420")
        self.minsize(420, 360)
        self.transient(self.master)
        self.grab_set()

    def _build_ui(self):
        colors = self.COLORS
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # 搜索头
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, padx=16, pady=(16, 8), sticky="ew")
        header.grid_columnconfigure(0, weight=1)

        self.search_entry = ctk.CTkEntry(
            header,
            placeholder_text="搜索...",
            height=36,
            corner_radius=16,
            fg_color=colors["panel"],
            border_color=colors["border"],
            text_color=colors["text"],
        )
        self.search_entry.grid(row=0, column=0, sticky="ew")
        self.search_entry.bind("<KeyRelease>", self._on_search)

        # 列表区
        self.list_frame = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            corner_radius=0,
        )
        self.list_frame.grid(row=1, column=0, padx=16, pady=0, sticky="nsew")
        self.list_frame._parent_frame.configure(fg_color="transparent")

        # 加载更多
        self.load_more_btn = ctk.CTkButton(
            self,
            text="加载更多",
            width=100,
            height=32,
            corner_radius=16,
            fg_color=colors["panel"],
            hover_color=colors["item_hover"],
            text_color=colors["text"],
            font=ctk.CTkFont(size=12),
            command=self._load_next_page,
        )

        # 底部按钮
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=2, column=0, padx=16, pady=(8, 16), sticky="ew")
        footer.grid_columnconfigure(0, weight=1)

        ctk.CTkButton(
            footer,
            text="取消",
            width=80,
            height=34,
            corner_radius=16,
            fg_color=colors["panel"],
            hover_color=colors["item_hover"],
            text_color=colors["text"],
            command=self.destroy,
        ).grid(row=0, column=0, sticky="w")

        self.confirm_btn = ctk.CTkButton(
            footer,
            text="确认",
            width=100,
            height=34,
            corner_radius=16,
            fg_color=colors["accent"],
            hover_color=colors["accent_hover"],
            text_color="#f8fbff",
            font=ctk.CTkFont(size=12, weight="bold"),
            state="disabled",
            command=self._confirm,
        )
        self.confirm_btn.grid(row=0, column=1, sticky="e")

    def _on_search(self, _event=None):
        keyword = self.search_entry.get().strip().lower()
        if not keyword:
            self.filtered_records = list(self.records)
        else:
            self.filtered_records = [
                r for r in self.records
                if keyword in self.get_display_text(r).lower()
            ]
        self._selected_record = None
        self._rendered_count = 0
        self.confirm_btn.configure(state="disabled")
        self._render_records()

    def _render_records(self):
        for child in self.list_frame.winfo_children():
            child.destroy()
        self._item_pool.clear()
        self.load_more_btn.grid_remove()

        if not self.filtered_records:
            ctk.CTkLabel(
                self.list_frame,
                text=self.empty_text,
                text_color=self.COLORS["muted"],
                font=ctk.CTkFont(size=13),
            ).pack(expand=True, pady=40)
            return

        self._load_next_page()

    def _load_next_page(self):
        colors = self.COLORS
        next_records = self.filtered_records[
            self._rendered_count : self._rendered_count + self.PAGE_SIZE
        ]

        for record in next_records:
            item = ctk.CTkFrame(
                self.list_frame,
                corner_radius=12,
                fg_color=colors["item"],
                border_width=1,
                border_color=colors["border"],
                cursor="hand2",
                height=64,
            )
            item.pack(fill="x", padx=2, pady=(0, 8))
            item.pack_propagate(False)
            item.bind("<Button-1>", lambda _e, r=record: self._select_record(r))

            label = ctk.CTkLabel(
                item,
                text=self.get_display_text(record),
                text_color=colors["text"],
                font=ctk.CTkFont(size=13),
                anchor="w",
                justify="left",
            )
            label.pack(fill="both", expand=True, padx=14, pady=10)
            label.bind("<Button-1>", lambda _e, r=record: self._select_record(r))

            self._item_pool.append((record, item))

        self._rendered_count += len(next_records)
        if self._rendered_count < len(self.filtered_records):
            self.load_more_btn.grid(row=3, column=0, pady=(0, 12))
        else:
            self.load_more_btn.grid_remove()

    def _select_record(self, record):
        colors = self.COLORS
        self._selected_record = record
        self.confirm_btn.configure(state="normal")

        for r, widget in self._item_pool:
            if r == record:
                widget.configure(
                    fg_color=colors["item_active"],
                    border_color=colors["accent"],
                )
            else:
                widget.configure(
                    fg_color=colors["item"],
                    border_color=colors["border"],
                )

    def _confirm(self):
        if self._selected_record:
            self.on_select(self._selected_record)
        self.destroy()
