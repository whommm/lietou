import os

from src.core.candidate_excel_service import CandidateExcelService


def test_candidate_excel_service_creates_and_reads_workbook(tmp_path):
    service = CandidateExcelService(workspace_root=str(tmp_path))
    file_path = service.create_workbook("后端工程师")

    assert os.path.exists(file_path)
    assert file_path.endswith(".xlsx")

    row_index = service.append_candidate_row(
        file_path,
        {
            "序号": 1,
            "姓名": "张三",
            "年龄": "30岁",
            "页码": 1,
            "排名": 2,
            "简历链接": "https://example.com/resume/1",
            "简历抓取状态": service.CAPTURE_STATUS_PENDING,
            "抓取时间": service.now_text(),
        },
    )
    service.update_candidate_detail(
        file_path,
        row_index,
        "这是简历正文",
        service.CAPTURE_STATUS_SUCCESS,
    )

    records = service.load_candidates(file_path)

    assert len(records) == 1
    assert records[0].row_index == row_index
    assert records[0].name == "张三"
    assert records[0].age == "30岁"
    assert records[0].capture_status == service.CAPTURE_STATUS_SUCCESS
    assert records[0].resume_text == "这是简历正文"


def test_candidate_excel_service_filters_matchable_rows_and_writes_results(tmp_path):
    service = CandidateExcelService(workspace_root=str(tmp_path))
    file_path = service.create_workbook("产品经理")

    success_row = service.append_candidate_row(
        file_path,
        {
            "序号": 1,
            "姓名": "李四",
            "简历链接": "https://example.com/resume/ok",
            "简历抓取状态": service.CAPTURE_STATUS_SUCCESS,
            "简历详情": "完整简历",
            "抓取时间": service.now_text(),
        },
    )
    service.append_candidate_row(
        file_path,
        {
            "序号": 2,
            "姓名": "王五",
            "简历链接": "https://example.com/resume/fail",
            "简历抓取状态": service.CAPTURE_STATUS_FAILED,
            "简历详情": "",
            "抓取时间": service.now_text(),
        },
    )

    matchable = service.load_matchable_candidates(file_path)
    assert len(matchable) == 1
    assert matchable[0].name == "李四"

    service.write_match_result(file_path, success_row, 86, "建议优先推进")
    updated = service.load_candidates(file_path)
    target = [item for item in updated if item.row_index == success_row][0]

    assert target.match_score == 86
    assert target.match_detail == "建议优先推进"
    assert target.matched_at
