import os

from src.core.config import ConfigManager
from src.core.liepin_browser import LiepinBrowserManager, LiepinBrowserState


def test_profile_dir_uses_config_path(tmp_path):
    config_path = os.path.join(tmp_path, "config.json")
    manager = ConfigManager(config_path=config_path)
    manager.update(liepin_browser_profile_dir="browser_profile/liepin-test")

    browser = LiepinBrowserManager(config_manager=manager)
    profile_dir = browser.get_profile_dir()

    assert profile_dir.endswith(os.path.join("browser_profile", "liepin-test"))


def test_state_reports_not_running_before_launch(tmp_path):
    config_path = os.path.join(tmp_path, "config.json")
    manager = ConfigManager(config_path=config_path)
    browser = LiepinBrowserManager(config_manager=manager)

    state = browser.get_state()

    assert isinstance(state, LiepinBrowserState)
    assert state.is_running is False
    assert state.logged_in is False


def test_pick_best_page_prefers_latest_liepin_page(tmp_path):
    class FakePage:
        def __init__(self, url):
            self.url = url

        def is_closed(self):
            return False

    config_path = os.path.join(tmp_path, "config.json")
    manager = ConfigManager(config_path=config_path)
    browser = LiepinBrowserManager(config_manager=manager)

    chosen = browser._pick_best_page(
        [
            FakePage("https://www.example.com"),
            FakePage("https://www.liepin.com/"),
            FakePage("https://www.liepin.com/zhaopin/"),
        ]
    )

    assert chosen.url == "https://www.liepin.com/zhaopin/"


def test_run_on_worker_executes_callable_on_single_thread(tmp_path):
    config_path = os.path.join(tmp_path, "config.json")
    manager = ConfigManager(config_path=config_path)
    browser = LiepinBrowserManager(config_manager=manager)

    first = browser._run_on_worker(lambda: browser._thread_id)
    second = browser._run_on_worker(lambda: browser._thread_id)

    assert first == second
    browser.close()


def test_is_search_page_url_accepts_h_search_url(tmp_path):
    config_path = os.path.join(tmp_path, "config.json")
    manager = ConfigManager(config_path=config_path)
    browser = LiepinBrowserManager(config_manager=manager)

    assert browser._is_search_page_url("https://h.liepin.com/search/getConditionItem")
    assert browser._is_search_page_url("https://h.liepin.com/search/list")
    assert browser._is_search_page_url("https://www.liepin.com/zhaopin/")
    assert not browser._is_search_page_url("https://www.liepin.com/")


def test_get_debug_dir_creates_expected_path(tmp_path):
    config_path = os.path.join(tmp_path, "config.json")
    manager = ConfigManager(config_path=config_path)
    browser = LiepinBrowserManager(config_manager=manager)

    debug_dir = browser.get_debug_dir()

    assert os.path.isdir(debug_dir)
    assert debug_dir.endswith(os.path.join("debug_artifacts", "liepin"))
