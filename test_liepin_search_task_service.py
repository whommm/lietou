import os

from src.core.candidate_repository import CandidateRepository
from src.core.database import DatabaseManager
from src.core.liepin_resume_extractor import LiepinResumeExtractor
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
    def __init__(self, current_results):
        self.current_results = current_results
        self.browser_manager = FakeBrowserManager()
        self.extract_calls = 0
        self.open_calls = []
        self.closed_pages = []
        self.result_page = self.browser_manager.page

    def extract_current_page_candidates(self):
        self.extract_calls += 1
        return list(self.current_results)

    def ensure_result_page(self):
        return self.result_page

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


def test_run_task_imports_current_result_page(tmp_path):
    manager = DatabaseManager(db_path=os.path.join(tmp_path, "test.db"))
    task_repository = SearchTaskRepository(manager)
    candidate_repository = CandidateRepository(manager)
    task = task_repository.create(
        job_history_id="job_001",
        task_name="算法岗搜索",
        keywords={"precise_keywords": ["算法工程师"]},
        max_candidates=2,
    )
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
    service = LiepinSearchTaskService(
        task_repository=task_repository,
        candidate_repository=candidate_repository,
        search_service=search_service,
        resume_extractor=FakeResumeExtractor(),
    )

    summary = service.run_task(task.id)
    updated_task = task_repository.get_by_id(task.id)
    linked_candidates = candidate_repository.list_by_search_task(task.id)

    assert summary.candidate_count == 2
    assert summary.processed_keywords == ["算法工程师"]
    assert search_service.extract_calls == 1
    assert search_service.open_calls == [
        "https://example.com/resume/1",
        "https://example.com/resume/2",
    ]
    assert len(search_service.closed_pages) == 2
    assert updated_task is not None
    assert updated_task.status == "completed"
    assert len(linked_candidates) == 2
    assert linked_candidates[0].resume_text
    assert search_service.browser_manager.page.visited_urls == [
        "https://example.com/resume/1",
        "https://example.com/resume/2",
    ]


def test_run_task_keeps_going_when_one_candidate_fails(tmp_path):
    manager = DatabaseManager(db_path=os.path.join(tmp_path, "test.db"))
    task_repository = SearchTaskRepository(manager)
    candidate_repository = CandidateRepository(manager)
    task = task_repository.create(
        job_history_id="job_001",
        task_name="产品岗搜索",
        keywords={"precise_keywords": ["产品经理"]},
        max_candidates=5,
    )
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
    service = LiepinSearchTaskService(
        task_repository=task_repository,
        candidate_repository=candidate_repository,
        search_service=search_service,
        resume_extractor=FakeResumeExtractor(
            broken_urls={"https://example.com/resume/bad"}
        ),
    )

    summary = service.run_task(task.id)
    updated_task = task_repository.get_by_id(task.id)
    linked_candidates = candidate_repository.list_by_search_task(task.id)

    assert summary.candidate_count == 1
    assert "https://example.com/resume/bad" in summary.failed_candidates
    assert summary.processed_keywords == ["产品经理"]
    assert updated_task is not None
    assert updated_task.status == "completed"
    assert len(linked_candidates) == 1
    assert linked_candidates[0].name == "赵六"
