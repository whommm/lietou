import json
from tkinter import TclError

import customtkinter as ctk
import pytest

from src.models import MatchCriteria, MatchCriterionItem
from src.ui.match_criteria_widget import MatchCriteriaWidget


def create_root():
    try:
        root = ctk.CTk()
        root.withdraw()
        return root
    except TclError as exc:
        pytest.skip("Tk environment unavailable: {}".format(exc))


def test_match_criteria_widget_loads_and_saves_selected_job(monkeypatch):
    root = create_root()
    monkeypatch.setattr("src.ui.match_criteria_editor.messagebox.showinfo", lambda *args, **kwargs: None)
    saved = {}
    criteria = MatchCriteria(
        core_requirements=[
            MatchCriterionItem(id="cr_1", text="结构设计经验", weight=100)
        ]
    )
    widget = MatchCriteriaWidget(
        root,
        on_save=lambda label, payload, criteria: saved.update(
            label=label, payload=payload, criteria=criteria
        ),
    )

    widget.update_job_options(
        ["结构工程师 [01-01 10:00]"],
        {
            "结构工程师 [01-01 10:00]": {
                "record_id": "job_1",
                "match_criteria": json.dumps(criteria.to_dict(), ensure_ascii=False),
            }
        },
    )
    widget.editor._on_save_click()

    assert widget.job_display.get() == "结构工程师 [01-01 10:00]"
    assert saved["label"] == "结构工程师 [01-01 10:00]"
    assert saved["payload"]["record_id"] == "job_1"
    assert saved["criteria"].core_requirements[0].text == "结构设计经验"

    widget.destroy()
    root.destroy()
