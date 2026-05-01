import os

from src.core.candidate_excel_service import CandidateExcelService
from src.core.database import DatabaseManager
from src.core.liepin_search_service import LiepinSearchCandidate
from src.core.liepin_search_service import LiepinSearchNoResultsError
from src.core.liepin_search_task_service import LiepinSearchTaskService
from src.core.search_task_repository import SearchTaskRepository
from src.models import Candidate


class FakePage:
    def __init__(self):
        self.visited_urls = []

    def goto(self, url, wait_until=None):
        self.visited_urls.append(url)


class FakeBrowserManager:
    def __init__(self):
        self.page = FakePage()

    def ensure_page(self):
        return self.page


class FakeSearchService:
    def __init__(self, current_results=None, query_sequences=None, next_page_results=None):
        self.current_results = current_results or []
        self.query_sequences = dict(query_sequences or {})
        self.next_page_results = dict(next_page_results or {})
        self.browser_manager = FakeBrowserManager()
        self.extract_calls = 0
        self.search_calls = []
        self.open_calls = []
        self.closed_pages = []
        self.result_page = self.browser_manager.page
        self.page_index = 0
        self.current_query = ""
        self.next_page_calls = 0

    def search(self, keyword):
        self.search_calls.append(keyword)
        self.current_query = keyword
        self.page_index = 0
        return self._get_current_page_results()

    def _get_current_page_results(self):
        pages = self.query_sequences.get(self.current_query)
        if pages is None:
            pages = [list(self.current_results)]
        index = min(self.page_index, len(pages) - 1)
        return list(pages[index])

    def extract_current_page_candidates(self):
        self.extract_calls += 1
        return self._get_current_page_results()

    def ensure_result_page(self):
        return self.result_page

    def go_to_next_result_page(self):
        self.next_page_calls += 1
        results = self.next_page_results.get(self.current_query, [])
        if not results:
            return False
        should_advance = results.pop(0)
        if should_advance:
            self.page_index += 1
        return should_advance

    def open_candidate_detail(self, page, candidate):
        assert page is self.result_page
        self.open_calls.append(candidate.profile_url or candidate.name)
        if candidate.profile_url:
            page.goto(candidate.profile_url, wait_until="domcontentloaded")
        return page

    def close_detail_page(self, detail_page, result_page):
        self.closed_pages.append((detail_page, result_page))
        return result_page


class FakeFilterSearchService(FakeSearchService):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.search_filter_calls = []

    def search(self, keyword, filters=None):
        self.search_filter_calls.append((keyword, filters))
        return super().search(keyword)


class FakeControlSearchService(FakeSearchService):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.search_control_calls = []

    def search(self, keyword, filters=None, match_mode="", scope="", position_filter=""):
        self.search_control_calls.append((keyword, filters, match_mode, scope, position_filter))
        return super().search(keyword)


class FakeResumeExtractor:
    def __init__(self, broken_urls=None):
        self.broken_urls = set(broken_urls or [])

    def extract_candidate(self, page, summary):
        if summary.profile_url in self.broken_urls:
            raise RuntimeError("extract failed")
        return Candidate(
            id="",
            profile_url=summary.profile_url,
            name=summary.name,
            current_title=summary.current_title,
            current_company=summary.current_company,
            resume_text="【候选人基础信息】\n姓名：{}".format(summary.name),
            resume_summary=summary.summary or summary.name,
        )


def build_service(tmp_path, search_service, broken_urls=None):
    manager = DatabaseManager(db_path=os.path.join(tmp_path, "test.db"))
    task_repository = SearchTaskRepository(manager)
    excel_service = CandidateExcelService(workspace_root=str(tmp_path))
    service = LiepinSearchTaskService(
        task_repository=task_repository,
        candidate_excel_service=excel_service,
        search_service=search_service,
        resume_extractor=FakeResumeExtractor(broken_urls=broken_urls),
    )
    return task_repository, excel_service, service


def test_run_task_executes_search_round_and_imports_candidates(tmp_path):
    search_service = FakeSearchService(
        query_sequences={
            "算法工程师": [
                [
                    LiepinSearchCandidate(
                        name="张三",
                        current_title="高级算法工程师",
                        current_company="字节跳动",
                        profile_url="https://example.com/resume/1",
                        summary="推荐系统",
                    ),
                    LiepinSearchCandidate(
                        name="李四",
                        current_title="算法专家",
                        current_company="百度",
                        profile_url="https://example.com/resume/2",
                        summary="搜索排序",
                    ),
                ]
            ]
        }
    )
    task_repository, excel_service, service = build_service(tmp_path, search_service)
    task = task_repository.create(
        job_history_id="job_001",
        task_name="算法岗搜索",
        keywords={
            "precise_keywords": ["算法工程师"],
            "executable_rounds": [{"query": "算法工程师", "label": "主搜", "priority": 1}],
        },
        max_candidates=2,
    )

    summary = service.run_task(task.id)
    updated_task = task_repository.get_by_id(task.id)
    records = excel_service.load_candidates(summary.excel_path)

    assert os.path.exists(summary.excel_path)
    assert summary.sourced_candidate_count == 2
    assert summary.enriched_candidate_count == 2
    assert summary.partial_candidate_count == 0
    assert summary.failed_candidate_count == 0
    assert summary.pages_processed == 1
    assert summary.processed_keywords == ["算法工程师"]
    assert search_service.search_calls == ["算法工程师"]
    assert search_service.open_calls == [
        "https://example.com/resume/1",
        "https://example.com/resume/2",
    ]
    assert len(search_service.closed_pages) == 2
    assert updated_task is not None
    assert updated_task.status == "completed"
    assert updated_task.executed_queries_json
    assert updated_task.query_level_stats_json
    assert len(records) == 2
    assert records[0].source_keyword == "算法工程师"
    assert records[0].resume_text
    assert records[0].capture_status == "抓取成功"
    executed_queries = __import__("json").loads(updated_task.executed_queries_json)
    query_stats = __import__("json").loads(updated_task.query_level_stats_json)
    assert executed_queries[0]["query"] == "算法工程师"
    assert query_stats[0]["accepted_candidates"] == 2
    assert query_stats[0]["deduplicated_candidates"] == 0
    assert search_service.browser_manager.page.visited_urls == [
        "https://example.com/resume/1",
        "https://example.com/resume/2",
    ]


def test_run_task_keeps_going_when_one_candidate_fails(tmp_path):
    search_service = FakeSearchService(
        query_sequences={
            "产品经理": [
                [
                    LiepinSearchCandidate(
                        name="王五",
                        current_title="产品经理",
                        current_company="美团",
                        profile_url="https://example.com/resume/bad",
                        summary="增长产品",
                    ),
                    LiepinSearchCandidate(
                        name="赵六",
                        current_title="高级产品经理",
                        current_company="京东",
                        profile_url="https://example.com/resume/good",
                        summary="商业化",
                    ),
                ]
            ]
        }
    )
    task_repository, excel_service, service = build_service(
        tmp_path,
        search_service,
        broken_urls={"https://example.com/resume/bad"},
    )
    task = task_repository.create(
        job_history_id="job_001",
        task_name="产品岗搜索",
        keywords={"precise_keywords": ["产品经理"]},
        max_candidates=5,
    )

    summary = service.run_task(task.id)
    updated_task = task_repository.get_by_id(task.id)
    records = excel_service.load_candidates(summary.excel_path)

    assert summary.sourced_candidate_count == 2
    assert summary.enriched_candidate_count == 1
    assert summary.partial_candidate_count == 1
    assert summary.failed_candidate_count == 1
    assert summary.pages_processed == 1
    assert (
        summary.failed_candidates[0]["identifier"] == "https://example.com/resume/bad"
    )
    assert summary.failed_candidates[0]["page_number"] == 1
    assert summary.failed_candidates[0]["rank_index"] == 1
    assert "候选人详情处理失败" in summary.failed_candidates[0]["reason"]
    assert summary.processed_keywords == ["产品经理"]
    assert updated_task is not None
    assert updated_task.status == "completed"
    assert len(records) == 2
    failed_record = [item for item in records if item.profile_url.endswith("bad")][0]
    assert failed_record.capture_status == "抓取失败"


def test_run_task_processes_multiple_pages_until_limit(tmp_path):
    search_service = FakeSearchService(
        query_sequences={
            "后端工程师": [
                [
                    LiepinSearchCandidate(
                        name="A", profile_url="https://example.com/resume/1"
                    ),
                    LiepinSearchCandidate(
                        name="B", profile_url="https://example.com/resume/2"
                    ),
                ],
                [
                    LiepinSearchCandidate(
                        name="C", profile_url="https://example.com/resume/3"
                    ),
                    LiepinSearchCandidate(
                        name="D", profile_url="https://example.com/resume/4"
                    ),
                ],
            ]
        },
        next_page_results={"后端工程师": [True, False]},
    )
    task_repository, excel_service, service = build_service(tmp_path, search_service)
    task = task_repository.create(
        job_history_id="job_002",
        task_name="多页搜索",
        keywords={
            "precise_keywords": ["后端工程师"],
            "executable_rounds": [{"query": "后端工程师", "label": "主搜", "priority": 1}],
        },
        max_pages=3,
        max_candidates=3,
    )

    summary = service.run_task(task.id)
    records = excel_service.load_candidates(summary.excel_path)

    assert summary.pages_processed == 2
    assert summary.sourced_candidate_count == 3
    assert summary.enriched_candidate_count == 3
    assert search_service.search_calls == ["后端工程师"]
    assert search_service.extract_calls == 1
    assert search_service.next_page_calls == 1
    assert summary.query_level_stats[0]["pages_processed"] == 2
    assert summary.query_level_stats[0]["raw_candidates"] == 4
    assert summary.query_level_stats[0]["accepted_candidates"] == 3
    assert len(records) == 3
    assert {item.page_number for item in records} == {1, 2}


def test_run_task_deduplicates_candidates_across_rounds(tmp_path):
    duplicate = LiepinSearchCandidate(
        name="张三",
        current_title="高级算法工程师",
        current_company="字节跳动",
        profile_url="https://example.com/resume/1",
    )
    search_service = FakeSearchService(
        query_sequences={
            "算法 工程师": [[duplicate]],
            "推荐 系统": [[duplicate, LiepinSearchCandidate(name="李四", profile_url="https://example.com/resume/2")]],
        }
    )
    task_repository, excel_service, service = build_service(tmp_path, search_service)
    task = task_repository.create(
        job_history_id="job_003",
        task_name="多轮去重",
        keywords={
            "executable_rounds": [
                {"query": "算法 工程师", "label": "第一轮", "priority": 1},
                {"query": "推荐 系统", "label": "第二轮", "priority": 2},
            ]
        },
        max_pages=1,
        max_candidates=10,
    )

    summary = service.run_task(task.id)
    updated_task = task_repository.get_by_id(task.id)
    records = excel_service.load_candidates(summary.excel_path)

    assert summary.processed_keywords == ["算法 工程师", "推荐 系统"]
    assert summary.query_level_stats[0]["accepted_candidates"] == 1
    assert summary.query_level_stats[1]["accepted_candidates"] == 1
    assert summary.query_level_stats[1]["deduplicated_candidates"] == 1
    assert len(records) == 2
    assert [item.source_keyword for item in records] == ["算法 工程师", "推荐 系统"]
    stored_stats = __import__("json").loads(updated_task.query_level_stats_json)
    assert stored_stats[1]["deduplicated_candidates"] == 1


def test_search_task_repository_persists_execution_artifacts(tmp_path):
    manager = DatabaseManager(db_path=os.path.join(tmp_path, "test.db"))
    repository = SearchTaskRepository(manager)
    task = repository.create(
        job_history_id="job_004",
        task_name="统计持久化",
        keywords={"precise_keywords": ["算法工程师"]},
    )

    updated = repository.update_execution_artifacts(
        task.id,
        executed_queries=[{"query": "算法工程师", "priority": 1}],
        query_level_stats=[{"query": "算法工程师", "accepted_candidates": 2}],
        search_control_snapshot={"round_count": 1},
    )
    reloaded = repository.get_by_id(task.id)

    assert updated is True
    assert reloaded is not None
    assert __import__("json").loads(reloaded.executed_queries_json)[0]["query"] == "算法工程师"
    assert __import__("json").loads(reloaded.query_level_stats_json)[0]["accepted_candidates"] == 2
    assert __import__("json").loads(reloaded.search_control_snapshot_json)["round_count"] == 1


def test_run_task_applies_filters_limits_each_round_and_callbacks(tmp_path):
    def candidate(index):
        return LiepinSearchCandidate(
            name="候选人{}".format(index),
            profile_url="https://example.com/resume/{}".format(index),
        )

    search_service = FakeFilterSearchService(
        query_sequences={
            "结构 灯具": [[candidate(1), candidate(2), candidate(3)]],
            "结构 照明": [[candidate(4), candidate(5), candidate(6)]],
        }
    )
    task_repository, excel_service, service = build_service(tmp_path, search_service)
    task = task_repository.create(
        job_history_id="job_005",
        task_name="每轮限制",
        keywords={
            "filters": {"目前城市": ["深圳", "广州"]},
            "per_round_limit": 2,
            "executable_rounds": [
                {"query": "结构 灯具", "label": "第一轮", "priority": 1},
                {"query": "结构 照明", "label": "第二轮", "priority": 2},
            ],
        },
        max_pages=1,
        max_candidates=10,
    )
    callbacks = []

    summary = service.run_task(
        task.id,
        on_round_complete=lambda excel_path, round_index, round_info, rows, stats, task: callbacks.append(
            (round_index, round_info["query"], list(rows), stats["accepted_candidates"])
        ),
    )
    records = excel_service.load_candidates(summary.excel_path)

    assert summary.sourced_candidate_count == 4
    assert [item[0] for item in callbacks] == [1, 2]
    assert [item[3] for item in callbacks] == [2, 2]
    assert len(callbacks[0][2]) == 2
    assert search_service.search_filter_calls == [
        ("结构 灯具", {"目前城市": ["深圳", "广州"]}),
        ("结构 照明", {"目前城市": ["深圳", "广州"]}),
    ]
    assert [record.source_keyword for record in records] == [
        "结构 灯具",
        "结构 灯具",
        "结构 照明",
        "结构 照明",
    ]


def test_run_task_passes_round_match_mode_and_scope(tmp_path):
    search_service = FakeControlSearchService(
        query_sequences={
            "算法 OR 推荐": [[LiepinSearchCandidate(name="张三", profile_url="https://example.com/resume/1")]],
        }
    )
    task_repository, excel_service, service = build_service(tmp_path, search_service)
    task = task_repository.create(
        job_history_id="job_007",
        task_name="模式范围搜索",
        keywords={
            "filters": {"目前城市": ["深圳"]},
            "executable_rounds": [
                {
                    "query": "算法 OR 推荐",
                    "label": "测绘",
                    "priority": 1,
                    "match_mode": "any",
                    "scope": "目前职位",
                    "position_filter": "产品",
                    "intent": "先测绘",
                }
            ],
        },
        max_pages=1,
        max_candidates=1,
    )

    summary = service.run_task(task.id)

    assert summary.sourced_candidate_count == 1
    assert search_service.search_control_calls == [
        ("算法 OR 推荐", {"目前城市": ["深圳"]}, "any", "目前职位", "产品")
    ]
    assert summary.executed_rounds[0]["match_mode"] == "any"
    assert summary.query_level_stats[0]["scope"] == "目前职位"
    assert summary.query_level_stats[0]["position_filter"] == "产品"


def test_run_task_skips_empty_round_and_continues_next_query(tmp_path):
    class EmptyFirstSearchService(FakeSearchService):
        def search(self, keyword, filters=None):
            if keyword == "空关键词":
                raise LiepinSearchNoResultsError("empty")
            return super().search(keyword)

    search_service = EmptyFirstSearchService(
        query_sequences={
            "命中关键词": [[LiepinSearchCandidate(name="张三", profile_url="https://example.com/resume/1")]],
        }
    )
    task_repository, excel_service, service = build_service(tmp_path, search_service)
    task = task_repository.create(
        job_history_id="job_006",
        task_name="空轮次继续",
        keywords={
            "executable_rounds": [
                {"query": "空关键词", "label": "第一轮", "priority": 1},
                {"query": "命中关键词", "label": "第二轮", "priority": 2},
            ]
        },
        max_pages=1,
        max_candidates=10,
    )

    summary = service.run_task(task.id)
    records = excel_service.load_candidates(summary.excel_path)

    assert summary.processed_keywords == ["空关键词", "命中关键词"]
    assert summary.query_level_stats[0]["accepted_candidates"] == 0
    assert summary.query_level_stats[1]["accepted_candidates"] == 1
    assert len(records) == 1
    assert records[0].source_keyword == "命中关键词"
