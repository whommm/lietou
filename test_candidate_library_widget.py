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
                "strategy": {
                    "precise_keywords": ["算法工程师", "推荐系统"],
                    "atomic_terms": {
                        "capability_terms": ["算法"],
                        "domain_terms": ["推荐系统"],
                    },
                    "executable_rounds": [
                        {"label": "第1轮主搜", "query": "算法 推荐系统"}
                    ],
                }
            }
        },
    )

    assert widget.job_display.get() == "算法工程师 [01-01 10:00]"
    assert widget.strategy_payload["precise_keywords"] == ["算法工程师", "推荐系统"]
    info_text = widget.info_box.get("1.0", "end")
    assert "搜索轮次（1 条）" in info_text
    assert "算法 推荐系统" in info_text
    assert "原子词：能力[算法] 领域[推荐系统]" in info_text

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


def test_candidate_library_widget_passes_confirmed_filters_to_handler():
    root = create_root()
    captured = {}
    widget = CandidateLibraryWidget(
        root,
        on_launch_browser=lambda: None,
        on_check_login=lambda: None,
        on_run_task=lambda *args: captured.update(args=args),
    )
    widget.update_job_options(
        ["结构工程师 [01-01 10:00]"],
        {
            "结构工程师 [01-01 10:00]": {
                "strategy": {
                    "filters": {"目前城市": ["深圳", "广州"], "工作年限": "3-5年"},
                    "executable_rounds": [{"label": "主搜", "query": "结构 灯具"}],
                }
            }
        },
    )
    widget._confirm_before_run = lambda job_label, payload, auto_match_available=True: {"目前城市": ["深圳"], "工作年限": "3-5年"}

    widget._on_run_task_click()

    assert captured["args"][0] == "结构工程师 [01-01 10:00]"
    assert captured["args"][2] == {"目前城市": ["深圳"], "工作年限": "3-5年"}

    widget.destroy()
    root.destroy()


def test_auto_grab_confirm_dialog_parses_edited_filters_and_rounds():
    from src.ui.candidate_library_widget import AutoGrabConfirmDialog

    filters = AutoGrabConfirmDialog._parse_filter_text(
        "城市：深圳、广州\n工作年限：3-5年\n教育经历：本科\n性别：不限\n活跃度：近一周"
    )
    rounds = AutoGrabConfirmDialog._parse_round_text(
        '搜索计划（共 2 轮）：\n第1轮：算法 OR 推荐\n第2轮："搜索排序" AND 字节',
        [
            {"label": "测绘", "match_mode": "any", "scope": "全部经历"},
            {"label": "精准", "match_mode": "all", "scope": "目前职位"},
        ],
    )

    assert filters == {
        "目前城市": ["深圳", "广州"],
        "工作年限": "3-5年",
        "教育经历": "本科",
        "性别": "不限",
        "活跃度": "近一周",
    }
    assert rounds[0]["query"] == "算法 OR 推荐"
    assert rounds[0]["match_mode"] == "any"
    assert rounds[1]["query"] == '"搜索排序" AND 字节'
    assert rounds[1]["scope"] == "目前职位"


def test_candidate_library_widget_lists_source_keywords_in_candidate_records():
    root = create_root()
    widget = CandidateLibraryWidget(
        root,
        on_launch_browser=lambda: None,
        on_check_login=lambda: None,
        on_run_task=lambda *args: None,
    )

    widget.set_candidate_records(
        [
            {
                "name": "张三",
                "capture_status": "抓取成功",
                "source_keyword": "算法 推荐系统",
            }
        ]
    )

    content = widget.candidate_list_box.get("1.0", "end")
    assert "张三 [抓取成功] <算法 推荐系统>" in content

    widget.destroy()
    root.destroy()
