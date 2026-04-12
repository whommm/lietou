"""Global background task list panel."""

import customtkinter as ctk
from typing import Callable, Optional

from ..core.task_queue import TaskQueue, TaskStatus


class TaskPanel(ctk.CTkToplevel):
    """Floating window showing all background tasks and their progress."""

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
        "success": "#10b981",
        "warning": "#f59e0b",
        "danger": "#ef4444",
    }

    STATUS_COLORS = {
        TaskStatus.PENDING: ("#60708c", "待执行"),
        TaskStatus.RUNNING: ("#4f7cff", "运行中"),
        TaskStatus.COMPLETED: ("#10b981", "已完成"),
        TaskStatus.FAILED: ("#ef4444", "失败"),
        TaskStatus.CANCELLED: ("#f59e0b", "已取消"),
    }

    def __init__(
        self,
        master,
        task_queue: TaskQueue,
        on_cancel: Optional[Callable[[str], None]] = None,
        **kwargs,
    ):
        super().__init__(master, **kwargs)
        self.task_queue = task_queue
        self.on_cancel = on_cancel
        self._refresh_handle: Optional[str] = None
        self._row_widgets: dict = {}

        self.title("后台任务")
        self.geometry("600x400")
        self.minsize(500, 300)
        self.configure(fg_color=self.PALETTE["panel"])

        self._build_header()
        self._build_list_container()
        self._start_refresh()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_header(self):
        colors = self.PALETTE
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(16, 8))

        ctk.CTkLabel(
            header,
            text="后台任务队列",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=colors["text"],
        ).pack(side="left")

        self.count_label = ctk.CTkLabel(
            header,
            text="",
            font=ctk.CTkFont(size=12),
            text_color=colors["muted"],
        )
        self.count_label.pack(side="right")

    def _build_list_container(self):
        colors = self.PALETTE
        self.list_frame = ctk.CTkScrollableFrame(
            self,
            fg_color=colors["panel_alt"],
            corner_radius=16,
            border_width=1,
            border_color=colors["border"],
        )
        self.list_frame.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        self.list_frame.grid_columnconfigure(0, weight=1)

    def _start_refresh(self):
        self._refresh()

    def _stop_refresh(self):
        if self._refresh_handle:
            try:
                self.after_cancel(self._refresh_handle)
            except Exception:
                pass
            self._refresh_handle = None

    def _refresh(self):
        if not self.winfo_exists():
            return
        self._render_tasks()
        self._refresh_handle = self.after(1000, self._refresh)

    def _render_tasks(self):
        tasks = self.task_queue.list_tasks()
        active_count = sum(
            1 for t in tasks if t.status in (TaskStatus.PENDING, TaskStatus.RUNNING)
        )
        self.count_label.configure(
            text="活跃 {} / 总计 {}".format(active_count, len(tasks))
        )

        # Reconcile rows
        current_ids = {t.task_id for t in tasks}
        for tid in list(self._row_widgets.keys()):
            if tid not in current_ids:
                self._row_widgets[tid].destroy()
                del self._row_widgets[tid]

        for idx, task in enumerate(tasks):
            if task.task_id in self._row_widgets:
                self._update_row(task, idx)
            else:
                self._create_row(task, idx)

    def _create_row(self, task, row_index: int):
        colors = self.PALETTE
        frame = ctk.CTkFrame(self.list_frame, fg_color=colors["panel"], corner_radius=12)
        frame.grid(row=row_index, column=0, padx=8, pady=6, sticky="ew")
        frame.grid_columnconfigure(0, weight=1)

        top = ctk.CTkFrame(frame, fg_color="transparent")
        top.grid(row=0, column=0, padx=12, pady=(10, 2), sticky="ew")
        top.grid_columnconfigure(0, weight=1)

        name_label = ctk.CTkLabel(
            top,
            text=task.name,
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=colors["text"],
            anchor="w",
        )
        name_label.grid(row=0, column=0, sticky="w")

        status_color, status_text = self.STATUS_COLORS.get(
            task.status, (colors["muted"], str(task.status.value))
        )
        status_label = ctk.CTkLabel(
            top,
            text=status_text,
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=status_color,
        )
        status_label.grid(row=0, column=1, sticky="e")

        progress_label = ctk.CTkLabel(
            frame,
            text=self._format_progress(task),
            font=ctk.CTkFont(size=12),
            text_color=colors["muted"],
            anchor="w",
        )
        progress_label.grid(row=1, column=0, padx=12, pady=(2, 2), sticky="w")

        action_btn = ctk.CTkButton(
            frame,
            text="取消",
            width=70,
            height=28,
            corner_radius=10,
            font=ctk.CTkFont(size=11),
            fg_color=colors["secondary"],
            hover_color=colors["secondary_hover"],
            text_color=colors["text"],
            command=lambda tid=task.task_id: self._on_cancel_click(tid),
        )
        action_btn.grid(row=2, column=0, padx=12, pady=(2, 10), sticky="e")

        self._row_widgets[task.task_id] = frame
        frame._widgets = {
            "name": name_label,
            "status": status_label,
            "progress": progress_label,
            "action": action_btn,
        }

    def _update_row(self, task, row_index: int):
        frame = self._row_widgets.get(task.task_id)
        if frame is None:
            return
        # Ensure ordering (grid row index may change as tasks finish/new arrive)
        frame.grid(row=row_index, column=0)

        w = frame._widgets
        status_color, status_text = self.STATUS_COLORS.get(
            task.status, (self.PALETTE["muted"], str(task.status.value))
        )
        w["status"].configure(text=status_text, text_color=status_color)
        w["progress"].configure(text=self._format_progress(task))

        if task.status in (TaskStatus.PENDING, TaskStatus.RUNNING):
            w["action"].configure(
                text="取消",
                state="normal",
                command=lambda tid=task.task_id: self._on_cancel_click(tid),
            )
        else:
            w["action"].configure(text="移除", state="normal")
            w["action"].configure(
                command=lambda fid=frame: self._remove_frame(fid, task.task_id)
            )

    def _format_progress(self, task) -> str:
        if task.status == TaskStatus.PENDING:
            return "等待调度..."
        if task.status == TaskStatus.RUNNING:
            parts = []
            if task.progress_total > 0:
                parts.append("进度 {}/{}".format(task.progress_current, task.progress_total))
            if task.progress_message:
                parts.append(task.progress_message)
            return " | ".join(parts) if parts else "正在执行..."
        if task.status == TaskStatus.COMPLETED:
            return "任务已完成"
        if task.status == TaskStatus.CANCELLED:
            return "任务已取消"
        return "错误：{}".format(task.error_message or "未知错误")

    def _on_cancel_click(self, task_id: str):
        if self.on_cancel:
            self.on_cancel(task_id)
        else:
            self.task_queue.cancel_task(task_id)

    def _remove_frame(self, frame, task_id: str):
        frame.destroy()
        if task_id in self._row_widgets:
            del self._row_widgets[task_id]

    def _on_close(self):
        self._stop_refresh()
        self.destroy()
