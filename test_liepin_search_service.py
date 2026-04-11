from src.core.liepin_search_service import LiepinSearchCandidate, LiepinSearchService


class FakeCard:
    def __init__(self, text, href):
        self._text = text
        self._href = href

    def inner_text(self, timeout=None):
        return self._text

    def locator(self, selector):
        return FakeLinkLocator(self._href)


class FakeLinkLocator:
    def __init__(self, href):
        self._href = href

    @property
    def first(self):
        return self

    def get_attribute(self, name, timeout=None):
        if name == "href":
            return self._href
        return None


class FakePage:
    pass


class FakeEvaluatePage:
    def __init__(self, rows):
        self.rows = rows

    def evaluate(self, script):
        return self.rows


class FakeBrowserPage:
    def __init__(self, url="https://example.com/detail"):
        self.url = url
        self.waited = []
        self.closed = False
        self.brought_to_front = 0

    def wait_for_load_state(self, state, timeout=None):
        self.waited.append((state, timeout))

    def close(self):
        self.closed = True

    def bring_to_front(self):
        self.brought_to_front += 1


class FakeContext:
    def __init__(self, pages):
        self.pages = pages


class FakeClickableResultPage:
    def __init__(self, detail_page):
        self.detail_page = detail_page
        self.context = FakeContext([self])
        self.clicked_index = None

    def evaluate(self, script, result_index):
        self.clicked_index = result_index
        self.context.pages.append(self.detail_page)
        return True

    def wait_for_timeout(self, timeout):
        return None


class DummyBrowserManager:
    def open_search_page(self):
        return None

    def ensure_logged_in(self):
        return None

    def ensure_page(self):
        return FakePage()

    def new_page(self):
        return FakePage()

    @staticmethod
    def _pick_best_page(pages, current_page=None):
        return pages[-1] if pages else current_page

    @staticmethod
    def set_active_page(page):
        pass


class FakeInputLocator:
    def __init__(self, visible=True, disabled=None, readonly=None, input_type="text"):
        self._visible = visible
        self._disabled = disabled
        self._readonly = readonly
        self._input_type = input_type
        self._value = ""

    def is_visible(self, timeout=None):
        return self._visible

    def get_attribute(self, name):
        mapping = {
            "disabled": self._disabled,
            "readonly": self._readonly,
            "type": self._input_type,
            "value": self._value,
        }
        return mapping.get(name)

    def click(self, timeout=None):
        return None

    def fill(self, value):
        self._value = value

    def press(self, key):
        if key == "Backspace":
            self._value = ""

    def type(self, value, delay=None):
        self._value = value

    def input_value(self, timeout=None):
        return self._value


class FakeLocatorList:
    def __init__(self, items):
        self._items = items

    def count(self):
        return len(self._items)

    def nth(self, index):
        return self._items[index]


class FakeSearchInputPage:
    def __init__(self, items):
        self._items = items

    def locator(self, selector):
        if selector == "input.search-component-input":
            return FakeLocatorList(self._items)
        raise RuntimeError("unexpected selector")


class SearchServiceStub(LiepinSearchService):
    def __init__(self, cards):
        super().__init__(DummyBrowserManager())
        self._cards = cards

    def _locate_result_cards(self, page):
        return self._cards, "test-selector"


class BrowserManagerWithRun:
    def __init__(self, page):
        self.page = page

    def run_with_page(self, func):
        return func(self.page)

    def new_page(self):
        return self.page

    def export_debug_snapshot(self, reason):
        return ""


def test_extract_candidates_from_page_maps_card_lines():
    service = SearchServiceStub(
        [
            FakeCard(
                "张三\n高级算法工程师\n字节跳动\n北京\n5年经验",
                "https://example.com/resume/1",
            )
        ]
    )

    candidates = service.extract_candidates_from_page(FakePage())

    assert len(candidates) == 1
    assert candidates[0].name == "张三"
    assert candidates[0].current_title == "高级算法工程师"
    assert candidates[0].current_company == "字节跳动"
    assert candidates[0].profile_url == "https://example.com/resume/1"


def test_extract_candidates_skips_broken_cards():
    class BrokenCard(FakeCard):
        def inner_text(self, timeout=None):
            raise RuntimeError("bad card")

    service = SearchServiceStub(
        [BrokenCard("", ""), FakeCard("李四\n产品经理\n美团", "https://example.com/2")]
    )

    candidates = service.extract_candidates_from_page(FakePage())

    assert len(candidates) == 1
    assert candidates[0].name == "李四"


def test_find_primary_search_input_prefers_editable_search_component_input():
    service = LiepinSearchService(DummyBrowserManager())
    page = FakeSearchInputPage(
        [
            FakeInputLocator(visible=True, disabled="disabled"),
            FakeInputLocator(visible=True, input_type="text"),
        ]
    )

    locator = service._find_primary_search_input(page)

    assert locator is page._items[1]


def test_write_keyword_verifies_input_value():
    service = LiepinSearchService(DummyBrowserManager())
    locator = FakeInputLocator()

    service._write_keyword(locator, "算法工程师")

    assert locator.input_value() == "算法工程师"


def test_extract_current_page_candidates_uses_existing_page():
    page = FakePage()
    browser_manager = BrowserManagerWithRun(page)
    service = SearchServiceStub(
        [
            FakeCard(
                "张三\n高级算法工程师\n字节跳动",
                "https://example.com/resume/1",
            )
        ]
    )
    service.browser_manager = browser_manager

    candidates = service.extract_current_page_candidates()

    assert len(candidates) == 1
    assert candidates[0].profile_url == "https://example.com/resume/1"


def test_extract_candidates_from_page_falls_back_to_dom_rows():
    service = LiepinSearchService(DummyBrowserManager())
    page = FakeEvaluatePage(
        [
            {
                "href": "https://example.com/resume/1",
                "lines": ["张三", "高级算法工程师", "字节跳动", "推荐系统负责人"],
            },
            {
                "href": "https://example.com/resume/2",
                "lines": ["李四", "算法专家", "百度", "搜索排序"],
            },
        ]
    )

    candidates = service.extract_candidates_from_page(page)

    assert len(candidates) == 2
    assert candidates[0].name == "张三"
    assert candidates[0].current_title == "高级算法工程师"
    assert candidates[1].profile_url == "https://example.com/resume/2"
    assert candidates[0].result_index == 0
    assert candidates[1].result_index == 1


def test_open_candidate_detail_switches_to_new_page_when_no_href():
    service = LiepinSearchService(DummyBrowserManager())
    detail_page = FakeBrowserPage(url="https://h.liepin.com/resume/detail/123")
    page = FakeClickableResultPage(detail_page)
    candidate = LiepinSearchCandidate(name="张三", result_index=0)

    opened_page = service.open_candidate_detail(page, candidate)

    assert page.clicked_index == 0
    assert opened_page is detail_page
    assert candidate.profile_url == "https://h.liepin.com/resume/detail/123"
    assert detail_page.waited == [("domcontentloaded", 10000)]


def test_close_detail_page_restores_result_page():
    service = LiepinSearchService(DummyBrowserManager())
    result_page = FakeBrowserPage(
        url="https://h.liepin.com/search/getConditionItem#session"
    )
    detail_page = FakeBrowserPage(url="https://h.liepin.com/resume/detail/123")

    service.close_detail_page(detail_page, result_page)

    assert detail_page.closed is True
    assert result_page.brought_to_front == 1
