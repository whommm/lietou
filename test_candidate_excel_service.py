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
            "来源关键词": "算法工程师",
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
    assert records[0].source_keyword == "算法工程师"
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
            "来源关键词": "产品经理",
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
    assert target.match_tier == "A"
    assert target.match_detail == "建议优先推进"
    assert target.matched_at
    assert service.count_greetable_candidates(file_path) == 1

    service.write_greeting_result(file_path, success_row, "发送成功", "您好")
    greeted = [item for item in service.load_candidates(file_path) if item.row_index == success_row][0]
    assert greeted.greeting_status == "发送成功"
    assert greeted.greeting_message == "您好"
    assert service.count_greetable_candidates(file_path) == 0


def test_candidate_excel_service_loads_matchable_rows_by_round_rows(tmp_path):
    service = CandidateExcelService(workspace_root=str(tmp_path))
    file_path = service.create_workbook("结构工程师")

    row_one = service.append_candidate_row(
        file_path,
        {
            "序号": 1,
            "姓名": "张三",
            "来源关键词": "结构 灯具",
            "简历抓取状态": service.CAPTURE_STATUS_SUCCESS,
            "简历详情": "完整简历1",
        },
    )
    row_two = service.append_candidate_row(
        file_path,
        {
            "序号": 2,
            "姓名": "李四",
            "来源关键词": "结构 照明",
            "简历抓取状态": service.CAPTURE_STATUS_SUCCESS,
            "简历详情": "完整简历2",
        },
    )
    service.append_candidate_row(
        file_path,
        {
            "序号": 3,
            "姓名": "王五",
            "来源关键词": "结构 LED",
            "简历抓取状态": service.CAPTURE_STATUS_FAILED,
            "简历详情": "",
        },
    )

    by_rows = service.load_matchable_candidates_by_rows(file_path, [row_two, 999])
    by_keyword = service.load_matchable_candidates_by_source_keyword(file_path, "结构 灯具")

    assert [item.row_index for item in by_rows] == [row_two]
    assert [item.row_index for item in by_keyword] == [row_one]


def test_candidate_excel_service_filters_greetable_gold_collar_without_contact(tmp_path):
    service = CandidateExcelService(workspace_root=str(tmp_path))
    file_path = service.create_workbook("金领候选人")

    gold_row = service.append_candidate_row(
        file_path,
        {
            "序号": 1,
            "姓名": "赵六",
            "简历链接": "https://example.com/resume/gold",
            "简历抓取状态": service.CAPTURE_STATUS_SUCCESS,
            "简历详情": "金领人才，完整简历",
            "匹配档位": "A",
            "人才标签": "金领",
            "联系方式": "",
        },
    )
    service.append_candidate_row(
        file_path,
        {
            "序号": 2,
            "姓名": "钱七",
            "简历链接": "https://example.com/resume/contact",
            "简历抓取状态": service.CAPTURE_STATUS_SUCCESS,
            "简历详情": "金领人才，电话 13800138000",
            "匹配档位": "A",
            "人才标签": "金领",
        },
    )
    service.append_candidate_row(
        file_path,
        {
            "序号": 3,
            "姓名": "孙八",
            "简历链接": "https://example.com/resume/normal",
            "简历抓取状态": service.CAPTURE_STATUS_SUCCESS,
            "简历详情": "普通候选人",
            "匹配档位": "A",
        },
    )

    strict = service.load_greetable_candidates(
        file_path,
        require_gold_collar=True,
        require_no_contact=True,
    )

    assert [item.row_index for item in strict] == [gold_row]
