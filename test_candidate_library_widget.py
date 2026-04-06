import customtkinter as ctk

from src.ui.candidate_library_widget import CandidateLibraryWidget


def test_candidate_library_widget_updates_job_options():
    root = ctk.CTk()
    root.withdraw()
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

    assert widget.job_combo.get() == "算法工程师 [01-01 10:00]"
    assert "算法工程师" in widget.strategy_box.get("1.0", "end")

    widget.destroy()
    root.destroy()


def test_candidate_library_widget_calls_export_debug_handler():
    root = ctk.CTk()
    root.withdraw()
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
