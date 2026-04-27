import customtkinter as ctk
import pytest
from tkinter import TclError

from src.core.history import HistoryManager
from src.ui.job_analysis_widget import JobAnalysisWidget


def create_root():
    try:
        root = ctk.CTk()
        root.withdraw()
        return root
    except TclError as exc:
        pytest.skip("Tk environment unavailable: {}".format(exc))


def test_job_analysis_widget_exposes_auto_capture_button(tmp_path):
    root = create_root()
    history_manager = HistoryManager(
        record_type="job_analysis",
        history_path=str(tmp_path / "history_job_analysis.json"),
        db_path=str(tmp_path / "test.db"),
    )
    widget = JobAnalysisWidget(
        root,
        on_analyze=lambda *args: None,
        history_manager=history_manager,
        company_options=["不使用"],
        on_send_to_candidates=lambda *args: None,
        on_auto_search_candidates=lambda *args: None,
    )

    assert widget.auto_capture_btn.cget("text") == "自动搜索并抓取"

    widget.destroy()
    root.destroy()
