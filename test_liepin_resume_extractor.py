from src.core.liepin_resume_extractor import LiepinResumeExtractor
from src.core.liepin_search_service import LiepinSearchCandidate


class FakeSectionLocator:
    def __init__(self, text):
        self._text = text

    @property
    def first(self):
        return self

    def is_visible(self, timeout=None):
        return bool(self._text)

    def inner_text(self, timeout=None):
        return self._text


class FakeDetailPage:
    def __init__(self, mapping):
        self.mapping = mapping

    def locator(self, selector):
        return FakeSectionLocator(self.mapping.get(selector, ""))


def test_extract_sections_reads_first_matching_selectors():
    page = FakeDetailPage(
        {
            ".resume-header": "姓名：张三\n当前职位：高级算法工程师",
            ".self-evaluation": "负责推荐系统和搜索策略优化",
            ".work-experience": "字节跳动 / 算法工程师 / 2021-至今",
            ".education-experience": "北京大学 / 计算机科学",
        }
    )
    extractor = LiepinResumeExtractor()

    sections = extractor.extract_sections(page)

    assert sections["basic_info"][0] == "姓名：张三"
    assert sections["summary"][0] == "负责推荐系统和搜索策略优化"
    assert sections["experience"][0] == "字节跳动 / 算法工程师 / 2021-至今"
    assert sections["education"][0] == "北京大学 / 计算机科学"


def test_extract_candidate_builds_normalized_resume_text():
    page = FakeDetailPage(
        {
            ".resume-header": "姓名：李四\n当前职位：产品经理",
            ".self-evaluation": "有增长产品和商业化经验",
            ".work-experience": "美团 / 产品经理 / 2020-至今",
        }
    )
    summary = LiepinSearchCandidate(
        name="李四",
        current_title="产品经理",
        current_company="美团",
        profile_url="https://example.com/3",
    )
    extractor = LiepinResumeExtractor()

    candidate = extractor.extract_candidate(page, summary)

    assert candidate.profile_url == "https://example.com/3"
    assert "【候选人基础信息】" in candidate.resume_text
    assert "【工作经历】" in candidate.resume_text
    assert candidate.resume_summary
