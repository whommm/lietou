import customtkinter as ctk
import pytest
from tkinter import TclError

from src.ui.batch_match_widget import BatchMatchWidget


def create_root():
    try:
        root = ctk.CTk()
        root.withdraw()
        return root
    except TclError as exc:
        pytest.skip("Tk environment unavailable: {}".format(exc))


def test_batch_match_widget_updates_candidates_and_results():
    root = create_root()
    called = {"cancel": False, "recent": False, "open_dir": False}
    widget = BatchMatchWidget(
        root,
        on_run_batch=lambda *args: None,
        on_cancel_batch=lambda: called.update(cancel=True),
        on_load_recent_batch=lambda: called.update(recent=True),
        on_open_excel_dir=lambda: called.update(open_dir=True),
    )

    widget.update_job_options(["算法岗 [01-01 10:00]"], {"算法岗 [01-01 10:00]": {}})
    widget.set_results("批量匹配完成")
    widget.set_excel_file("E:/Lietou/exports/candidates/demo.xlsx", matchable_count=1)

    assert widget.job_combo.get() == "算法岗 [01-01 10:00]"
    assert "demo.xlsx" in widget.excel_path_box.get("1.0", "end")
    assert "Excel" in widget.candidate_preview_label.cget("text")
    assert "批量匹配完成" in widget.summary_box.get("1.0", "end")

    widget.set_running(True)
    widget._on_cancel_batch_click()
    widget._on_load_recent_batch_click()
    widget._on_open_excel_dir_click()
    assert called["cancel"] is True
    assert called["recent"] is True
    assert called["open_dir"] is True

    widget.destroy()
    root.destroy()
