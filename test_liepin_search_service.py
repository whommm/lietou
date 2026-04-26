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


class FakeStaticLocator:
    def __init__(self, text="", visible=True, attributes=None, children=None):
        self._text = text
        self._visible = visible
        self._attributes = attributes or {}
        self._children = children or {}
        self.clicked = 0
        self.filled = []
        self.waited = []

    @property
    def first(self):
        return self

    def locator(self, selector):
        child = self._children.get(selector)
        if child is None:
            child = FakeStaticLocator(visible=False)
        return child

    def is_visible(self, timeout=None):
        return self._visible

    def wait_for(self, state=None, timeout=None):
        self.waited.append((state, timeout))
        return None

    def click(self, timeout=None):
        self.clicked += 1

    def fill(self, value):
        self.filled.append(value)

    def inner_text(self, timeout=None):
        return self._text

    def get_attribute(self, name, timeout=None):
        return self._attributes.get(name)

    def count(self):
        return 1 if self._visible else 0

    def nth(self, index):
        if index != 0:
            raise IndexError(index)
        return self

    def bounding_box(self):
        return self._attributes.get("bounding_box")


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

    @property
    def first(self):
        return self


class FakeLocatorList:
    def __init__(self, items):
        self._items = items

    def count(self):
        return len(self._items)

    def nth(self, index):
        return self._items[index]

    @property
    def first(self):
        return self._items[0] if self._items else FakeStaticLocator(visible=False)


class FakeSearchInputPage:
    def __init__(self, items):
        self._items = items

    def locator(self, selector):
        if selector == "input.search-component-input":
            return FakeLocatorList(self._items)
        return FakeLocatorList([])


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


class FakeControlPage:
    def __init__(self, mapping, body_text=""):
        self._mapping = mapping
        self._body_text = body_text
        self.keyboard = self
        self.pressed = []
        self.waits = []

    def locator(self, selector):
        if selector == "body":
            return FakeStaticLocator(text=self._body_text)
        item = self._mapping.get(selector)
        if item is None:
            return FakeStaticLocator(visible=False)
        return item

    def wait_for_timeout(self, timeout):
        self.waits.append(timeout)

    def press(self, key):
        self.pressed.append(key)


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


def test_detect_search_controls_prefers_main_container_input_and_search_button():
    service = LiepinSearchService(DummyBrowserManager())
    search_input = FakeInputLocator()
    search_input._visible = True
    search_input.bounding_box = lambda: {"x": 180, "y": 2, "width": 680, "height": 38}
    search_button = FakeStaticLocator(
        text="搜 索",
        attributes={"bounding_box": {"x": 874, "y": 1, "width": 98, "height": 42}},
    )
    page = FakeControlPage(
        {
            "button.search-btn": search_button,
            "div.search-auto-complete-box": FakeStaticLocator(
                children={"input.ant-select-selection-search-input": search_input}
            ),
        }
    )

    controls = service._detect_search_controls(page)

    assert controls.search_button is search_button
    assert controls.search_input is search_input


def test_write_keyword_verifies_input_value():
    service = LiepinSearchService(DummyBrowserManager())
    locator = FakeInputLocator()

    service._write_keyword(locator, "算法工程师")

    assert locator.input_value() == "算法工程师"


def test_apply_tag_filter_clicks_target_tag_and_waits():
    service = LiepinSearchService(DummyBrowserManager())
    target = FakeStaticLocator(text="1-3年")
    page = FakeControlPage(
        {"div.search-item.sfilter-work-year label.tag-item:has-text('1-3年')": target},
        body_text="工作年限： 1-3年",
    )

    service._apply_tag_filter(page, service.FILTER_FIELD_SPECS["工作年限"], "1-3年")

    assert target.clicked == 1


def test_apply_dropdown_filter_clicks_matching_option():
    service = LiepinSearchService(DummyBrowserManager())
    input_locator = FakeStaticLocator()
    option_male = FakeStaticLocator(text="男")
    options = FakeStaticLocator(children={})
    options.count = lambda: 2
    options.nth = lambda index: [FakeStaticLocator(text="不限"), option_male][index]
    dropdown = FakeStaticLocator(children={"div.ant-select-item.ant-select-item-option": options})
    container = FakeStaticLocator(children={"input.ant-select-selection-search-input": input_locator})
    page = FakeControlPage(
        {
            "div.ant-select.ant-select-lg.h-select.sexSelectStyle.gray.ant-select-single.ant-select-show-arrow": container,
            "div.ant-select-dropdown.search-select.ant-select-dropdown-placement-bottomLeft": dropdown,
        },
        body_text="性 别： 男",
    )

    service._apply_dropdown_filter(page, service.FILTER_FIELD_SPECS["性别"], "男")

    assert input_locator.clicked == 1
    assert option_male.clicked == 1


def test_apply_city_filter_uses_modal_search_and_confirm():
    service = LiepinSearchService(DummyBrowserManager())
    trigger = FakeStaticLocator(text="其他")
    city_input = FakeStaticLocator()
    suggest = FakeStaticLocator(text="湖南 · 长沙")
    confirm = FakeStaticLocator(text="确认")
    modal = FakeStaticLocator(
        children={
            'span.ant-tag.ant-tag-checkable:has-text(\'长沙\')': FakeStaticLocator(visible=False),
            'input.ant-input[placeholder="搜索城市"]': city_input,
            "div.suggest-list > ul > li": suggest,
            "button.ant-btn.ant-btn-primary": confirm,
        }
    )
    page = FakeControlPage(
        {
            "div.search-item.sfilter-city label.tag-item:has-text('长沙')": FakeStaticLocator(visible=False),
            "div.search-item.sfilter-city span.btn-choose:has-text('其他')": trigger,
            "div.ant-modal.city-modal": modal,
        },
        body_text="目前城市： 长沙",
    )

    service._apply_city_filter(page, service.FILTER_FIELD_SPECS["目前城市"], "长沙")

    assert trigger.clicked == 1
    assert city_input.filled == ["长沙"]
    assert suggest.clicked == 1
    assert confirm.clicked == 1


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
