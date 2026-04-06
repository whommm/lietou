"""Liepin search execution and result list extraction."""

from dataclasses import dataclass
from typing import Callable
from typing import List

from .liepin_browser import LiepinBrowserManager, LiepinLoginRequiredError

try:
    from playwright.sync_api import Error, Page
except ImportError:  # pragma: no cover
    Error = Exception
    Page = None


class LiepinSearchError(Exception):
    """Base error for Liepin search execution."""


class LiepinSearchPageChangedError(LiepinSearchError):
    """Raised when the search page no longer matches expected selectors."""


@dataclass
class LiepinSearchCandidate:
    """Candidate summary captured from the result list page."""

    name: str = ""
    current_title: str = ""
    current_company: str = ""
    city: str = ""
    work_years: str = ""
    education: str = ""
    profile_url: str = ""
    summary: str = ""
    result_index: int = -1


class LiepinSearchService:
    """Execute keyword searches on Liepin and parse result cards.

    The selectors are intentionally centralized so later site updates only need
    to be fixed in one place.
    """

    SEARCH_INPUT_SELECTORS = [
        "input.search-component-input",
        ".search-component-input input",
        'input[placeholder*="搜索"]',
        'input[placeholder*="职位"]',
        'input[placeholder*="关键词"]',
        'input[type="text"]',
    ]
    SEARCH_BUTTON_SELECTORS = [
        "button.search-btn",
        'button:has-text("搜索")',
        'button:has-text("找人")',
        'button[type="submit"]',
    ]
    RESULT_CARD_SELECTORS = [
        '[data-selector="jobseeker-item"]',
        ".sojob-item-main",
        ".candidate-card",
        ".sojob-list li",
    ]
    PROFILE_LINK_SELECTORS = [
        'a[href*="/resume/"]',
        'a[href*="/search/detail"]',
        'a[href*="/candidates/"]',
        "a",
    ]

    def __init__(self, browser_manager: LiepinBrowserManager):
        self.browser_manager = browser_manager

    def _with_debug_snapshot(
        self, reason: str, func: Callable[[], List[LiepinSearchCandidate]]
    ):
        """Run a search step and export a page snapshot on failure."""
        try:
            return func()
        except Exception as exc:
            snapshot_path = ""
            try:
                snapshot_path = self.browser_manager.export_debug_snapshot(reason)
            except Exception:
                snapshot_path = ""

            if snapshot_path:
                raise LiepinSearchError(
                    "{}\n已导出页面结构诊断文件: {}".format(str(exc), snapshot_path)
                )
            raise

    def open_search_page(self):
        """Open the Liepin search page and require a logged-in session."""
        self.browser_manager.open_search_page()
        self.browser_manager.ensure_logged_in()
        return self.browser_manager.get_state()

    def search(self, keyword: str) -> List[LiepinSearchCandidate]:
        """Run a keyword search and return the first page of result summaries."""
        if not keyword.strip():
            raise LiepinSearchError("搜索关键词不能为空")

        self.open_search_page()

        def _run(page):
            self._execute_search(page, keyword.strip())
            return self.extract_candidates_from_page(page)

        return self._with_debug_snapshot(
            "search_keyword_{}".format(keyword.strip()),
            lambda: self.browser_manager.run_with_page(_run),
        )

    def extract_current_page_candidates(self) -> List[LiepinSearchCandidate]:
        """Parse candidate summaries from the current page without searching."""

        def _run(page):
            return self.extract_candidates_from_page(page)

        return self._with_debug_snapshot(
            "current_result_page",
            lambda: self.browser_manager.run_with_page(_run),
        )

    def ensure_result_page(self):
        """Return the active result page and validate it still looks like search."""

        def _run(page):
            url = (page.url or "").lower()
            if not self.browser_manager._is_search_page_url(url):
                raise LiepinSearchPageChangedError("当前活动页不是搜索结果页")
            return page

        return self.browser_manager.run_with_page(_run)

    def _execute_search(self, page: Page, keyword: str) -> None:
        """Fill the most likely search field and submit the search.

        The live page contains more than one `.search-component-input`, so this
        method tries visible editable candidates one by one and only accepts a
        candidate when the page actually reaches the result state.
        """
        inputs = self._find_candidate_search_inputs(page)
        if not inputs:
            raise LiepinSearchPageChangedError("未找到猎聘搜索输入框，请检查页面结构")

        last_error = None
        for input_locator in inputs:
            try:
                self._clear_search_inputs(page)
                self._write_keyword(input_locator, keyword)
                self._submit_search(page)
                self._wait_for_results(page)
                return
            except Exception as exc:
                last_error = exc
                continue

        if last_error is not None:
            raise last_error
        raise LiepinSearchPageChangedError("搜索执行失败，未找到有效的关键词输入框")

    def extract_candidates_from_page(self, page: Page) -> List[LiepinSearchCandidate]:
        """Parse summary cards from the current result page."""
        cards = self._locate_result_cards(page)
        if not cards:
            return self._extract_candidates_with_dom_fallback(page)

        candidates = []
        for card in cards:
            try:
                profile_url = self._extract_profile_url(card)
                text = card.inner_text(timeout=2000).strip()
            except Exception:
                continue

            lines = [line.strip() for line in text.splitlines() if line.strip()]
            candidate = LiepinSearchCandidate(
                name=lines[0] if lines else "",
                current_title=lines[1] if len(lines) > 1 else "",
                current_company=lines[2] if len(lines) > 2 else "",
                summary="\n".join(lines[:8]),
                profile_url=profile_url,
                result_index=len(candidates),
            )
            candidates.append(candidate)
        return candidates

    def _extract_candidates_with_dom_fallback(
        self, page: Page
    ) -> List[LiepinSearchCandidate]:
        """Heuristically extract result rows from the live result page DOM."""
        try:
            rows = page.evaluate(
                r"""
                () => {
                  const cleanText = (text) => (text || '')
                    .replace(/\u00a0/g, ' ')
                    .split(/\n+/)
                    .map((line) => line.replace(/\s+/g, ' ').trim())
                    .filter(Boolean);

                  const hrefScore = (href) => {
                    const value = (href || '').toLowerCase();
                    if (!value || value.startsWith('javascript:') || value === '#') {
                      return -1;
                    }
                    if (value.includes('/resume/') || value.includes('res_id_encode=')) {
                      return 5;
                    }
                    if (value.includes('/search/detail') || value.includes('/detail/')) {
                      return 4;
                    }
                    if (value.includes('h.liepin.com')) {
                      return 2;
                    }
                    return 1;
                  };

                  const pickProfileHref = (element) => {
                    const anchors = Array.from(element.querySelectorAll('a[href]'));
                    anchors.sort((left, right) => hrefScore(right.getAttribute('href')) - hrefScore(left.getAttribute('href')));
                    return anchors.length ? (anchors[0].getAttribute('href') || '') : '';
                  };

                  const actionButtons = Array.from(document.querySelectorAll('button')).filter((button) => {
                    const text = (button.innerText || button.textContent || '').replace(/\s+/g, ' ').trim();
                    return text.includes('立即沟通');
                  });

                  const containers = [];
                  const seen = new Set();

                  for (const button of actionButtons) {
                    let current = button;
                    let chosen = null;
                    while (current && current !== document.body) {
                      const rect = current.getBoundingClientRect ? current.getBoundingClientRect() : null;
                      const text = (current.innerText || current.textContent || '').replace(/\s+/g, ' ').trim();
                      const checkbox = current.querySelector('input[name="res_id_encode"]');
                      if (checkbox && rect && rect.height >= 100 && rect.width >= 700 && text.length >= 20) {
                        chosen = current;
                        break;
                      }
                      current = current.parentElement;
                    }

                    if (!chosen) {
                      continue;
                    }

                    const key = chosen.innerText || chosen.textContent || '';
                    if (!key || seen.has(key)) {
                      continue;
                    }
                    seen.add(key);

                    const rect = chosen.getBoundingClientRect ? chosen.getBoundingClientRect() : { top: 0 };
                    containers.push({
                      index: containers.length,
                      top: rect.top || 0,
                      href: pickProfileHref(chosen),
                      lines: cleanText(chosen.innerText || chosen.textContent || ''),
                    });
                  }

                  containers.sort((left, right) => left.top - right.top);
                  return containers;
                }
                """
            )
        except Exception as exc:
            raise LiepinSearchPageChangedError(
                "未找到候选人结果卡片，且结果页启发式提取失败: {}".format(str(exc))
            )

        candidates = []
        for row in rows or []:
            lines = row.get("lines") or []
            if not lines:
                continue

            candidates.append(
                LiepinSearchCandidate(
                    name=lines[0] if lines else "",
                    current_title=lines[1] if len(lines) > 1 else "",
                    current_company=lines[2] if len(lines) > 2 else "",
                    summary="\n".join(lines[:8]),
                    profile_url=row.get("href") or "",
                    result_index=row.get("index", len(candidates)),
                )
            )

        if candidates:
            return candidates
        raise LiepinSearchPageChangedError("未找到候选人结果卡片")

    def open_candidate_detail(self, page: Page, candidate: LiepinSearchCandidate):
        """Open one candidate detail page and return the active detail page."""
        if candidate.profile_url:
            page.goto(candidate.profile_url, wait_until="domcontentloaded")
            return page

        if candidate.result_index < 0:
            raise LiepinSearchPageChangedError("候选人缺少详情入口，无法打开完整简历")

        try:
            before_pages = list(page.context.pages)
        except Exception:
            before_pages = [page]

        try:
            clicked = page.evaluate(
                r"""
                (targetIndex) => {
                  const buttons = Array.from(document.querySelectorAll('button')).filter((button) => {
                    const text = (button.innerText || button.textContent || '').replace(/\s+/g, ' ').trim();
                    return text.includes('立即沟通');
                  });

                  const containers = [];
                  const seen = new Set();
                  for (const button of buttons) {
                    let current = button;
                    let chosen = null;
                    while (current && current !== document.body) {
                      const rect = current.getBoundingClientRect ? current.getBoundingClientRect() : null;
                      const text = (current.innerText || current.textContent || '').replace(/\s+/g, ' ').trim();
                      const checkbox = current.querySelector('input[name="res_id_encode"]');
                      if (checkbox && rect && rect.height >= 100 && rect.width >= 700 && text.length >= 20) {
                        chosen = current;
                        break;
                      }
                      current = current.parentElement;
                    }
                    if (!chosen) {
                      continue;
                    }
                    const key = chosen.innerText || chosen.textContent || '';
                    if (!key || seen.has(key)) {
                      continue;
                    }
                    seen.add(key);
                    containers.push(chosen);
                  }

                  const container = containers[targetIndex];
                  if (!container) {
                    return false;
                  }

                  const clickable =
                    container.querySelector('a[target="_blank"][href]') ||
                    container.querySelector('a[href]') ||
                    container.querySelector('[role="link"]') ||
                    container;

                  if (!(clickable instanceof HTMLElement)) {
                    return false;
                  }
                  clickable.scrollIntoView({ block: 'center' });
                  clickable.click();
                  return true;
                }
                """,
                candidate.result_index,
            )
        except Exception as exc:
            raise LiepinSearchPageChangedError(
                "候选人缺少详情链接，且点击结果行失败: {}".format(str(exc))
            )

        if not clicked:
            raise LiepinSearchPageChangedError("候选人缺少详情入口，无法打开完整简历")

        try:
            page.wait_for_timeout(1200)
        except Exception:
            pass

        detail_page = page
        try:
            current_pages = list(page.context.pages)
            new_pages = [item for item in current_pages if item not in before_pages]
            if new_pages:
                detail_page = self.browser_manager._pick_best_page(new_pages, page)
            else:
                detail_page = self.browser_manager._pick_best_page(current_pages, page)
        except Exception:
            detail_page = page

        detail_page.wait_for_load_state("domcontentloaded", timeout=10000)
        candidate.profile_url = detail_page.url or candidate.profile_url
        return detail_page

    def close_detail_page(self, detail_page: Page, result_page: Page) -> Page:
        """Close transient detail tabs and return focus to the result page."""
        if detail_page is not None and detail_page is not result_page:
            try:
                detail_page.close()
            except Exception:
                pass
        try:
            result_page.bring_to_front()
        except Exception:
            pass
        return result_page

    def _fill_search_input(self, page: Page, keyword: str) -> None:
        input_locator = self._find_primary_search_input(page)
        if input_locator is None:
            raise LiepinSearchPageChangedError("未找到猎聘搜索输入框，请检查页面结构")

        self._write_keyword(input_locator, keyword)

    def _submit_search(self, page: Page) -> None:
        button_locator = self._first_visible_locator(page, self.SEARCH_BUTTON_SELECTORS)
        if button_locator is not None:
            button_locator.click(timeout=5000)
            return

        input_locator = self._find_primary_search_input(page)
        if input_locator is None:
            raise LiepinSearchPageChangedError("未找到搜索按钮，也无法回退到输入框提交")
        input_locator.press("Enter")

    def _wait_for_results(self, page: Page) -> None:
        for selector in self.RESULT_CARD_SELECTORS:
            try:
                locator = page.locator(selector)
                locator.first.wait_for(state="visible", timeout=15000)
                return
            except Exception:
                continue
        raise LiepinSearchPageChangedError("搜索完成后未找到结果列表，请检查页面结构")

    def _locate_result_cards(self, page: Page):
        if not hasattr(page, "locator"):
            return []
        for selector in self.RESULT_CARD_SELECTORS:
            locator = page.locator(selector)
            try:
                count = locator.count()
            except Error:
                continue
            if count > 0:
                return [locator.nth(index) for index in range(count)]
        return []

    def _extract_profile_url(self, card) -> str:
        for selector in self.PROFILE_LINK_SELECTORS:
            try:
                locator = card.locator(selector).first
                href = locator.get_attribute("href", timeout=1500)
            except Exception:
                continue
            if href:
                return href
        return ""

    def _first_visible_locator(self, page: Page, selectors: List[str]):
        for selector in selectors:
            locator = page.locator(selector).first
            try:
                if locator.is_visible(timeout=2500):
                    return locator
            except Exception:
                continue
        return None

    def _find_primary_search_input(self, page: Page):
        """Find the main free-text search input on the resume search page."""
        candidates = self._find_candidate_search_inputs(page)
        return candidates[0] if candidates else None

    def _find_candidate_search_inputs(self, page: Page):
        """Return candidate search inputs ordered by likelihood.

        On the live page there are multiple search-like inputs. The user
        confirmed that the primary keyword field is the top-most one in the
        filter area, so we sort visible editable candidates by vertical
        position, top to bottom.
        """
        candidates = []
        try:
            direct = page.locator("input.search-component-input")
            count = direct.count()
            for index in range(count):
                candidate = direct.nth(index)
                if self._is_editable_input(candidate):
                    top = self._locator_top(candidate)
                    candidates.append((top, index, candidate))
        except Exception:
            candidates = []

        if candidates:
            candidates.sort(key=lambda item: (item[0], item[1]))
            return [item[2] for item in candidates]

        fallback = self._first_visible_locator(page, self.SEARCH_INPUT_SELECTORS)
        return [fallback] if fallback is not None else []

    @staticmethod
    def _locator_top(locator) -> float:
        """Return the vertical position for one locator."""
        try:
            box = locator.bounding_box()
            if box and "y" in box:
                return float(box["y"])
        except Exception:
            pass
        return float("inf")

    def _clear_search_inputs(self, page: Page) -> None:
        """Clear all candidate search inputs before a new attempt."""
        for locator in self._find_candidate_search_inputs(page):
            try:
                locator.click(timeout=1000)
                locator.fill("")
            except Exception:
                continue

    def _write_keyword(self, locator, keyword: str) -> None:
        """Write a keyword into an input and verify that the value stuck."""
        locator.click(timeout=5000)
        try:
            locator.fill("")
        except Exception:
            pass
        locator.press("Control+A")
        locator.press("Backspace")
        locator.type(keyword, delay=40)

        value = ""
        try:
            value = locator.input_value(timeout=1500)
        except Exception:
            try:
                value = locator.get_attribute("value") or ""
            except Exception:
                value = ""

        if keyword not in value:
            try:
                locator.fill(keyword)
                value = locator.input_value(timeout=1500)
            except Exception:
                pass

        if keyword not in (value or ""):
            raise LiepinSearchPageChangedError("关键词未能写入搜索输入框")

    @staticmethod
    def _is_editable_input(locator) -> bool:
        """Return whether a locator points to a visible, enabled text input."""
        try:
            if not locator.is_visible(timeout=1500):
                return False
            disabled = locator.get_attribute("disabled")
            readonly = locator.get_attribute("readonly")
            input_type = (locator.get_attribute("type") or "text").lower()
            return (
                disabled is None
                and readonly is None
                and input_type in ("text", "search")
            )
        except Exception:
            return False
