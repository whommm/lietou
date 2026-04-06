import customtkinter as ctk

from src.ui.batch_match_widget import BatchMatchWidget


def test_batch_match_widget_updates_candidates_and_results():
    root = ctk.CTk()
    root.withdraw()
    widget = BatchMatchWidget(root, on_run_batch=lambda *args: None)

    widget.update_job_options(["算法岗 [01-01 10:00]"], {"算法岗 [01-01 10:00]": {}})
    widget.update_candidates(
        [
            {
                "candidate_id": "c1",
                "name": "张三",
                "current_title": "算法工程师",
                "current_company": "字节跳动",
                "keyword": "算法工程师",
            }
        ]
    )
    widget.set_results(
        [
            {
                "result_id": "r1",
                "candidate_name": "张三",
                "score": 90,
                "recommendation": "建议优先推进",
                "summary": "经验贴合",
                "risks": "无明显硬伤",
                "full_report_html": "<div>report</div>",
            }
        ],
        "批量匹配完成",
    )

    assert widget.job_combo.get() == "算法岗 [01-01 10:00]"
    assert "张三" in widget.candidate_box.get("1.0", "end")
    assert "建议优先推进" in widget.result_box.get("1.0", "end")

    widget.destroy()
    root.destroy()
