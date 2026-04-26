"""Liepin search execution and result list extraction."""

import logging
import re
from dataclasses import dataclass
from typing import Callable
from typing import Dict
from typing import List
from typing import Optional

from .liepin_browser import LiepinBrowserManager

try:
    from playwright.sync_api import Error, Page
except ImportError:  # pragma: no cover
    Error = Exception
    Page = None

logger = logging.getLogger(__name__)


class LiepinSearchError(Exception):
    """Base error for Liepin search execution."""


class LiepinSearchPageChangedError(LiepinSearchError):
    """Raised when the search page no longer matches expected selectors."""


@dataclass
class LiepinSearchCandidate:
    """Candidate summary captured from the result list page."""

    name: str = ""
    age: str = ""
    current_title: str = ""
    current_company: str = ""
    city: str = ""
    work_years: str = ""
    education: str = ""
    profile_url: str = ""
    summary: str = ""
    result_index: int = -1


@dataclass
class LiepinSearchControls:
    """Resolved primary controls on the Liepin search page."""

    search_input: object = None
    search_button: object = None


@dataclass
class LiepinFilterFieldSpec:
    """One filter field definition resolved from the live search page."""

    title: str
    field_type: str
    container_selector: str
    title_text: str = ""


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
        ".resume-list-item",
        ".ant-list-item",
        ".resume-item",
        ".ant-list-items > li",
        ".resume-list > div",
        ".resume-card",
        ".jobseeker-item",
        ".resume-list-content > div",
        "[class*='resume-item']",
        "[class*='candidate']",
    ]
    PROFILE_LINK_SELECTORS = [
        'a[href*="/resume/"]',
        'a[href*="/search/detail"]',
        'a[href*="/candidates/"]',
        "a",
    ]
    NEXT_PAGE_SELECTORS = [
        # Primary: Ant Design pagination next button (li element)
        ".ant-pagination-next:not(.ant-pagination-disabled)",
        'li[title="下一页"]:not(.ant-pagination-disabled)',
        # Secondary: button inside the next page li
        ".ant-pagination-next button",
        ".ant-pagination-next a",
        # Tertiary: generic pagination link (used by Liepin)
        'li[title="下一页"]:not(.ant-pagination-disabled) .ant-pagination-item-link',
        'li[title="下一页"] .ant-pagination-item-link',
        'li[title="下一页"] button',
        # Alternative: look for the last pagination item link that's not disabled
        ".ant-pagination > li:not(.ant-pagination-disabled):last-child .ant-pagination-item-link",
        ".ant-pagination > li:nth-last-child(1):not(.ant-pagination-disabled) .ant-pagination-item-link",
        ".ant-pagination > li:nth-last-child(2):not(.ant-pagination-disabled) .ant-pagination-item-link",
        # Alternative pagination class names
        ".pagination-next:not(.disabled)",
        ".lp-pagination-next",
        # Attribute-based selectors
        '[aria-label*="下一页"]',
        '[title="下一页"]',
        '[title*="下一页"]',
    ]
    LOADING_SELECTORS = [
        ".ant-spin.ant-spin-spinning",
        ".resume-spin-box",
        ".loading",
        "[class*='loading']",
    ]
    FILTER_FIELD_SPECS = {
        "目前城市": LiepinFilterFieldSpec(
            title="目前城市",
            field_type="city_modal",
            container_selector="div.search-item.sfilter-city",
            title_text="目前城市：",
        ),
        "期望城市": LiepinFilterFieldSpec(
            title="期望城市",
            field_type="city_modal",
            container_selector="div.search-item.sfilter-city",
            title_text="期望城市：",
        ),
        "工作年限": LiepinFilterFieldSpec(
            title="工作年限",
            field_type="tag",
            container_selector="div.search-item.sfilter-work-year",
            title_text="工作年限：",
        ),
        "教育经历": LiepinFilterFieldSpec(
            title="教育经历",
            field_type="tag",
            container_selector="div.search-item.sfilter-edu",
            title_text="教育经历：",
        ),
        "院校要求": LiepinFilterFieldSpec(
            title="院校要求",
            field_type="tag",
            container_selector="div.search-item.sfilter-additional",
            title_text="院校要求：",
        ),
        "性别": LiepinFilterFieldSpec(
            title="性别",
            field_type="dropdown",
            container_selector="div.ant-select.ant-select-lg.h-select.sexSelectStyle.gray.ant-select-single.ant-select-show-arrow",
            title_text="性 别：",
        ),
    }

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

    def search(
        self, keyword: str, filters: Optional[Dict[str, object]] = None
    ) -> List[LiepinSearchCandidate]:
        """Run a keyword search, apply optional filters, and return first page summaries."""
        if not keyword.strip():
            raise LiepinSearchError("搜索关键词不能为空")

        self.open_search_page()

        def _run(page):
            self._execute_search(page, keyword.strip())
            if filters:
                self._apply_filters_on_page(page, filters)
            return self.extract_candidates_from_page(page)

        return self._with_debug_snapshot(
            "search_keyword_{}".format(keyword.strip()),
            lambda: self.browser_manager.run_with_page(_run),
        )

    def apply_filters(self, filters: Dict[str, object]) -> None:
        """Apply a batch of supported filters on the active search page."""
        if not filters:
            return

        def _run(page):
            self._apply_filters_on_page(page, filters)
            return True

        self._with_debug_snapshot(
            "apply_filters",
            lambda: self.browser_manager.run_with_page(_run),
        )

    def _apply_filters_on_page(self, page: Page, filters: Dict[str, object]) -> None:
        """Apply supported filters to an already-open result page."""
        normalized_filters = {
            (key or "").strip(): value for key, value in (filters or {}).items() if (key or "").strip()
        }
        if not normalized_filters:
            return
        for title, value in normalized_filters.items():
            self._apply_one_filter(page, title, value)

    def extract_current_page_candidates(self) -> List[LiepinSearchCandidate]:
        """Parse candidate summaries from the current page without searching."""

        def _run(p):
            return self.extract_candidates_from_page(p)

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

    def go_to_next_result_page(self) -> bool:
        """Move to the next result page when pagination is available.

        Note: After successful navigation, the page object may become stale
        due to page reload. Callers should refresh their page reference using
        ensure_result_page() after this method returns True.
        """
        def _run(page):
            return self._go_to_next_result_page_locked(page)
        return self.browser_manager.run_with_page(_run)

    def _go_to_next_result_page_locked(self, page: Page) -> bool:
        """Internal implementation of pagination navigation on the worker thread."""
        import logging
        logger = logging.getLogger(__name__)

        current_page_num = self._get_current_page_number(page)
        target_page_num = current_page_num + 1 if current_page_num > 0 else 2
        logger.warning("go_to_next_result_page: Current page is %s, trying to go to page %s",
                   current_page_num, target_page_num)

        # Strategy 1: click next page button
        next_button = self._find_next_page_control(page)
        if next_button is not None:
            try:
                next_button.scroll_into_view_if_needed(timeout=1500)
                next_button.click(timeout=4000)
                logger.warning("go_to_next_result_page: Clicked next page button")
                if self._wait_for_page_change(page, current_page_num, timeout=6000):
                    self._soft_wait_for_results(page)
                    self.browser_manager.set_active_page(page)
                    return True
                logger.warning("go_to_next_result_page: Page number did not change after clicking next button")
            except Exception as exc:
                logger.warning("Next button click failed: %s", exc)

        # Strategy 2: click specific page number
        try:
            logger.warning("go_to_next_result_page: Trying direct page number click for page %s", target_page_num)
            if self._click_page_number(page, target_page_num):
                if self._wait_for_page_change(page, current_page_num, timeout=6000):
                    self._soft_wait_for_results(page)
                    self.browser_manager.set_active_page(page)
                    return True
        except Exception as exc:
            logger.warning("Page number click failed: %s", exc)

        # Strategy 3: navigate via URL parameter
        try:
            logger.warning("go_to_next_result_page: Trying URL navigation for page %s", target_page_num)
            if self._navigate_to_page_via_url(page, target_page_num):
                self._soft_wait_for_results(page)
                self.browser_manager.set_active_page(page)
                return True
        except Exception as exc:
            logger.warning("URL navigation failed: %s", exc)

        logger.error("go_to_next_result_page: All pagination strategies failed")
        return False

    def _wait_for_page_change(self, page: Page, previous_page_num: int, timeout: int = 6000) -> bool:
        """Poll pagination until the active page number changes."""
        import logging
        import time
        logger = logging.getLogger(__name__)
        deadline = time.time() + timeout / 1000.0
        while time.time() < deadline:
            try:
                new_num = self._get_current_page_number(page)
                if new_num != previous_page_num and new_num > 0:
                    logger.warning("_wait_for_page_change: detected page change to %s", new_num)
                    return True
            except Exception as exc:
                logger.debug("_wait_for_page_change error: %s", exc)
            try:
                page.wait_for_timeout(300)
            except Exception:
                pass
        return False

    def _soft_wait_for_results(self, page: Page) -> None:
        """Best-effort wait for results without blocking the whole task.

        If results are not visible within a short window we log a warning
        and return anyway so the caller can attempt DOM fallback extraction.
        """
        import logging
        logger = logging.getLogger(__name__)
        for selector in self.RESULT_CARD_SELECTORS:
            try:
                locator = page.locator(selector)
                # count() is synchronous and fast; skip selectors that don't match at all
                if locator.count() == 0:
                    continue
                locator.first.wait_for(state="visible", timeout=3000)
                logger.warning("_soft_wait_for_results: results visible via selector %s", selector)
                return
            except Exception:
                continue
        logger.warning("_soft_wait_for_results: no result cards visible, proceeding anyway")

    def _execute_search(self, page: Page, keyword: str) -> None:
        """Fill the most likely search field and submit the search.

        The live page contains more than one `.search-component-input`, so this
        method tries visible editable candidates one by one and only accepts a
        candidate when the page actually reaches the result state.
        """
        controls = self._detect_search_controls(page)
        if controls.search_input is None:
            raise LiepinSearchPageChangedError("未找到猎聘搜索输入框，请检查页面结构")
        self._write_keyword(controls.search_input, keyword)
        self._submit_search(page, controls)
        self._wait_for_results(page)

    # Regex patterns for structured field extraction from result-card text
    _AGE_PATTERN = re.compile(r"(\d+岁)")
    _EDUCATION_PATTERN = re.compile(r"(本科|硕士|博士|大专|中专|高中|初中)")
    _WORK_YEARS_PATTERN = re.compile(r"(?:工作)?(\d+年(?:经验)?)")
    _SALARY_PATTERN = re.compile(r"\d+k(?:-\d+k)?")
    _COMPANY_MARKERS = (
        "有限公司", "有限责任公司", "股份公司", "公司", "集团", "研究院", "研究所", "事务所", "中心"
    )
    _JOB_KEYWORDS = (
        "工程师", "经理", "总监", "主管", "专员", "顾问", "设计师", "开发", "运营", "产品经理",
        "销售", "教师", "医生", "护士", "会计", "人事", "行政", "财务", "采购", "物流",
        "翻译", "记者", "律师", "研究员", "分析师", "架构师", "测试", "运维", "前端", "后端",
        "算法", "数据", "市场", "品牌", "公关", "助理", "秘书", "客服", "技术支持", "项目管理",
        "生产", "质量", "工艺", "制造", "设备", "机械", "电气", "自动化", "材料", "化工",
    )
    _PERSONAL_TAGS = ("男", "女", "已婚", "未婚", "共青团员", "党员", "群众", "预备党员", "民主党派")

    def _clean_candidate_lines(self, lines: List[str]) -> tuple:
        """Remove UI noise and extract structured fields from result-card text.

        Returns (cleaned_lines, name, age, title, company, city, work_years, education).
        """
        cleaned = []
        for line in lines:
            line = line.strip()
            if not line or len(line) < 2:
                continue
            if line in self.CANDIDATE_NOISE_MARKERS:
                continue
            if any(marker in line for marker in self.FILTER_CARD_MARKERS):
                continue
            cleaned.append(line)

        if not cleaned:
            return [], "", "", "", "", "", "", ""

        name = cleaned[0]
        age = ""
        education = ""
        work_years = ""
        city = ""
        title = ""
        company = ""

        full_text = " ".join(cleaned)

        # Extract age / education / work_years globally
        m = self._AGE_PATTERN.search(full_text)
        if m:
            age = m.group(1)

        m = self._EDUCATION_PATTERN.search(full_text)
        if m:
            education = m.group(1)

        m = self._WORK_YEARS_PATTERN.search(full_text)
        if m:
            work_years = m.group(1)

        # Identify company name
        company_line_idx = -1
        for i, line in enumerate(cleaned):
            for marker in self._COMPANY_MARKERS:
                idx = line.find(marker)
                if idx != -1:
                    company_line_idx = i
                    if idx > 0:
                        potential_title = line[:idx].strip()
                        if len(potential_title) >= 2:
                            title = potential_title
                    company = line[idx:].strip()
                    break
            if company_line_idx != -1:
                break

        # Fallback: third line is likely the company if no marker matched
        if company_line_idx == -1 and len(cleaned) >= 3:
            candidate = cleaned[2]
            if not re.search(r"\d岁|\d+年(?:经验)?|本科|硕士|博士|大专", candidate):
                company = candidate
                company_line_idx = 2

        # Identify city from the compressed personal-info line
        for line in cleaned:
            has_personal = False
            temp = line
            if age and age in temp:
                temp = temp.replace(age, "")
                has_personal = True
            if education and education in temp:
                temp = temp.replace(education, "")
                has_personal = True
            if work_years and work_years in temp:
                temp = temp.replace(work_years, "")
                has_personal = True
            if has_personal or self._SALARY_PATTERN.search(temp):
                temp = self._SALARY_PATTERN.sub("", temp)
                temp = re.sub(r"^(男|女)\s*", "", temp)
                for tag in self._PERSONAL_TAGS:
                    temp = temp.replace(tag, "")
                temp = temp.replace(" ", "").strip()
                if 2 <= len(temp) <= 5 and temp not in (name, title, company) and not re.search(r"\d", temp):
                    city = temp
                    break

        # Identify title if not already extracted from a combined line
        if not title:
            for i, line in enumerate(cleaned):
                if i == 0 or i == company_line_idx:
                    continue
                temp = line
                for val in (age, education, work_years, city):
                    if val:
                        temp = temp.replace(val, "")
                temp = self._SALARY_PATTERN.sub("", temp)
                temp = re.sub(r"^(男|女)\s*", "", temp)
                for tag in self._PERSONAL_TAGS:
                    temp = temp.replace(tag, "")
                temp = temp.strip()
                if len(temp) < 2:
                    continue
                for kw in self._JOB_KEYWORDS:
                    if kw in temp:
                        title = line.strip()
                        break
                if title:
                    break

        # Fallback: first meaningful non-name / non-company line as title
        if not title:
            for i, line in enumerate(cleaned):
                if i == 0 or i == company_line_idx:
                    continue
                temp = line
                for val in (age, education, work_years, city):
                    if val:
                        temp = temp.replace(val, "")
                temp = self._SALARY_PATTERN.sub("", temp)
                temp = re.sub(r"^(男|女)\s*", "", temp)
                for tag in self._PERSONAL_TAGS:
                    temp = temp.replace(tag, "")
                temp = temp.strip()
                if len(temp) >= 2:
                    title = line.strip()
                    break

        return cleaned, name, age, title, company, city, work_years, education

    def extract_candidates_from_page(self, page: Page) -> List[LiepinSearchCandidate]:
        """Parse summary cards from the current result page."""
        url = ""
        try:
            url = page.url or ""
        except Exception:
            pass
        cards, matched_selector = self._locate_result_cards(page)
        logger.warning("extract_candidates_from_page: url=%s selector=%s cards=%s", url, matched_selector or "none", len(cards))

        if not cards:
            logger.warning("extract_candidates_from_page: No cards found via selectors, trying DOM fallback")
            return self._extract_candidates_with_dom_fallback(page)

        candidates = []
        for card in cards:
            try:
                profile_url = self._extract_profile_url(card)
                text = card.inner_text(timeout=2000).strip()
            except Exception:
                continue

            lines = [line.strip() for line in text.splitlines() if line.strip()]
            cleaned, name, age, title, company, city, work_years, education = self._clean_candidate_lines(lines)
            if not name:
                logger.warning("extract_candidates_from_page: skipping card with no valid name")
                continue
            candidate = LiepinSearchCandidate(
                name=name,
                age=age,
                current_title=title,
                current_company=company,
                city=city,
                work_years=work_years,
                education=education,
                summary="\n".join(cleaned[:8]),
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
                  // Scroll to top first to get consistent element positions
                  window.scrollTo(0, 0);
                  
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

                  const extractHrefFromElement = (el) => {
                    if (!el) return '';
                    // Direct href
                    let href = el.getAttribute('href') || '';
                    if (href) return href;
                    // Data attributes
                    for (const attr of ['data-href', 'data-url', 'data-link', 'data-resume-url', 'data-detail-url']) {
                      href = el.getAttribute(attr) || '';
                      if (href) return href;
                    }
                    // Onclick with URL
                    const onclick = el.getAttribute('onclick') || '';
                    const urlMatch = onclick.match(/(?:https?:\/\/[^\s'"]+)/);
                    if (urlMatch) return urlMatch[0];
                    return '';
                  };

                  const pickProfileHref = (element) => {
                    // 1. Try the element itself
                    let bestHref = extractHrefFromElement(element);
                    if (bestHref) return bestHref;
                    // 2. Try all descendants, scored
                    const anchors = Array.from(element.querySelectorAll('a[href], [data-href], [data-url], [data-link], [data-resume-url], [data-detail-url]'));
                    anchors.sort((left, right) => hrefScore(extractHrefFromElement(right)) - hrefScore(extractHrefFromElement(left)));
                    if (anchors.length) {
                      return extractHrefFromElement(anchors[0]) || '';
                    }
                    // 3. Look for hidden input with res_id_encode and construct a plausible URL
                    const resIdInput = element.querySelector('input[name="res_id_encode"]');
                    if (resIdInput) {
                      const resId = resIdInput.value || resIdInput.getAttribute('value') || '';
                      if (resId) {
                        return (location.origin || 'https://h.liepin.com') + '/resume/showresumedetail/?res_id_encode=' + encodeURIComponent(resId);
                      }
                    }
                    return '';
                  };

                  // Try multiple selectors for action buttons - Liepin uses various elements
                  let actionButtons = Array.from(document.querySelectorAll('button')).filter((button) => {
                    const text = (button.innerText || button.textContent || '').replace(/\s+/g, ' ').trim();
                    return text.includes('沟通') || text.includes('交换') || text.includes('联系');
                  });
                  
                  // If no buttons found, try links/anchors with action classes
                  if (actionButtons.length === 0) {
                    actionButtons = Array.from(document.querySelectorAll('a, span, div')).filter((el) => {
                      const text = (el.innerText || el.textContent || '').replace(/\s+/g, ' ').trim();
                      const hasActionText = text.includes('沟通') || text.includes('交换') || text.includes('联系') || text.includes('意向');
                      const hasActionClass = (el.className || '').toString().includes('action') || 
                                            (el.className || '').toString().includes('btn') ||
                                            (el.className || '').toString().includes('button');
                      return hasActionText && (hasActionClass || text.length < 20);
                    });
                  }
                  
                  // Debug info
                  const debugInfo = { buttonCount: actionButtons.length, containersFound: 0, skippedNoCheckbox: 0, skippedNoSize: 0, windowWidth: window.innerWidth };

                  const containers = [];
                  const seen = new Set();

                  for (const button of actionButtons) {
                    let current = button;
                    let chosen = null;
                    let skipReason = '';
                    while (current && current !== document.body) {
                      const rect = current.getBoundingClientRect ? current.getBoundingClientRect() : null;
                      const text = (current.innerText || current.textContent || '').replace(/\s+/g, ' ').trim();
                      const checkbox = current.querySelector('input[name="res_id_encode"]');
                      // RELAXED: Reduced size requirements for smaller viewports
                      const minWidth = window.innerWidth < 1500 ? 400 : 600;
                      const minHeight = window.innerHeight < 800 ? 80 : 100;
                      if (!checkbox) {
                        skipReason = 'no_checkbox';
                      } else if (!rect || rect.height < minHeight || rect.width < minWidth) {
                        skipReason = 'too_small:' + (rect ? `${rect.width}x${rect.height}(need>${minWidth}x${minHeight})` : 'no_rect');
                      } else if (text.length < 10) {
                        skipReason = 'text_too_short';
                      } else {
                        chosen = current;
                        break;
                      }
                      current = current.parentElement;
                    }

                    if (!chosen) {
                      if (skipReason.includes('no_checkbox')) debugInfo.skippedNoCheckbox++;
                      else if (skipReason.includes('too_small')) debugInfo.skippedNoSize++;
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
                      rawHtml: chosen.outerHTML ? chosen.outerHTML.slice(0, 600) : '',
                    });
                  }
                  
                  debugInfo.containersFound = containers.length;
                  
                  containers.sort((left, right) => left.top - right.top);
                  
                  // Return debug info as the last element (will be removed in Python)
                  containers.push({ _debugInfo: debugInfo });
                  return containers;
                }
                """
            )
        except Exception as exc:
            raise LiepinSearchPageChangedError(
                "未找到候选人结果卡片，且结果页启发式提取失败: {}".format(str(exc))
            )

        # Log debug info from JavaScript extraction (last element contains debug info)
        debug_info = None
        if isinstance(rows, list) and rows:
            last_row = rows[-1]
            if isinstance(last_row, dict) and '_debugInfo' in last_row:
                debug_info = last_row['_debugInfo']
                rows.pop()  # Remove debug element

        if debug_info:
            logger.warning("DOM fallback debug: buttons=%s, containers=%s, skippedNoCheckbox=%s, skippedNoSize=%s",
                       debug_info.get('buttonCount'), debug_info.get('containersFound'),
                       debug_info.get('skippedNoCheckbox'), debug_info.get('skippedNoSize'))
        else:
            logger.warning("DOM fallback: rows type=%s, count=%s", type(rows).__name__, len(rows) if rows else 0)

        candidates = []
        for row in rows or []:
            lines = row.get("lines") or []
            if not lines:
                continue
            cleaned, name, age, title, company, city, work_years, education = self._clean_candidate_lines(lines)
            if not name:
                logger.warning("DOM fallback: skipping container with no valid name after cleaning, raw_first_line=%s", lines[0] if lines else "")
                continue
            candidates.append(
                LiepinSearchCandidate(
                    name=name,
                    age=age,
                    current_title=title,
                    current_company=company,
                    city=city,
                    work_years=work_years,
                    education=education,
                    summary="\n".join(cleaned[:8]),
                    profile_url=row.get("href") or "",
                    result_index=len(candidates),
                )
            )

        logger.warning("DOM fallback: produced %s valid candidates", len(candidates))
        for i, row in enumerate(rows[:5]):
            logger.warning("DOM fallback raw %s: href=%s raw_html=%s", i + 1, row.get("href") or "(none)", (row.get("rawHtml") or "")[:300])
        for i, c in enumerate(candidates[:5]):
            logger.warning("DOM fallback candidate %s: name=%s href=%s", i + 1, c.name, c.profile_url or "(none)")
        if candidates:
            return candidates
        raise LiepinSearchPageChangedError("未找到候选人结果卡片")

    @staticmethod
    def _ensure_absolute_url(url: str) -> str:
        if url and url.startswith("/") and not url.startswith("//"):
            return "https://h.liepin.com" + url
        return url

    @staticmethod
    def _is_detail_page_url(url: str) -> bool:
        normalized = (url or "").lower()
        return "showresumedetail" in normalized or "/resume/" in normalized

    def open_candidate_detail(self, page: Page, candidate: LiepinSearchCandidate):
        """Open one candidate detail page and return the active detail page."""
        import logging
        import time
        logger = logging.getLogger(__name__)
        profile_url = self._ensure_absolute_url(candidate.profile_url or "")
        if profile_url:
            # 优先在新标签页打开，避免覆盖搜索结果页
            start = time.time()
            detail_page = None
            try:
                detail_page = self.browser_manager.new_page()
                detail_page.goto(profile_url, wait_until="domcontentloaded", timeout=15000)
                # 校验是否被重定向到找人/搜索页（常见于浏览器启动后的前几次访问）
                if not self._is_detail_page_url(detail_page.url or ""):
                    logger.warning("open_candidate_detail: redirected after domcontentloaded, waiting for stabilization")
                    # 短暂等待页面稳定
                    detail_page.wait_for_timeout(1200)
                    if not self._is_detail_page_url(detail_page.url or ""):
                        logger.warning("open_candidate_detail: still not detail page after wait, retrying with networkidle")
                        detail_page.goto(profile_url, wait_until="networkidle", timeout=15000)
                logger.warning("open_candidate_detail: opened in new tab elapsed=%.2fs url=%s", time.time() - start, (detail_page.url or profile_url)[:120])
                return detail_page
            except Exception as exc:
                logger.warning("open_candidate_detail: new tab failed elapsed=%.2fs url=%s error=%s", time.time() - start, profile_url[:120], exc)
                if detail_page is not None and detail_page is not page:
                    try:
                        detail_page.close()
                    except Exception:
                        pass
                # 降级：在当前页打开
            start = time.time()
            try:
                page.goto(profile_url, wait_until="domcontentloaded", timeout=15000)
                if not self._is_detail_page_url(page.url or ""):
                    page.wait_for_timeout(1200)
                    if not self._is_detail_page_url(page.url or ""):
                        page.goto(profile_url, wait_until="networkidle", timeout=15000)
                logger.warning("open_candidate_detail: opened in current tab elapsed=%.2fs url=%s", time.time() - start, (page.url or profile_url)[:120])
            except Exception as exc:
                logger.warning("open_candidate_detail: current tab also failed elapsed=%.2fs url=%s error=%s", time.time() - start, profile_url[:120], exc)
                raise
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
                  // Use the same action-button logic as DOM fallback for consistency
                  let actionButtons = Array.from(document.querySelectorAll('button')).filter((button) => {
                    const text = (button.innerText || button.textContent || '').replace(/\s+/g, ' ').trim();
                    return text.includes('沟通') || text.includes('交换') || text.includes('联系');
                  });
                  if (actionButtons.length === 0) {
                    actionButtons = Array.from(document.querySelectorAll('a, span, div')).filter((el) => {
                      const text = (el.innerText || el.textContent || '').replace(/\s+/g, ' ').trim();
                      const hasActionText = text.includes('沟通') || text.includes('交换') || text.includes('联系') || text.includes('意向');
                      const hasActionClass = (el.className || '').toString().includes('action') ||
                                            (el.className || '').toString().includes('btn') ||
                                            (el.className || '').toString().includes('button');
                      return hasActionText && (hasActionClass || text.length < 20);
                    });
                  }

                  const containers = [];
                  const seen = new Set();
                  for (const button of actionButtons) {
                    let current = button;
                    let chosen = null;
                    while (current && current !== document.body) {
                      const rect = current.getBoundingClientRect ? current.getBoundingClientRect() : null;
                      const text = (current.innerText || current.textContent || '').replace(/\s+/g, ' ').trim();
                      const checkbox = current.querySelector('input[name="res_id_encode"]');
                      // RELAXED: match DOM fallback size rules
                      const minWidth = window.innerWidth < 1500 ? 400 : 600;
                      const minHeight = window.innerHeight < 800 ? 80 : 100;
                      if (checkbox && rect && rect.height >= minHeight && rect.width >= minWidth && text.length >= 10) {
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
        import logging
        logger = logging.getLogger(__name__)
        if detail_page is not None and detail_page is not result_page:
            try:
                detail_page.close()
                logger.warning("close_detail_page: closed transient tab")
            except Exception as exc:
                logger.warning("close_detail_page: close transient tab failed: %s", exc)
        try:
            result_page.bring_to_front()
        except Exception:
            pass
        # Keep browser manager's active page pointer aligned to the result page
        try:
            self.browser_manager.set_active_page(result_page)
        except Exception:
            pass
        return result_page

    def _fill_search_input(self, page: Page, keyword: str) -> None:
        input_locator = self._find_primary_search_input(page)
        if input_locator is None:
            raise LiepinSearchPageChangedError("未找到猎聘搜索输入框，请检查页面结构")

        self._write_keyword(input_locator, keyword)

    def _submit_search(self, page: Page, controls: Optional[LiepinSearchControls] = None) -> None:
        controls = controls or self._detect_search_controls(page)
        button_locator = controls.search_button or self._first_visible_locator(page, self.SEARCH_BUTTON_SELECTORS)
        if button_locator is not None:
            button_locator.click(timeout=5000)
            return

        input_locator = controls.search_input or self._find_primary_search_input(page)
        if input_locator is None:
            raise LiepinSearchPageChangedError("未找到搜索按钮，也无法回退到输入框提交")
        input_locator.press("Enter")

    def _wait_for_results(self, page: Page) -> None:
        for selector in self.RESULT_CARD_SELECTORS:
            try:
                locator = page.locator(selector)
                locator.first.wait_for(state="visible", timeout=12000)
                return
            except Exception:
                continue
        raise LiepinSearchPageChangedError("搜索完成后未找到结果列表，请检查页面结构")

    # Keywords that indicate text lines are UI noise rather than candidate data
    FILTER_CARD_MARKERS = (
        "包含全部关键词",
        "没找到相关匹配项",
        "查看全部",
        "不限",
        "全选",
    )
    CANDIDATE_NOISE_MARKERS = (
        "在线",
        "今天活跃",
        "3天内活跃",
        "7天内活跃",
        "半月内活跃",
        "活跃状态",
        "隐藏",
        "查看联系方式",
        "立即沟通",
        "交换电话",
        "收藏",
        "举报",
    )

    def _locate_result_cards(self, page: Page):
        if not hasattr(page, "locator"):
            return [], ""
        for selector in self.RESULT_CARD_SELECTORS:
            locator = page.locator(selector)
            try:
                count = locator.count()
            except Error:
                continue
            if count > 0:
                # Validate first card text doesn't look like a filter widget
                try:
                    first_text = locator.first.inner_text(timeout=1500).strip()
                    if first_text and any(marker in first_text for marker in self.FILTER_CARD_MARKERS):
                        logger.warning("_locate_result_cards: selector=%s matched filter widget, skipping. text=%s", selector, first_text[:60])
                        continue
                except Exception:
                    pass
                return [locator.nth(index) for index in range(count)], selector
        return [], ""

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

    def _find_next_page_control(self, page: Page):
        """Find the next page button with comprehensive logging and fallback strategies."""
        import logging
        logger = logging.getLogger(__name__)

        # Scroll to bottom to ensure pagination is visible
        try:
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(500)
        except Exception:
            pass

        # Strategy 1: Try standard selectors targeting the li element
        for selector in self.NEXT_PAGE_SELECTORS:
            try:
                locator = page.locator(selector).first
                if not locator.is_visible(timeout=1500):
                    continue
                if self._is_disabled_pagination(locator):
                    logger.debug("Next page button found but disabled: %s", selector)
                    continue
                # Prefer inner clickable element over the container
                for inner_sel in ['a', 'button', '[role="button"]']:
                    try:
                        inner = locator.locator(inner_sel).first
                        if inner.is_visible(timeout=1000) and not self._is_disabled_pagination(inner):
                            logger.debug("Next page button found via selector %s (inner %s)", selector, inner_sel)
                            return inner
                    except Exception:
                        continue
                logger.debug("Next page button found via selector: %s", selector)
                return locator
            except Exception:
                continue

        # Strategy 2: JavaScript fallback to find pagination
        try:
            js_result = page.evaluate(
                r"""
                () => {
                    const strategies = [
                        () => document.querySelector('.ant-pagination-next:not(.ant-pagination-disabled)'),
                        () => document.querySelector('li[title="下一页"]:not(.ant-pagination-disabled)'),
                        () => {
                            const pagination = document.querySelector('.ant-pagination');
                            if (!pagination) return null;
                            const items = Array.from(pagination.querySelectorAll('li'));
                            for (let i = items.length - 1; i >= 0; i--) {
                                const item = items[i];
                                const text = (item.innerText || item.textContent || '').trim();
                                if (/^\d+$/.test(text)) continue;
                                if (item.classList.contains('ant-pagination-disabled')) continue;
                                if (item.classList.contains('ant-pagination-prev')) continue;
                                return item;
                            }
                            return null;
                        },
                    ];
                    for (let i = 0; i < strategies.length; i++) {
                        const btn = strategies[i]();
                        if (btn) {
                            return {
                                found: true,
                                strategy: i,
                                className: btn.className,
                                title: btn.getAttribute('title') || '',
                                text: (btn.innerText || btn.textContent || '').trim().slice(0, 50),
                            };
                        }
                    }
                    return { found: false };
                }
                """
            )
            if js_result and js_result.get("found"):
                logger.debug("Next page found via JavaScript strategy %s: %s", 
                           js_result.get("strategy"), js_result.get("className"))
                selectors_to_try = [
                    '.ant-pagination-next:not(.ant-pagination-disabled)',
                    'li[title="下一页"]:not(.ant-pagination-disabled)',
                    '.ant-pagination > li:nth-last-child(1):not(.ant-pagination-disabled)',
                    '.ant-pagination > li:nth-last-child(2):not(.ant-pagination-disabled)',
                ]
                for selector in selectors_to_try:
                    try:
                        locator = page.locator(selector).first
                        if locator.is_visible(timeout=1500):
                            if not self._is_disabled_pagination(locator):
                                for inner_sel in ['a', 'button', '[role="button"]']:
                                    try:
                                        inner = locator.locator(inner_sel).first
                                        if inner.is_visible(timeout=1000) and not self._is_disabled_pagination(inner):
                                            return inner
                                    except Exception:
                                        continue
                                return locator
                    except Exception:
                        continue
        except Exception as exc:
            logger.debug("JavaScript fallback for next page button failed: %s", exc)

        logger.warning("Could not find next page button with any selector")
        return None

    def _get_current_page_number(self, page: Page) -> int:
        """Get the current active page number from pagination."""
        try:
            active_page = page.locator('.ant-pagination-item-active').first
            if active_page.is_visible(timeout=1000):
                page_text = active_page.inner_text(timeout=1000)
                try:
                    return int(page_text.strip())
                except ValueError:
                    pass
        except Exception:
            pass
        return 0

    def _click_page_number(self, page: Page, target_page: int) -> bool:
        """Click on a specific page number as fallback navigation."""
        import logging
        logger = logging.getLogger(__name__)
        
        selectors = [
            f'.ant-pagination-item-{target_page}',
            f'.ant-pagination-item[title="{target_page}"]',
            f'li[title="{target_page}"]',
        ]
        
        for selector in selectors:
            try:
                logger.debug("_click_page_number: Trying selector %s", selector)
                page_link = page.locator(selector).first
                if page_link.is_visible(timeout=1500):
                    # Prefer inner clickable element
                    clicked_inner = False
                    for inner_sel in ['a', 'button']:
                        try:
                            inner = page_link.locator(inner_sel).first
                            if inner.is_visible(timeout=1000):
                                inner.click(timeout=5000)
                                clicked_inner = True
                                break
                        except Exception:
                            continue
                    if not clicked_inner:
                        page_link.click(timeout=5000)
                    logger.info("_click_page_number: Clicked page %s using selector %s", target_page, selector)
                    return True
            except Exception as exc:
                logger.debug("_click_page_number: Selector %s failed: %s", selector, exc)
                continue
        
        logger.error("_click_page_number: All selectors failed for page %s", target_page)
        return False

    def _navigate_to_page_via_url(self, page: Page, target_page: int) -> bool:
        """Navigate to a specific result page by modifying the URL parameter."""
        current_url = page.url or ""
        if not current_url:
            return False
        
        import re
        new_url = current_url
        # Liepin uses curPage starting from 0
        page_param_value = target_page - 1
        
        if re.search(r'[?&]curPage=\d+', current_url):
            new_url = re.sub(r'([?&]curPage=)\d+', lambda m: m.group(1) + str(page_param_value), current_url)
        elif re.search(r'[?&]page=\d+', current_url):
            new_url = re.sub(r'([?&]page=)\d+', lambda m: m.group(1) + str(target_page), current_url)
        elif '?' in current_url:
            new_url = current_url + '&curPage=' + str(page_param_value)
        else:
            new_url = current_url + '?curPage=' + str(page_param_value)
        
        if new_url == current_url:
            return False
        
        try:
            page.goto(new_url, wait_until="domcontentloaded", timeout=15000)
            return True
        except Exception:
            return False

    @staticmethod
    def _is_disabled_pagination(locator) -> bool:
        try:
            disabled = locator.get_attribute("disabled")
            aria_disabled = (locator.get_attribute("aria-disabled") or "").lower()
            class_name = (locator.get_attribute("class") or "").lower()
        except Exception:
            return False

        return (
            disabled is not None
            or aria_disabled == "true"
            or "ant-pagination-disabled" in class_name
            or "disabled" in class_name
        )

    def _first_visible_locator(self, page: Page, selectors: List[str]):
        for selector in selectors:
            try:
                locator = page.locator(selector).first
                if locator.is_visible(timeout=2500):
                    return locator
            except Exception:
                continue
        return None

    def _find_primary_search_input(self, page: Page):
        """Find the main free-text search input on the resume search page."""
        return self._detect_search_controls(page).search_input

    def _detect_search_controls(self, page: Page) -> LiepinSearchControls:
        """Resolve the top search input and the matching search button."""
        button_locator = self._find_search_button(page)
        if button_locator is not None:
            input_locator = self._find_search_input_near_button(page, button_locator)
            if input_locator is not None:
                return LiepinSearchControls(
                    search_input=input_locator,
                    search_button=button_locator,
                )

        candidates = self._find_candidate_search_inputs(page)
        return LiepinSearchControls(
            search_input=candidates[0] if candidates else None,
            search_button=button_locator,
        )

    def _find_search_button(self, page: Page):
        primary = self._first_visible_locator(page, ["button.search-btn"])
        if primary is not None:
            return primary
        return self._first_visible_locator(page, self.SEARCH_BUTTON_SELECTORS)

    def _find_search_input_near_button(self, page: Page, button_locator):
        """Prefer the verified main search container near `button.search-btn`."""
        try:
            container = page.locator("div.search-auto-complete-box").first
            container.wait_for(state="visible", timeout=1500)
            input_locator = container.locator("input.ant-select-selection-search-input").first
            if self._is_editable_input(input_locator):
                return input_locator
        except Exception:
            pass

        try:
            button_box = button_locator.bounding_box()
        except Exception:
            button_box = None
        if not button_box:
            return None

        best_candidate = None
        best_score = None
        for candidate in self._find_candidate_search_inputs(page):
            try:
                box = candidate.bounding_box()
            except Exception:
                box = None
            if not box:
                continue
            width = box.get("width") or 0
            horizontal_gap = abs((button_box.get("x") or 0) - ((box.get("x") or 0) + width))
            vertical_gap = abs((button_box.get("y") or 0) - (box.get("y") or 0))
            score = (0 if width >= 500 else 1, vertical_gap, horizontal_gap)
            if best_score is None or score < best_score:
                best_score = score
                best_candidate = candidate
        return best_candidate

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

        try:
            direct = page.locator("input.ant-select-selection-search-input")
            count = direct.count()
            for index in range(count):
                candidate = direct.nth(index)
                if not self._is_editable_input(candidate):
                    continue
                top = self._locator_top(candidate)
                candidates.append((top, index, candidate))
        except Exception:
            candidates = []

        if candidates:
            candidates.sort(key=lambda item: (item[0], item[1]))
            return [item[2] for item in candidates]

        fallback = self._first_visible_locator(page, self.SEARCH_INPUT_SELECTORS)
        return [fallback] if fallback is not None else []

    def _apply_one_filter(self, page: Page, title: str, value: object) -> None:
        spec = self.FILTER_FIELD_SPECS.get(title)
        if spec is None:
            raise LiepinSearchError("暂不支持该筛选字段: {}".format(title))
        if spec.field_type == "tag":
            self._apply_tag_filter(page, spec, str(value))
            return
        if spec.field_type == "dropdown":
            self._apply_dropdown_filter(page, spec, str(value))
            return
        if spec.field_type == "city_modal":
            self._apply_city_filter(page, spec, value)
            return
        raise LiepinSearchError("未实现的筛选字段类型: {}".format(spec.field_type))

    def _field_container(self, page: Page, spec: LiepinFilterFieldSpec):
        """Resolve one filter row by selector plus title text.

        Several live fields share the same container selector, especially
        current city and expected city. The mapping document says to bind fields
        by title text + parent container, so do not blindly use `.first`.
        """
        containers = page.locator(spec.container_selector)
        try:
            count = containers.count()
        except Exception:
            count = 0
        title_text = (spec.title_text or spec.title or "").replace(" ", "")
        for index in range(count):
            container = containers.nth(index)
            try:
                if not container.is_visible(timeout=1200):
                    continue
                text = (container.inner_text(timeout=1200) or "").replace(" ", "")
                if title_text and title_text in text:
                    return container
            except Exception:
                continue
        if count:
            return containers.first
        return page.locator(spec.container_selector).first

    def _apply_tag_filter(self, page: Page, spec: LiepinFilterFieldSpec, value: str) -> None:
        container = self._field_container(page, spec)
        locator = container.locator("label.tag-item:has-text('{}')".format(value)).first
        if not locator.is_visible(timeout=3000):
            raise LiepinSearchPageChangedError("未找到标签筛选项: {} -> {}".format(spec.title, value))
        locator.click(timeout=5000)
        self._wait_for_filter_apply(page, expected_text=value)

    def _apply_dropdown_filter(self, page: Page, spec: LiepinFilterFieldSpec, value: str) -> None:
        container = self._field_container(page, spec)
        if not container.is_visible(timeout=3000):
            raise LiepinSearchPageChangedError("未找到下拉筛选控件: {}".format(spec.title))
        input_locator = container.locator("input.ant-select-selection-search-input").first
        input_locator.click(timeout=5000)
        try:
            input_locator.press("ArrowDown")
        except Exception:
            page.keyboard.press("ArrowDown")
        page.wait_for_timeout(200)
        try:
            options = self._open_dropdown_options(page)
            self._select_dropdown_option(options, value)
        except Exception:
            self._select_dropdown_option_by_keyboard(page, value)
        self._wait_for_filter_apply(page, expected_text=value)

    def _apply_city_filter(self, page: Page, spec: LiepinFilterFieldSpec, value: object) -> None:
        cities = [item for item in (value if isinstance(value, list) else [value]) if str(item).strip()]
        cities = [str(item).strip() for item in cities]
        if not cities:
            return
        if len(cities) == 1:
            self._apply_single_city_filter(page, spec, cities[0])
            return

        container = self._field_container(page, spec)
        trigger = container.locator("span.btn-choose:has-text('其他')").first
        if not trigger.is_visible(timeout=3000):
            raise LiepinSearchPageChangedError("未找到城市其他入口: {}".format(spec.title))
        trigger.click(timeout=5000)
        modal = page.locator("div.ant-modal.city-modal").first
        modal.wait_for(state="visible", timeout=5000)
        for city in cities:
            self._select_city_in_modal(modal, city)
        confirm = modal.locator("button.ant-btn.ant-btn-primary").first
        confirm.click(timeout=5000)
        modal.wait_for(state="hidden", timeout=8000)
        self._wait_for_filter_apply(page, expected_text=cities[0])

    def _apply_single_city_filter(self, page: Page, spec: LiepinFilterFieldSpec, value: str) -> None:
        container = self._field_container(page, spec)
        hot_tag = container.locator("label.tag-item:has-text('{}')".format(value)).first
        try:
            if hot_tag.is_visible(timeout=1200):
                hot_tag.click(timeout=5000)
                self._wait_for_filter_apply(page, expected_text=value)
                return
        except Exception:
            pass

        trigger = container.locator("span.btn-choose:has-text('其他')").first
        if not trigger.is_visible(timeout=3000):
            raise LiepinSearchPageChangedError("未找到城市其他入口: {}".format(spec.title))
        trigger.click(timeout=5000)
        modal = page.locator("div.ant-modal.city-modal").first
        modal.wait_for(state="visible", timeout=5000)

        self._select_city_in_modal(modal, value)
        confirm = modal.locator("button.ant-btn.ant-btn-primary").first
        confirm.click(timeout=5000)
        modal.wait_for(state="hidden", timeout=8000)
        self._wait_for_filter_apply(page, expected_text=value)

    def _select_city_in_modal(self, modal, value: str) -> None:
        hot_city = modal.locator("span.ant-tag.ant-tag-checkable:has-text('{}')".format(value)).first
        try:
            if hot_city.is_visible(timeout=1200):
                hot_city.click(timeout=5000)
                return
            raise RuntimeError("not-hot-city")
        except Exception:
            city_input = modal.locator('input.ant-input[placeholder="搜索城市"]').first
            city_input.click(timeout=3000)
            city_input.fill(value)
            suggest = modal.locator("div.suggest-list > ul > li").first
            suggest.wait_for(state="visible", timeout=5000)
            suggest.click(timeout=5000)

    def _open_dropdown_options(self, page: Page):
        dropdown = page.locator("div.ant-select-dropdown.search-select").first
        try:
            dropdown.wait_for(state="visible", timeout=1500)
            return dropdown.locator("div.ant-select-item.ant-select-item-option")
        except Exception:
            page.keyboard.press("ArrowDown")
            page.wait_for_timeout(200)
            dropdown.wait_for(state="visible", timeout=3000)
            return dropdown.locator("div.ant-select-item.ant-select-item-option")

    def _select_dropdown_option(self, options, value: str) -> None:
        count = options.count()
        for index in range(count):
            option = options.nth(index)
            try:
                text = (option.inner_text(timeout=1000) or "").strip()
            except Exception:
                continue
            if value == text or value in text:
                option.click(timeout=5000)
                return
        raise LiepinSearchPageChangedError("未找到下拉选项: {}".format(value))

    @staticmethod
    def _select_dropdown_option_by_keyboard(page: Page, value: str) -> None:
        """Fallback for Ant Select fields where visible option locators are unstable."""
        steps_by_value = {
            "不限": 1,
            "男": 2,
            "女": 3,
        }
        steps = steps_by_value.get((value or "").strip())
        if steps is None:
            raise LiepinSearchPageChangedError("未找到下拉选项: {}".format(value))
        for _ in range(max(0, steps - 1)):
            page.keyboard.press("ArrowDown")
            page.wait_for_timeout(120)
        page.keyboard.press("Enter")

    def _wait_for_filter_apply(self, page: Page, expected_text: str = "", timeout: int = 12000) -> None:
        """Wait until the filter-driven refresh cycle settles."""
        import time

        self._wait_for_loading_cycle(page, timeout=timeout)
        self._soft_wait_for_results(page)
        if not expected_text:
            return
        deadline = time.time() + timeout / 1000.0
        while time.time() < deadline:
            try:
                body_text = page.locator("body").inner_text(timeout=1500)
                if expected_text in (body_text or ""):
                    return
            except Exception:
                pass
            try:
                page.wait_for_timeout(300)
            except Exception:
                break

    def _wait_for_loading_cycle(self, page: Page, timeout: int = 12000) -> None:
        import time

        deadline = time.time() + timeout / 1000.0
        saw_loading = False
        while time.time() < deadline:
            loading = self._is_loading(page)
            if loading:
                saw_loading = True
            if saw_loading and not loading:
                return
            try:
                page.wait_for_timeout(250)
            except Exception:
                break

    def _is_loading(self, page: Page) -> bool:
        for selector in self.LOADING_SELECTORS:
            try:
                locator = page.locator(selector)
                if locator.count() > 0 and locator.first.is_visible(timeout=300):
                    return True
            except Exception:
                continue
        return False

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
