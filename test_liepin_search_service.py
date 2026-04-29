from src.core.liepin_search_service import (
    LiepinSearchCandidate,
    LiepinSearchNoResultsError,
    LiepinSearchService,
)


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

    def focus(self):
        self.clicked += 1

    def press(self, key):
        return None

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

    @staticmethod
    def export_debug_snapshot(reason):
        return ""


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


class FakeSearchContainerPage:
    def __init__(self, container, direct_inputs=None, ant_inputs=None, button=None):
        self._container = container
        self._direct_inputs = direct_inputs or []
        self._ant_inputs = ant_inputs or []
        self._button = button or FakeStaticLocator(visible=False)

    def locator(self, selector):
        if selector == "div.search-auto-complete-box":
            return self._container
        if selector == "input.search-component-input":
            return FakeLocatorList(self._direct_inputs)
        if selector == "input.ant-select-selection-search-input":
            return FakeLocatorList(self._ant_inputs)
        if selector == "button.search-btn":
            return self._button
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
        self.opened = 0

    def run_with_page(self, func):
        return func(self.page)

    def new_page(self):
        return self.page

    def open_search_page(self):
        self.opened += 1

    def ensure_logged_in(self):
        return None

    def get_state(self):
        return {}

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


def test_detect_search_controls_ignores_keyword_mode_input_and_picks_widest_main_input():
    service = LiepinSearchService(DummyBrowserManager())
    mode_input = FakeInputLocator(visible=True, input_type="search")
    mode_input.bounding_box = lambda: {"x": 45, "y": 142, "width": 108, "height": 42}
    main_input = FakeInputLocator(visible=True, input_type="search")
    main_input.bounding_box = lambda: {"x": 185, "y": 142, "width": 680, "height": 38}
    narrow_input = FakeInputLocator(visible=True, input_type="search")
    narrow_input.bounding_box = lambda: {"x": 118, "y": 213, "width": 266, "height": 30}
    search_button = FakeStaticLocator(
        text="搜 索",
        attributes={"bounding_box": {"x": 874, "y": 1, "width": 98, "height": 42}},
    )
    container = FakeStaticLocator(
        text="包含全部关键词 搜职位/公司/行业等（中文用空格隔开，英文用逗号隔开） 搜 索",
        children={
            "div.auto-input-wrap-v3 input.ant-select-selection-search-input": main_input,
            "input.ant-select-selection-search-input": FakeLocatorList([mode_input, main_input]),
        },
    )
    page = FakeSearchContainerPage(
        container=container,
        direct_inputs=[narrow_input],
        ant_inputs=[mode_input, main_input, narrow_input],
        button=search_button,
    )

    controls = service._detect_search_controls(page)

    assert controls.search_button is search_button
    assert controls.search_input is main_input


def test_write_keyword_verifies_input_value():
    service = LiepinSearchService(DummyBrowserManager())
    locator = FakeInputLocator()

    service._write_keyword(locator, "算法工程师")

    assert locator.input_value() == "算法工程师"


def test_apply_tag_filter_clicks_target_tag_and_waits():
    service = LiepinSearchService(DummyBrowserManager())
    target = FakeStaticLocator(text="1-3年")
    container = FakeStaticLocator(
        text="工作年限： 不限 应届生 1-3年",
        children={"label.tag-item:has-text('1-3年')": target},
    )
    page = FakeControlPage(
        {"div.search-item.sfilter-work-year": container},
        body_text="工作年限： 1-3年",
    )

    service._apply_tag_filter(page, service.FILTER_FIELD_SPECS["工作年限"], "1-3年")

    assert target.clicked == 1


def test_apply_tag_filter_maps_work_years_to_existing_tag():
    service = LiepinSearchService(DummyBrowserManager())
    target = FakeStaticLocator(text="3-5年")
    container = FakeStaticLocator(
        text="工作年限： 不限 应届生 1-3年 3-5年 5-10年 10年以上",
        children={"label.tag-item:has-text('3-5年')": target},
    )
    page = FakeControlPage(
        {"div.search-item.sfilter-work-year": container},
        body_text="工作年限： 3-5年",
    )

    service._apply_tag_filter(page, service.FILTER_FIELD_SPECS["工作年限"], "3年以上")

    assert target.clicked == 1


def test_apply_dropdown_filter_clicks_matching_option():
    service = LiepinSearchService(DummyBrowserManager())
    input_locator = FakeStaticLocator()
    option_male = FakeStaticLocator(text="男")
    options = FakeStaticLocator(children={})
    options.count = lambda: 2
    options.nth = lambda index: [FakeStaticLocator(text="不限"), option_male][index]
    dropdown = FakeStaticLocator(children={"div.ant-select-item.ant-select-item-option": options})
    container = FakeStaticLocator(
        text="性 别： 不限",
        children={"input.ant-select-selection-search-input": input_locator},
    )
    page = FakeControlPage(
        {
            "div.ant-select.ant-select-lg.h-select.sexSelectStyle.gray.ant-select-single.ant-select-show-arrow": container,
            "div.ant-select-dropdown.search-select": dropdown,
        },
        body_text="性 别： 男",
    )

    service._apply_dropdown_filter(page, service.FILTER_FIELD_SPECS["性别"], "男")

    assert container.clicked >= 1
    assert input_locator.clicked >= 1
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
    container = FakeStaticLocator(
        text="目前城市： 不限 其他",
        children={
            "label.tag-item:has-text('长沙')": FakeStaticLocator(visible=False),
            "span.btn-choose:has-text('其他')": trigger,
        },
    )
    page = FakeControlPage(
        {
            "div.search-item.sfilter-city": container,
            "div.ant-modal.city-modal": modal,
        },
        body_text="目前城市： 长沙",
    )

    service._apply_city_filter(page, service.FILTER_FIELD_SPECS["目前城市"], "长沙")

    assert trigger.clicked == 1
    assert city_input.filled == ["长沙"]
    assert suggest.clicked == 1
    assert confirm.clicked == 1


def test_apply_city_filter_waits_for_enabled_confirm_button():
    service = LiepinSearchService(DummyBrowserManager())
    trigger = FakeStaticLocator(text="其他")
    city_input = FakeStaticLocator()

    class ConfirmLocator(FakeStaticLocator):
        def __init__(self):
            super().__init__(text="确认", attributes={"disabled": "disabled", "class": "ant-btn ant-btn-primary disabled"})
            self.get_attribute_calls = 0

        def get_attribute(self, name, timeout=None):
            if name in ("disabled", "class"):
                self.get_attribute_calls += 1
                if self.get_attribute_calls >= 3:
                    if name == "disabled":
                        return None
                    return "ant-btn ant-btn-primary"
            return super().get_attribute(name, timeout=timeout)

    confirm = ConfirmLocator()

    class SuggestLocator(FakeStaticLocator):
        def click(self, timeout=None):
            super().click(timeout=timeout)

    suggest = SuggestLocator(text="湖南 · 长沙")
    modal = FakeStaticLocator(
        children={
            'span.ant-tag.ant-tag-checkable:has-text(\'长沙\')': FakeStaticLocator(visible=False),
            'input.ant-input[placeholder="搜索城市"]': city_input,
            "div.suggest-list > ul > li": suggest,
            'button:has-text("确认")': confirm,
            "button.ant-btn.ant-btn-primary": FakeStaticLocator(text="确 定", attributes={"disabled": "disabled"}),
        }
    )
    container = FakeStaticLocator(
        text="目前城市： 不限 其他",
        children={
            "label.tag-item:has-text('长沙')": FakeStaticLocator(visible=False),
            "span.btn-choose:has-text('其他')": trigger,
        },
    )
    page = FakeControlPage(
        {
            "div.search-item.sfilter-city": container,
            "div.ant-modal.city-modal": modal,
        },
        body_text="目前城市： 长沙",
    )

    service._apply_city_filter(page, service.FILTER_FIELD_SPECS["目前城市"], "长沙")

    assert trigger.clicked == 1
    assert city_input.filled == ["长沙"]
    assert suggest.clicked == 1
    assert confirm.clicked == 1


def test_apply_city_filter_accepts_multiple_cities():
    service = LiepinSearchService(DummyBrowserManager())
    trigger = FakeStaticLocator(text="其他")
    confirm = FakeStaticLocator(text="确认")
    selected = []

    class CityModal(FakeStaticLocator):
        def locator(self, selector):
            if selector.startswith("span.ant-tag.ant-tag-checkable"):
                city = selector.split("has-text('", 1)[1].split("')", 1)[0]
                item = FakeStaticLocator(text=city)
                item.click = lambda timeout=None, city=city: selected.append(city)
                return item
            return super().locator(selector)

    modal = CityModal(children={
        'button:has-text("确认")': confirm,
        "button.ant-btn.ant-btn-primary": FakeStaticLocator(text="确 定", attributes={"disabled": "disabled"}),
    })
    container = FakeStaticLocator(
        text="目前城市： 不限 其他",
        children={"span.btn-choose:has-text('其他')": trigger},
    )
    page = FakeControlPage(
        {
            "div.search-item.sfilter-city": container,
            "div.ant-modal.city-modal": modal,
        },
        body_text="目前城市： 深圳 广州",
    )

    service._apply_city_filter(page, service.FILTER_FIELD_SPECS["目前城市"], ["深圳", "广州"])

    assert trigger.clicked == 1
    assert selected == ["深圳", "广州"]
    assert confirm.clicked == 1


def test_apply_city_filter_uses_title_to_choose_expected_city_row():
    service = LiepinSearchService(DummyBrowserManager())
    current_trigger = FakeStaticLocator(text="目前其他")
    expected_trigger = FakeStaticLocator(text="期望其他")
    confirm = FakeStaticLocator(text="确认")
    modal = FakeStaticLocator(
        children={
            "span.ant-tag.ant-tag-checkable:has-text('南京')": FakeStaticLocator(text="南京"),
            'button:has-text("确认")': confirm,
            "button.ant-btn.ant-btn-primary": confirm,
        }
    )
    current = FakeStaticLocator(
        text="目前城市： 不限 其他",
        children={"span.btn-choose:has-text('其他')": current_trigger},
    )
    expected = FakeStaticLocator(
        text="期望城市： 不限 其他",
        children={"span.btn-choose:has-text('其他')": expected_trigger},
    )
    page = FakeControlPage(
        {
            "div.search-item.sfilter-city": FakeLocatorList([current, expected]),
            "div.ant-modal.city-modal": modal,
        },
        body_text="期望城市： 南京",
    )

    service._apply_city_filter(page, service.FILTER_FIELD_SPECS["期望城市"], "南京")

    assert current_trigger.clicked == 0
    assert expected_trigger.clicked == 1
    assert confirm.clicked == 1


def test_search_applies_filters_before_extracting_candidates():
    page = FakeControlPage({}, body_text="工作年限： 3-5年")
    browser_manager = BrowserManagerWithRun(page)
    service = LiepinSearchService(browser_manager)
    service._execute_search = lambda page, keyword: setattr(service, "executed_keyword", keyword)
    service._apply_filters_on_page = lambda page, filters: setattr(service, "applied_filters", filters)
    service.extract_candidates_from_page = lambda page: [LiepinSearchCandidate(name="张三")]

    candidates = service.search("结构 灯具", filters={"工作年限": "3-5年"})

    assert service.executed_keyword == "结构 灯具"
    assert service.applied_filters == {"工作年限": "3-5年"}
    assert candidates[0].name == "张三"


def test_apply_filters_on_page_skips_unsupported_live_value():
    page = FakeControlPage({}, body_text="")
    service = LiepinSearchService(DummyBrowserManager())
    calls = []

    def fake_apply(page, title, value):
        calls.append((title, value))
        raise __import__("src.core.liepin_search_service", fromlist=["LiepinSearchPageChangedError"]).LiepinSearchPageChangedError("bad option")

    service._apply_one_filter = fake_apply

    service._apply_filters_on_page(page, {"工作年限": "3年以上"})

    assert calls == [("工作年限", "3年以上")]


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


def test_wait_for_results_accepts_dom_fallback_candidates(monkeypatch):
    service = LiepinSearchService(DummyBrowserManager())

    class EmptyLocator:
        @property
        def first(self):
            return self

        def wait_for(self, state=None, timeout=None):
            raise RuntimeError("no selector match")

        def count(self):
            return 0

    class ResultPage:
        def locator(self, selector):
            return EmptyLocator()

        def wait_for_timeout(self, timeout):
            return None

    monkeypatch.setattr(service, "_is_loading", lambda page: False)
    monkeypatch.setattr(
        service,
        "_extract_candidates_with_dom_fallback",
        lambda page: [LiepinSearchCandidate(name="张三")],
    )

    service._wait_for_results(ResultPage())


def test_wait_for_results_returns_quickly_when_any_selector_is_visible():
    service = LiepinSearchService(DummyBrowserManager())

    class InvisibleLocator:
        @property
        def first(self):
            return self

        def count(self):
            return 0

        def is_visible(self, timeout=None):
            return False

    class VisibleLocator(InvisibleLocator):
        def count(self):
            return 3

        def is_visible(self, timeout=None):
            return True

    class ResultPage:
        def locator(self, selector):
            if selector == service.RESULT_CARD_SELECTORS[0]:
                return VisibleLocator()
            return InvisibleLocator()

        def wait_for_timeout(self, timeout):
            raise AssertionError("should not enter slow polling path")

    service._wait_for_results(ResultPage())


def test_wait_for_results_accepts_result_page_heuristics_without_card_selector():
    service = LiepinSearchService(DummyBrowserManager())

    class InvisibleLocator:
        @property
        def first(self):
            return self

        def count(self):
            return 0

        def is_visible(self, timeout=None):
            return False

    class VisibleLocator(InvisibleLocator):
        def count(self):
            return 1

        def is_visible(self, timeout=None):
            return True

    class ResultPage:
        def locator(self, selector):
            if selector == 'input[name="res_id_encode"]':
                return VisibleLocator()
            return InvisibleLocator()

        def wait_for_timeout(self, timeout):
            raise AssertionError("should not wait once result heuristics match")

    service._wait_for_results(ResultPage())


def test_wait_for_results_raises_no_results_error_for_empty_page():
    service = LiepinSearchService(DummyBrowserManager())

    class EmptyLocator:
        @property
        def first(self):
            return self

        def count(self):
            return 0

        def is_visible(self, timeout=None):
            return False

        def inner_text(self, timeout=None):
            return "没找到相关匹配项"

    class ResultPage:
        def locator(self, selector):
            return EmptyLocator()

        def wait_for_timeout(self, timeout):
            return None

    try:
        service._wait_for_results(ResultPage())
        raised = None
    except Exception as exc:
        raised = exc

    assert isinstance(raised, LiepinSearchNoResultsError)


def test_page_looks_empty_when_only_batch_view_is_present():
    service = LiepinSearchService(DummyBrowserManager())

    class EmptyLocator:
        def __init__(self, count=0, text=""):
            self._count = count
            self._text = text

        @property
        def first(self):
            return self

        def count(self):
            return self._count

        def is_visible(self, timeout=None):
            return self._count > 0

        def inner_text(self, timeout=None):
            return self._text

    class ResultPage:
        def locator(self, selector):
            if selector == "body":
                return EmptyLocator(text="批量查看")
            if selector == 'button:has-text("批量查看")':
                return EmptyLocator(count=1)
            return EmptyLocator(count=0)

    assert service._page_looks_empty(ResultPage()) is True


def test_with_debug_snapshot_preserves_no_results_error(monkeypatch):
    service = LiepinSearchService(DummyBrowserManager())
    monkeypatch.setattr(service.browser_manager, "export_debug_snapshot", lambda reason: "D:/debug.txt")

    try:
        service._with_debug_snapshot("search_keyword_test", lambda: (_ for _ in ()).throw(LiepinSearchNoResultsError("empty")))
        raised = None
    except Exception as exc:
        raised = exc

    assert isinstance(raised, LiepinSearchNoResultsError)
    assert "D:/debug.txt" in str(raised)


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
