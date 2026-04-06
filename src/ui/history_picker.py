"""历史选择器弹窗。"""

from typing import Callable, List, Optional

import customtkinter as ctk

from ..core.history import HistoryRecord


class HistoryPickerDialog(ctk.CTkToplevel):
    """用于从历史记录中选择条目的弹窗。"""

    PAGE_SIZE = 24

    PALETTE = {
        "window": "#edf4ff",
        "panel": "#ffffff",
        "panel_alt": "#f7faff",
        "border": "#d9e5ff",
        "text": "#13233d",
        "muted": "#64748f",
        "accent": "#4f7cff",
        "accent_hover": "#3f68e6",
        "secondary": "#edf3ff",
        "secondary_hover": "#dde8ff",
        "item": "#ffffff",
        "item_hover": "#eef4ff",
    }

    def __init__(
        self,
        master,
        title: str,
        records: List[HistoryRecord],
        on_select: Callable[[HistoryRecord], None],
        empty_text: str,
        theme: str = "light",
    ):
        super().__init__(master)
        self.records = records
        self.on_select = on_select
        self.theme = theme
        self.filtered_records = list(records)
        self._selected_record: Optional[HistoryRecord] = None
        self._item_frames = []
        self._rendered_count = 0
        self._empty_text = empty_text
        self._title = title

        colors = self.PALETTE
        self.configure(fg_color=colors["window"])
        self.title(title)
        self.geometry("760x560")
        self.minsize(640, 480)
        self.transient(master)
        self.grab_set()

        self._build_ui()
        self._render_records()

    def _build_ui(self):
        colors = self.PALETTE
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(
            self,
            corner_radius=24,
            fg_color=colors["panel"],
            border_width=1,
            border_color=colors["border"],
        )
        header.grid(row=0, column=0, padx=16, pady=(16, 8), sticky="ew")
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text=self._title,
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=colors["text"],
        ).grid(row=0, column=0, padx=18, pady=(16, 4), sticky="w")

        ctk.CTkLabel(
            header,
            text="最近 3 条保留在页面上，完整记录在这里搜索和选择。",
            font=ctk.CTkFont(size=12),
            text_color=colors["muted"],
        ).grid(row=1, column=0, padx=18, pady=(0, 12), sticky="w")

        self.search_entry = ctk.CTkEntry(
            header,
            placeholder_text="搜索标题或预览内容...",
            height=38,
            corner_radius=16,
            fg_color=colors["panel_alt"],
            border_color=colors["border"],
            text_color=colors["text"],
        )
        self.search_entry.grid(row=2, column=0, padx=18, pady=(0, 16), sticky="ew")
        self.search_entry.bind("<KeyRelease>", self._on_search)

        body = ctk.CTkFrame(
            self,
            corner_radius=24,
            fg_color=colors["panel"],
            border_width=1,
            border_color=colors["border"],
        )
        body.grid(row=1, column=0, padx=16, pady=8, sticky="nsew")
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(0, weight=1)

        self.list_frame = ctk.CTkScrollableFrame(body, fg_color="transparent")
        self.list_frame.grid(row=0, column=0, padx=12, pady=12, sticky="nsew")

        self.load_more_btn = ctk.CTkButton(
            body,
            text="加载更多",
            width=100,
            height=34,
            corner_radius=17,
            fg_color=colors["secondary"],
            hover_color=colors["secondary_hover"],
            text_color=colors["text"],
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._load_next_page,
        )
        self.load_more_btn.grid(row=1, column=0, pady=(0, 12))

        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=2, column=0, padx=16, pady=(8, 16), sticky="ew")
        footer.grid_columnconfigure(0, weight=1)

        self.cancel_btn = ctk.CTkButton(
            footer,
            text="取消",
            width=92,
            height=38,
            corner_radius=18,
            fg_color=colors["secondary"],
            hover_color=colors["secondary_hover"],
            text_color=colors["text"],
            command=self.destroy,
        )
        self.cancel_btn.grid(row=0, column=0, padx=6, sticky="w")

        self.confirm_btn = ctk.CTkButton(
            footer,
            text="选择并载入",
            width=120,
            height=40,
            corner_radius=20,
            fg_color=colors["accent"],
            hover_color=colors["accent_hover"],
            text_color="#f8fbff",
            font=ctk.CTkFont(size=12, weight="bold"),
            state="disabled",
            command=self._confirm,
        )
        self.confirm_btn.grid(row=0, column=1, padx=6, sticky="e")

    def _on_search(self, _event=None):
        keyword = self.search_entry.get().strip().lower()
        if not keyword:
            self.filtered_records = list(self.records)
        else:
            self.filtered_records = [
                record
                for record in self.records
                if keyword in record.title.lower()
                or keyword in (record.jd_text or "").lower()
                or keyword in (record.result or "").lower()
            ]
        self._selected_record = None
        self._rendered_count = 0
        self.confirm_btn.configure(state="disabled")
        self._render_records()

    def _render_records(self):
        colors = self.PALETTE
        for child in self.list_frame.winfo_children():
            child.destroy()
        self._item_frames.clear()
        self.load_more_btn.grid_remove()

        if not self.filtered_records:
            ctk.CTkLabel(
                self.list_frame,
                text=self._empty_text,
                text_color=colors["muted"],
                font=ctk.CTkFont(size=13),
            ).pack(expand=True, pady=60)
            return

        self._load_next_page()

    def _load_next_page(self):
        """按批次渲染更多搜索结果。"""
        colors = self.PALETTE
        next_records = self.filtered_records[
            self._rendered_count : self._rendered_count + self.PAGE_SIZE
        ]

        for record in next_records:
            item = ctk.CTkFrame(
                self.list_frame,
                corner_radius=18,
                fg_color=colors["item"],
                border_width=1,
                border_color=colors["border"],
                cursor="hand2",
            )
            item.pack(fill="x", padx=4, pady=6)
            item.bind("<Button-1>", lambda _e, r=record: self._select_record(r))

            top = ctk.CTkFrame(item, fg_color="transparent")
            top.pack(fill="x", padx=14, pady=(12, 4))

            title = ctk.CTkLabel(
                top,
                text=record.title,
                text_color=colors["text"],
                font=ctk.CTkFont(size=15, weight="bold"),
                anchor="w",
            )
            title.pack(side="left", fill="x", expand=True)
            title.bind("<Button-1>", lambda _e, r=record: self._select_record(r))

            time_label = ctk.CTkLabel(
                top,
                text=record.created_at,
                text_color=colors["muted"],
                font=ctk.CTkFont(size=11),
            )
            time_label.pack(side="right")
            time_label.bind("<Button-1>", lambda _e, r=record: self._select_record(r))

            preview_text = (record.jd_text or record.result or "").replace("\n", " ")[
                :140
            ]
            preview = ctk.CTkLabel(
                item,
                text=preview_text,
                text_color=colors["muted"],
                font=ctk.CTkFont(size=12),
                justify="left",
                anchor="w",
                wraplength=620,
            )
            preview.pack(fill="x", padx=14, pady=(0, 12))
            preview.bind("<Button-1>", lambda _e, r=record: self._select_record(r))

            self._item_frames.append((record, item))

        self._rendered_count += len(next_records)
        if self._rendered_count < len(self.filtered_records):
            self.load_more_btn.grid()
        else:
            self.load_more_btn.grid_remove()

    def _select_record(self, record: HistoryRecord):
        colors = self.PALETTE
        self._selected_record = record
        self.confirm_btn.configure(state="normal")
        for current_record, frame in self._item_frames:
            frame.configure(
                fg_color=colors["item_hover"]
                if current_record.id == record.id
                else colors["item"]
            )

    def _confirm(self):
        if not self._selected_record:
            return
        self.on_select(self._selected_record)
        self.destroy()
