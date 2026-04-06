"""Playwright browser session manager for Liepin automation."""

import os
import queue
import re
import sys
import threading
from datetime import datetime
from dataclasses import dataclass
from typing import Callable, Optional, TypeVar

from .config import ConfigManager

try:
    from playwright.sync_api import (
        BrowserContext,
        Error,
        Page,
        Playwright,
        sync_playwright,
    )
except ImportError:  # pragma: no cover - validated at runtime when dependency exists
    BrowserContext = None
    Error = Exception
    Page = None
    Playwright = None
    sync_playwright = None


class LiepinBrowserError(Exception):
    """Base error for Liepin browser automation."""


class PlaywrightNotInstalledError(LiepinBrowserError):
    """Raised when Playwright is not installed."""


class LiepinLoginRequiredError(LiepinBrowserError):
    """Raised when the browser is open but not logged in to Liepin."""


@dataclass
class LiepinBrowserState:
    """Observable browser session state."""

    profile_dir: str
    channel: str
    headless: bool
    is_running: bool = False
    logged_in: bool = False
    current_url: str = ""


T = TypeVar("T")


class LiepinBrowserManager:
    """Manage a persistent Playwright browser context for Liepin."""

    LOGIN_URL = "https://www.liepin.com/"
    SEARCH_URL = "https://h.liepin.com/search/getConditionItem"

    def __init__(self, config_manager: Optional[ConfigManager] = None):
        self.config_manager = config_manager or ConfigManager()
        self._playwright: Optional[Playwright] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._thread: Optional[threading.Thread] = None
        self._task_queue = queue.Queue()
        self._thread_id: Optional[int] = None

    def _get_base_dir(self) -> str:
        if getattr(sys, "frozen", False):
            return os.path.dirname(sys.executable)
        return os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )

    def get_profile_dir(self) -> str:
        """Return the absolute path to the persistent browser profile directory."""
        profile_dir = os.path.normpath(
            self.config_manager.config.liepin_browser_profile_dir.strip()
        )
        if os.path.isabs(profile_dir):
            return profile_dir
        return os.path.normpath(os.path.join(self._get_base_dir(), profile_dir))

    def get_debug_dir(self) -> str:
        """Return the absolute path for browser debug artifacts."""
        path = os.path.join(self._get_base_dir(), "debug_artifacts", "liepin")
        os.makedirs(path, exist_ok=True)
        return path

    @staticmethod
    def _pick_best_page(pages, current_page=None):
        """Prefer the most recently opened Liepin page."""
        valid_pages = []
        for page in pages or []:
            try:
                if page.is_closed():
                    continue
            except Exception:
                continue
            valid_pages.append(page)

        if not valid_pages:
            return current_page

        liepin_pages = []
        for page in valid_pages:
            try:
                if "liepin.com" in (page.url or "").lower():
                    liepin_pages.append(page)
            except Exception:
                continue

        if liepin_pages:
            return liepin_pages[-1]
        return valid_pages[-1]

    def _ensure_worker(self) -> None:
        """Start the dedicated Playwright worker thread if needed."""
        if self._thread and self._thread.is_alive():
            return

        self._thread = threading.Thread(
            target=self._worker_loop,
            name="LiepinBrowserWorker",
            daemon=True,
        )
        self._thread.start()

    def _worker_loop(self) -> None:
        """Run Playwright tasks on a single dedicated thread."""
        self._thread_id = threading.get_ident()
        while True:
            item = self._task_queue.get()
            if item is None:
                break

            func, args, kwargs, result_queue = item
            try:
                value = func(*args, **kwargs)
                result_queue.put((True, value))
            except Exception as exc:
                result_queue.put((False, exc))

    def _run_on_worker(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Execute a callable on the dedicated Playwright thread."""
        self._ensure_worker()
        if threading.get_ident() == self._thread_id:
            return func(*args, **kwargs)

        result_queue = queue.Queue(maxsize=1)
        self._task_queue.put((func, args, kwargs, result_queue))
        success, payload = result_queue.get()
        if success:
            return payload
        raise payload

    def _sync_active_page(self) -> Optional[Page]:
        """Keep the current page pointer aligned to the best available page."""
        if self._context is None:
            return None
        self._page = self._pick_best_page(list(self._context.pages), self._page)
        return self._page

    def _launch_locked(self) -> LiepinBrowserState:
        """Launch the persistent browser inside the worker thread."""
        if sync_playwright is None:
            raise PlaywrightNotInstalledError(
                "未安装 Playwright，请先安装 playwright 并执行 playwright install chromium"
            )

        if self._context is not None:
            return self._get_state_locked()

        profile_dir = self.get_profile_dir()
        os.makedirs(profile_dir, exist_ok=True)

        self._playwright = sync_playwright().start()
        browser_type = getattr(
            self._playwright,
            self.config_manager.config.liepin_browser_channel,
            self._playwright.chromium,
        )
        self._context = browser_type.launch_persistent_context(
            user_data_dir=profile_dir,
            headless=self.config_manager.config.liepin_browser_headless,
            viewport={"width": 1440, "height": 960},
        )
        self._page = self._pick_best_page(list(self._context.pages))
        if self._page is None:
            self._page = self._context.new_page()
        return self._get_state_locked()

    def _ensure_page_locked(self) -> Page:
        """Return an active page inside the worker thread."""
        if self._context is None or self._page is None:
            self._launch_locked()
        page = self._sync_active_page()
        if page is None and self._context is not None:
            self._page = self._context.new_page()
            page = self._page
        return page

    @staticmethod
    def _is_search_page_url(url: str) -> bool:
        """Return whether a URL looks like the Liepin search workspace."""
        normalized = (url or "").lower()
        return (
            "h.liepin.com/search/getconditionitem" in normalized
            or "h.liepin.com/search" in normalized
            or "liepin.com/zhaopin" in normalized
        )

    def _get_state_locked(self) -> LiepinBrowserState:
        """Return browser state from inside the worker thread."""
        page = self._sync_active_page()
        return LiepinBrowserState(
            profile_dir=self.get_profile_dir(),
            channel=self.config_manager.config.liepin_browser_channel,
            headless=self.config_manager.config.liepin_browser_headless,
            is_running=self._context is not None,
            logged_in=self._is_logged_in_locked(),
            current_url=page.url if page else "",
        )

    def get_state(self) -> LiepinBrowserState:
        """Return the current browser session state."""
        return self._run_on_worker(self._get_state_locked)

    def launch(self) -> LiepinBrowserState:
        """Launch a persistent Playwright browser context."""
        return self._run_on_worker(self._launch_locked)

    def ensure_page(self) -> Page:
        """Return an active page, launching the browser if needed."""
        return self._run_on_worker(self._ensure_page_locked)

    def run_with_page(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Execute a callback with the active page on the worker thread."""

        def _invoke():
            page = self._ensure_page_locked()
            return func(page, *args, **kwargs)

        return self._run_on_worker(_invoke)

    def export_debug_snapshot(self, reason: str = "manual") -> str:
        """Export the current page structure for selector debugging."""

        def _export(page):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", reason).strip("_") or "snapshot"
            base_name = "{}_{}".format(timestamp, slug)
            debug_dir = self.get_debug_dir()
            html_path = os.path.join(debug_dir, base_name + ".html")
            meta_path = os.path.join(debug_dir, base_name + ".txt")

            html = page.content()
            title = page.title()
            url = page.url or ""
            interactive = page.evaluate(
                """
                () => {
                  const collect = (selector) => Array.from(document.querySelectorAll(selector)).slice(0, 80).map((el, index) => ({
                    index,
                    tag: el.tagName,
                    id: el.id || '',
                    name: el.getAttribute('name') || '',
                    type: el.getAttribute('type') || '',
                    placeholder: el.getAttribute('placeholder') || '',
                    role: el.getAttribute('role') || '',
                    href: el.getAttribute('href') || '',
                    text: (el.innerText || el.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 200),
                    className: (el.className || '').toString().replace(/\s+/g, ' ').trim().slice(0, 240),
                    rectTop: Math.round((el.getBoundingClientRect && el.getBoundingClientRect().top) || 0),
                    rectLeft: Math.round((el.getBoundingClientRect && el.getBoundingClientRect().left) || 0),
                  }));
                  return {
                    inputs: collect('input, textarea, [contenteditable="true"]'),
                    buttons: collect('button, [role="button"], input[type="button"], input[type="submit"]'),
                    forms: collect('form'),
                    iframes: collect('iframe'),
                  };
                }
                """
            )

            with open(html_path, "w", encoding="utf-8") as html_file:
                html_file.write(html)

            with open(meta_path, "w", encoding="utf-8") as meta_file:
                meta_file.write("URL: {}\n".format(url))
                meta_file.write("TITLE: {}\n\n".format(title))
                for section in ("inputs", "buttons", "forms", "iframes"):
                    meta_file.write("[{}]\n".format(section.upper()))
                    for item in interactive.get(section, []):
                        meta_file.write(
                            "{tag} | top={rectTop} | left={rectLeft} | id={id} | name={name} | type={type} | placeholder={placeholder} | role={role} | href={href} | class={className} | text={text}\n".format(
                                **item
                            )
                        )
                    meta_file.write("\n")

            return meta_path

        return self.run_with_page(_export)

    def open_home(self) -> LiepinBrowserState:
        """Navigate to the Liepin home page."""

        def _open_home_locked():
            page = self._ensure_page_locked()
            page.goto(self.LOGIN_URL, wait_until="domcontentloaded")
            return self._get_state_locked()

        return self._run_on_worker(_open_home_locked)

    def open_search_page(self) -> LiepinBrowserState:
        """Navigate to the Liepin search page."""

        def _open_search_locked():
            page = self._ensure_page_locked()
            current_url = page.url or ""
            if not self._is_search_page_url(current_url):
                try:
                    page.goto(self.SEARCH_URL, wait_until="domcontentloaded")
                except Exception:
                    # Liepin may redirect immediately after navigation; as long as
                    # we land on a valid search page, treat it as success.
                    self._sync_active_page()
            self._sync_active_page()
            return self._get_state_locked()

        return self._run_on_worker(_open_search_locked)

    def _is_logged_in_locked(self) -> bool:
        """Best-effort login state detection inside the worker thread."""
        page = self._sync_active_page()
        if page is None:
            return False

        try:
            url = (page.url or "").lower()
            if "login" in url or "passport" in url:
                return False

            text = page.locator("body").inner_text(timeout=3000)
        except Error:
            return False
        except Exception:
            return False

        logged_in_markers = (
            "退出登录",
            "我的简历",
            "我的职位",
            "消息",
            "招聘官",
            "找人",
        )
        login_markers = (
            "登录",
            "注册",
            "立即登录",
        )

        if any(marker in text for marker in logged_in_markers):
            return True
        if any(marker in text for marker in login_markers):
            return False
        return False

    def is_logged_in(self) -> bool:
        """Best-effort login state detection for Liepin.

        This first implementation intentionally uses conservative heuristics and
        will be refined against the live site during integration.
        """
        return self._run_on_worker(self._is_logged_in_locked)

    def ensure_logged_in(self) -> LiepinBrowserState:
        """Raise if the browser is not currently logged in to Liepin."""
        state = self.get_state()
        if state.logged_in:
            return state
        raise LiepinLoginRequiredError("猎聘当前未登录，请先在浏览器中手动完成登录")

    def close(self) -> None:
        """Close the persistent browser context and Playwright runtime."""

        def _close_locked() -> None:
            if self._context is not None:
                self._context.close()
                self._context = None
            if self._playwright is not None:
                self._playwright.stop()
                self._playwright = None
            self._page = None

        if self._thread and self._thread.is_alive():
            self._run_on_worker(_close_locked)
            self._task_queue.put(None)
            self._thread.join(timeout=3.0)
        self._thread = None
        self._thread_id = None
