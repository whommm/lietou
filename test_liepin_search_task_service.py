import os

from src.core.candidate_excel_service import CandidateExcelService
from src.core.database import DatabaseManager
from src.core.liepin_search_service import LiepinSearchCandidate
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
    def __init__(self, current_results, page_sequences=None, next_page_results=None):
        self.current_results = current_results
        self.page_sequences = list(page_sequences or [list(current_results)])
        self.next_page_results = list(next_page_results or [])
        self.browser_manager = FakeBrowserManager()
        self.extract_calls = 0
        self.open_calls = []
        self.closed_pages = []
        self.result_page = self.browser_manager.page
        self.page_index = 0
        self.next_page_calls = 0

    def extract_current_page_candidates(self):
        self.extract_calls += 1
        index = min(self.page_index, len(self.page_sequences) - 1)
        return list(self.page_sequences[index])

    def ensure_result_page(self):
        return self.result_page

    def go_to_next_result_page(self, page):
        assert page is self.result_page
        self.next_page_calls += 1
        if not self.next_page_results:
            return False
        should_advance = self.next_page_results.pop(0)
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


def test_run_task_imports_current_result_page(tmp_path):
    search_service = FakeSearchService(
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
    )
    task_repository, excel_service, service = build_service(tmp_path, search_service)
    task = task_repository.create(
        job_history_id="job_001",
        task_name="算法岗搜索",
        keywords={"precise_keywords": ["算法工程师"]},
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
    assert search_service.extract_calls == 1
    assert search_service.open_calls == [
        "https://example.com/resume/1",
        "https://example.com/resume/2",
    ]
    assert len(search_service.closed_pages) == 2
    assert updated_task is not None
    assert updated_task.status == "completed"
    assert len(records) == 2
    assert records[0].resume_text
    assert records[0].capture_status == "抓取成功"
    assert search_service.browser_manager.page.visited_urls == [
        "https://example.com/resume/1",
        "https://example.com/resume/2",
    ]


def test_run_task_keeps_going_when_one_candidate_fails(tmp_path):
    search_service = FakeSearchService(
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
        current_results=[],
        page_sequences=[
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
        ],
        next_page_results=[True, False],
    )
    task_repository, excel_service, service = build_service(tmp_path, search_service)
    task = task_repository.create(
        job_history_id="job_002",
        task_name="多页搜索",
        keywords={"precise_keywords": ["后端工程师"]},
        max_pages=3,
        max_candidates=3,
    )

    summary = service.run_task(task.id)
    records = excel_service.load_candidates(summary.excel_path)

    assert summary.pages_processed == 2
    assert summary.sourced_candidate_count == 3
    assert summary.enriched_candidate_count == 3
    assert search_service.extract_calls == 2
    assert search_service.next_page_calls == 1
    assert len(records) == 3
    assert {item.page_number for item in records} == {1, 2}
