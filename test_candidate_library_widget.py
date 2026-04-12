import customtkinter as ctk
import pytest
from tkinter import TclError
from tkinter import messagebox

from src.ui.candidate_library_widget import CandidateLibraryWidget


def create_root():
    try:
        root = ctk.CTk()
        root.withdraw()
        return root
    except TclError as exc:
        pytest.skip("Tk environment unavailable: {}".format(exc))


def test_candidate_library_widget_updates_job_options():
    root = create_root()
    widget = CandidateLibraryWidget(
        root,
        on_launch_browser=lambda: None,
        on_check_login=lambda: None,
        on_run_task=lambda *args: None,
    )

    widget.update_job_options(
        ["算法工程师 [01-01 10:00]"],
        {
            "算法工程师 [01-01 10:00]": {
                "strategy": {"precise_keywords": ["算法工程师", "推荐系统"]}
            }
        },
    )

    assert widget.job_display.get() == "算法工程师 [01-01 10:00]"
    assert widget.strategy_payload == {"precise_keywords": ["算法工程师", "推荐系统"]}

    widget.destroy()
    root.destroy()


def test_candidate_library_widget_calls_export_debug_handler():
    root = create_root()
    called = {"value": False}
    widget = CandidateLibraryWidget(
        root,
        on_launch_browser=lambda: None,
        on_check_login=lambda: None,
        on_run_task=lambda *args: None,
        on_export_debug=lambda: called.update(value=True),
    )

    widget._on_export_debug_click()

    assert called["value"] is True

    widget.destroy()
    root.destroy()


def test_candidate_library_widget_keeps_task_console_actions():
    root = create_root()
    widget = CandidateLibraryWidget(
        root,
        on_launch_browser=lambda: None,
        on_check_login=lambda: None,
        on_run_task=lambda *args: None,
    )

    assert widget.launch_browser_btn.cget("text") == "启动猎聘浏览器"
    assert widget.run_task_btn.cget("text") == "开始抓取并写入 Excel"
    assert "当前还没有候选人 Excel 文件" in widget.excel_path_box.get("1.0", "end")

    widget.destroy()
    root.destroy()


def test_candidate_library_widget_imports_excel_through_handler():
    root = create_root()
    captured = {"imported": False, "open_dir": False}
    widget = CandidateLibraryWidget(
        root,
        on_launch_browser=lambda: None,
        on_check_login=lambda: None,
        on_run_task=lambda *args: None,
        on_import_excel=lambda: captured.update(imported=True),
        on_open_excel_dir=lambda: captured.update(open_dir=True),
    )

    widget._on_import_excel_click()
    widget._on_open_excel_dir_click()

    assert captured["imported"] is True
    assert captured["open_dir"] is True

    widget.destroy()
    root.destroy()
