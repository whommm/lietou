"""Match criteria editor widget."""

import customtkinter as ctk
from tkinter import messagebox
from typing import Callable, List, Optional

from ..models import MatchCriteria, MatchCriterionItem


class _CriterionRow(ctk.CTkFrame):
    """A single editable row for a criterion item."""

    def __init__(
        self,
        master,
        item: MatchCriterionItem,
        on_delete: Callable,
        theme: str = "light",
        show_checkbox: bool = False,
        show_weight: bool = False,
        show_upgrade: bool = False,
        on_upgrade: Optional[Callable] = None,
        on_toggle: Optional[Callable] = None,
    ):
        super().__init__(master, fg_color="transparent")
        self.item = item
        self.on_delete = on_delete
        self.on_upgrade = on_upgrade
        self.on_toggle = on_toggle
        self.theme = theme

        self.checkbox = None
        self.weight_slider = None
        self.weight_label = None
        self.upgrade_btn = None

        self.text_entry = ctk.CTkEntry(
            self,
            placeholder_text="输入要求描述",
            corner_radius=12,
            height=32,
        )
        self.text_entry.insert(0, item.text)
        self.text_entry.grid(row=0, column=0, padx=(0, 6), sticky="ew")
        self.grid_columnconfigure(0, weight=1)
        col = 1

        if show_checkbox:
            self.checkbox = ctk.CTkCheckBox(
                self,
                text="启用",
                width=60,
                height=24,
                checkbox_width=18,
                checkbox_height=18,
                corner_radius=4,
            )
            self.checkbox.select() if item.enabled else self.checkbox.deselect()
            self.checkbox.grid(row=0, column=col, padx=6)
            if self.on_toggle:
                self.checkbox.configure(command=self._on_checkbox_change)
            col += 1

        if show_weight:
            self.weight_label = ctk.CTkLabel(self, text=f"{item.weight}%", width=45)
            self.weight_label.grid(row=0, column=col, padx=(6, 0))
            col += 1
            self.weight_slider = ctk.CTkSlider(
                self,
                from_=0,
                to=100,
                number_of_steps=100,
                width=120,
                height=16,
                corner_radius=8,
            )
            self.weight_slider.set(item.weight)
            self.weight_slider.grid(row=0, column=col, padx=6)
            self.weight_slider.bind("<ButtonRelease-1>", self._on_slider_release)
            col += 1

        if show_upgrade:
            self.upgrade_btn = ctk.CTkButton(
                self,
                text="设为硬门槛",
                width=80,
                height=26,
                corner_radius=10,
                font=ctk.CTkFont(size=11),
                command=self._on_upgrade_click,
            )
            self.upgrade_btn.grid(row=0, column=col, padx=6)
            col += 1

        self.del_btn = ctk.CTkButton(
            self,
            text="删除",
            width=50,
            height=26,
            corner_radius=10,
            fg_color="#ff4d4f",
            hover_color="#d9363e",
            text_color="white",
            font=ctk.CTkFont(size=11),
            command=self.on_delete,
        )
        self.del_btn.grid(row=0, column=col, padx=(6, 0))

    def _on_checkbox_change(self):
        if self.on_toggle:
            self.on_toggle()

    def _on_upgrade_click(self):
        if self.on_upgrade:
            self.on_upgrade(self.item)

    def _on_slider_release(self, _event=None):
        if self.weight_slider:
            val = int(round(self.weight_slider.get()))
            self.weight_label.configure(text=f"{val}%")
            self.item.weight = val

    def sync_to_item(self):
        self.item.text = self.text_entry.get().strip()
        if self.checkbox is not None:
            self.item.enabled = bool(self.checkbox.get())
        if self.weight_slider is not None:
            self.item.weight = int(round(self.weight_slider.get()))

    def refresh_weight_label(self):
        if self.weight_slider and self.weight_label:
            self.weight_slider.set(self.item.weight)
            self.weight_label.configure(text=f"{self.item.weight}%")


class MatchCriteriaEditor(ctk.CTkFrame):
    """Editable match criteria panel."""

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
        criteria: Optional[MatchCriteria] = None,
        on_save: Optional[Callable[[MatchCriteria], None]] = None,
        on_change: Optional[Callable[[MatchCriteria], None]] = None,
        theme: str = "light",
        **kwargs,
    ):
        super().__init__(master, **kwargs)
        self.on_save = on_save
        self.on_change = on_change
        self.theme = theme
        self._default_criteria: Optional[MatchCriteria] = None
        self._colors = self.PALETTE
        self.configure(fg_color=self._colors["panel_alt"], corner_radius=16)

        self._criteria = criteria if criteria is not None else MatchCriteria()
        self._dealbreaker_rows: List[_CriterionRow] = []
        self._core_rows: List[_CriterionRow] = []
        self._basic_rows: List[_CriterionRow] = []
        self._bonus_rows: List[_CriterionRow] = []

        self._build_header()
        self._build_sections()
        self._build_footer()
        self._refresh_all_rows()

    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=12, pady=(10, 6))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text="匹配标准编辑器",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=self._colors["text"],
        ).pack(side="left")

        btn_frame = ctk.CTkFrame(header, fg_color="transparent")
        btn_frame.pack(side="right")

        self.save_btn = ctk.CTkButton(
            btn_frame,
            text="保存并用于后续批量匹配",
            width=160,
            height=28,
            corner_radius=12,
            fg_color=self._colors["accent"],
            hover_color=self._colors["accent_hover"],
            text_color="white",
            font=ctk.CTkFont(size=11),
            command=self._on_save_click,
        )
        self.save_btn.pack(side="left", padx=(0, 6))

        self.reset_btn = ctk.CTkButton(
            btn_frame,
            text="恢复默认",
            width=80,
            height=28,
            corner_radius=12,
            fg_color=self._colors["secondary"],
            hover_color=self._colors["secondary_hover"],
            text_color=self._colors["text"],
            font=ctk.CTkFont(size=11),
            command=self._on_reset_click,
        )
        self.reset_btn.pack(side="left")

    def _build_sections(self):
        container = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            corner_radius=0,
        )
        container.pack(fill="both", expand=True, padx=8, pady=(0, 6))
        container._parent_frame.configure(fg_color="transparent")

        self.dealbreaker_frame = self._create_section(
            container, "一票否决项", self._add_dealbreaker
        )
        self.core_frame = self._create_section(
            container, "核心要求", self._add_core
        )
        self.basic_frame = self._create_section(
            container, "基础要求", self._add_basic
        )
        self.bonus_frame = self._create_section(
            container, "加分项", self._add_bonus
        )

        # Misjudgment reminders
        reminders_card = ctk.CTkFrame(
            container, fg_color=self._colors["panel"], corner_radius=12
        )
        reminders_card.pack(fill="x", pady=6, padx=2)
        ctk.CTkLabel(
            reminders_card,
            text="常见误判提醒",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=self._colors["text"],
        ).pack(anchor="w", padx=10, pady=(8, 4))
        self.reminders_text = ctk.CTkTextbox(
            reminders_card,
            height=80,
            wrap="word",
            corner_radius=10,
            border_width=1,
            border_color=self._colors["border"],
            fg_color=self._colors["panel_alt"],
            text_color=self._colors["text"],
            font=ctk.CTkFont(size=12),
        )
        self.reminders_text.pack(fill="x", padx=10, pady=(0, 8))

    def _create_section(self, parent, title: str, add_command):
        card = ctk.CTkFrame(parent, fg_color=self._colors["panel"], corner_radius=12)
        card.pack(fill="x", pady=6, padx=2)
        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=(8, 4))
        ctk.CTkLabel(
            header,
            text=title,
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=self._colors["text"],
        ).pack(side="left")
        add_btn = ctk.CTkButton(
            header,
            text="+ 新增",
            width=60,
            height=24,
            corner_radius=10,
            fg_color=self._colors["secondary"],
            hover_color=self._colors["secondary_hover"],
            text_color=self._colors["text"],
            font=ctk.CTkFont(size=11),
            command=add_command,
        )
        add_btn.pack(side="right")
        return card

    def _build_footer(self):
        self.footer_label = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(size=11),
            text_color=self._colors["muted"],
        )
        self.footer_label.pack(fill="x", padx=12, pady=(0, 8))

    def _refresh_all_rows(self):
        for frame, rows, show_cb, show_wt, show_up, on_up in (
            (
                self.dealbreaker_frame,
                self._dealbreaker_rows,
                True,
                False,
                False,
                None,
            ),
            (
                self.core_frame,
                self._core_rows,
                True,
                False,
                False,
                None,
            ),
            (
                self.basic_frame,
                self._basic_rows,
                False,
                False,
                True,
                self._upgrade_basic_to_dealbreaker,
            ),
            (self.bonus_frame, self._bonus_rows, False, False, False, None),
        ):
            # Destroy old widgets except header (first 2 children: header + add_btn parent)
            for widget in frame.winfo_children()[1:]:
                widget.destroy()
            rows.clear()
            items = {
                self.dealbreaker_frame: self._criteria.dealbreakers,
                self.core_frame: self._criteria.core_requirements,
                self.basic_frame: self._criteria.basic_requirements,
                self.bonus_frame: self._criteria.bonuses,
            }[frame]
            for item in items:
                row = _CriterionRow(
                    frame,
                    item,
                    on_delete=lambda f=frame, i=item: self._delete_row(f, i),
                    theme=self.theme,
                    show_checkbox=show_cb,
                    show_weight=show_wt,
                    show_upgrade=show_up,
                    on_upgrade=on_up,
                    on_toggle=self._on_row_toggle if show_cb or show_wt else None,
                )
                row.pack(fill="x", padx=10, pady=(2, 2))
                rows.append(row)

        self.reminders_text.delete("1.0", "end")
        self.reminders_text.insert(
            "1.0", "\n".join(self._criteria.misjudgment_reminders)
        )
        self._update_footer()

    def _on_row_toggle(self, *_args):
        self._sync_rows_to_items()
        self._update_footer()
        if self.on_change:
            self.on_change(self.get_criteria())

    def _delete_row(self, frame, item):
        items_map = {
            self.dealbreaker_frame: self._criteria.dealbreakers,
            self.core_frame: self._criteria.core_requirements,
            self.basic_frame: self._criteria.basic_requirements,
            self.bonus_frame: self._criteria.bonuses,
        }
        items = items_map.get(frame)
        if items and item in items:
            items.remove(item)
        self._refresh_all_rows()
        if self.on_change:
            self.on_change(self.get_criteria())

    def _add_dealbreaker(self):
        idx = len(self._criteria.dealbreakers) + 1
        self._criteria.dealbreakers.append(
            MatchCriterionItem(id=f"db_{idx}", text="", enabled=True)
        )
        self._refresh_all_rows()
        if self.on_change:
            self.on_change(self.get_criteria())

    def _add_core(self):
        idx = len(self._criteria.core_requirements) + 1
        self._criteria.core_requirements.append(
            MatchCriterionItem(id=f"core_{idx}", text="", enabled=True, weight=0)
        )
        self._refresh_all_rows()
        if self.on_change:
            self.on_change(self.get_criteria())

    def _add_basic(self):
        idx = len(self._criteria.basic_requirements) + 1
        self._criteria.basic_requirements.append(
            MatchCriterionItem(id=f"basic_{idx}", text="", enabled=True)
        )
        self._refresh_all_rows()
        if self.on_change:
            self.on_change(self.get_criteria())

    def _add_bonus(self):
        idx = len(self._criteria.bonuses) + 1
        self._criteria.bonuses.append(
            MatchCriterionItem(id=f"bonus_{idx}", text="", enabled=True)
        )
        self._refresh_all_rows()
        if self.on_change:
            self.on_change(self.get_criteria())

    def _upgrade_basic_to_dealbreaker(self, item: MatchCriterionItem):
        if item in self._criteria.basic_requirements:
            self._criteria.basic_requirements.remove(item)
            new_item = MatchCriterionItem(
                id=f"db_{len(self._criteria.dealbreakers)+1}",
                text=item.text,
                enabled=True,
                weight=0,
            )
            self._criteria.dealbreakers.append(new_item)
            self._refresh_all_rows()
            if self.on_change:
                self.on_change(self.get_criteria())

    def _sync_rows_to_items(self):
        for rows in (
            self._dealbreaker_rows,
            self._core_rows,
            self._basic_rows,
            self._bonus_rows,
        ):
            for row in rows:
                row.sync_to_item()
        reminders = self.reminders_text.get("1.0", "end").strip()
        self._criteria.misjudgment_reminders = [
            r.strip() for r in reminders.split("\n") if r.strip()
        ]

    def _update_footer(self):
        active_core = [r.item for r in self._core_rows if r.item.enabled]
        if active_core:
            self.footer_label.configure(
                text=f"当前启用的核心要求：{len(active_core)} 条 ✅",
                text_color="#52c41a",
            )
        else:
            self.footer_label.configure(
                text="至少要有 1 条启用的核心要求",
                text_color="#ff4d4f",
            )

    def _on_save_click(self):
        self._sync_rows_to_items()
        errors = self._criteria.validate()
        if errors:
            messagebox.showwarning("校验失败", "\n".join(errors))
            self._update_footer()
            return
        if self.on_save:
            self.on_save(self._criteria)
        messagebox.showinfo("成功", "匹配标准已保存，后续批量匹配将使用此版本")

    def _on_reset_click(self):
        if self._default_criteria is not None:
            self._criteria = MatchCriteria(
                dealbreakers=[
                    MatchCriterionItem(
                        id=i.id,
                        text=i.text,
                        enabled=i.enabled,
                        weight=i.weight,
                    )
                    for i in self._default_criteria.dealbreakers
                ],
                core_requirements=[
                    MatchCriterionItem(
                        id=i.id,
                        text=i.text,
                        enabled=i.enabled,
                        weight=i.weight,
                    )
                    for i in self._default_criteria.core_requirements
                ],
                basic_requirements=[
                    MatchCriterionItem(
                        id=i.id,
                        text=i.text,
                        enabled=i.enabled,
                        weight=i.weight,
                    )
                    for i in self._default_criteria.basic_requirements
                ],
                bonuses=[
                    MatchCriterionItem(
                        id=i.id,
                        text=i.text,
                        enabled=i.enabled,
                        weight=i.weight,
                    )
                    for i in self._default_criteria.bonuses
                ],
                misjudgment_reminders=list(
                    self._default_criteria.misjudgment_reminders
                ),
                version=self._default_criteria.version,
                confirmed_at=self._default_criteria.confirmed_at,
            )
            self._refresh_all_rows()
            if self.on_change:
                self.on_change(self._criteria)

    def set_criteria(self, criteria: MatchCriteria, set_as_default: bool = False):
        self._criteria = criteria
        if set_as_default:
            self._default_criteria = MatchCriteria(
                dealbreakers=[
                    MatchCriterionItem(
                        id=i.id, text=i.text, enabled=i.enabled, weight=i.weight
                    )
                    for i in criteria.dealbreakers
                ],
                core_requirements=[
                    MatchCriterionItem(
                        id=i.id, text=i.text, enabled=i.enabled, weight=i.weight
                    )
                    for i in criteria.core_requirements
                ],
                basic_requirements=[
                    MatchCriterionItem(
                        id=i.id, text=i.text, enabled=i.enabled, weight=i.weight
                    )
                    for i in criteria.basic_requirements
                ],
                bonuses=[
                    MatchCriterionItem(
                        id=i.id, text=i.text, enabled=i.enabled, weight=i.weight
                    )
                    for i in criteria.bonuses
                ],
                misjudgment_reminders=list(criteria.misjudgment_reminders),
                version=criteria.version,
                confirmed_at=criteria.confirmed_at,
            )
        self._refresh_all_rows()

    def get_criteria(self) -> MatchCriteria:
        self._sync_rows_to_items()
        return self._criteria
