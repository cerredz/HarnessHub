"""Tests for the Playwright-backed Google Maps browser integration."""

from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from harnessiq.integrations.google_maps_playwright import (
    PlaywrightGoogleMapsSession,
    _GOOGLE_MAPS_BOOTSTRAP_URL,
)
from harnessiq.tools.browser import build_browser_tool_definitions


class _FakeKeyboard:
    def press(self, key):  # noqa: ANN001
        self.last_key = key


class _FakePage:
    def __init__(self, url: str = "https://www.google.com/maps/search/dentist+edison+nj") -> None:
        self.url = url
        self.keyboard = _FakeKeyboard()
        self.goto_calls: list[tuple[str, dict[str, object]]] = []

    def goto(self, url, **kwargs):  # noqa: ANN001
        self.goto_calls.append((url, kwargs))
        self.url = url

    def wait_for_load_state(self, *args, **kwargs):  # noqa: ANN001
        return None

    def click(self, selector, **kwargs):  # noqa: ANN001
        self.last_click = selector

    def fill(self, selector, text):  # noqa: ANN001
        self.last_fill = (selector, text)

    def type(self, selector, text):  # noqa: ANN001
        self.last_type = (selector, text)

    def select_option(self, selector, value):  # noqa: ANN001
        self.last_select = (selector, value)

    def hover(self, selector, **kwargs):  # noqa: ANN001
        self.last_hover = selector

    def set_input_files(self, selector, file_path):  # noqa: ANN001
        self.last_upload = (selector, file_path)

    def evaluate(self, script):  # noqa: ANN001
        if "window.scrollBy" in script:
            return None
        return {
            "title": "Edison Family Dental",
            "imageCount": 4,
            "hasViewport": True,
            "hasNav": True,
            "hasForm": True,
            "linkCount": 12,
        }

    def screenshot(self, **kwargs):  # noqa: ANN001
        return b"png"

    def content(self):
        return "<html><body>Dentist Edison NJ</body></html>"

    def inner_text(self, selector):  # noqa: ANN001
        if selector == "body":
            return (
                "Edison Family Dental\nDentist\n4.6 32 reviews\nQuestions & Answers\n"
                "Response from the owner\nUpdates\nMarch 2, 2026"
            )
        return ""

    def query_selector(self, selector):  # noqa: ANN001
        return object() if selector == ".exists" else None

    def title(self):
        return "Edison Family Dental"

    def eval_on_selector_all(self, selector, script):  # noqa: ANN001
        if "maps/place" in selector:
            return [
                {
                    "rank": 1,
                    "name": "Competitor Dental",
                    "category": "Dentist",
                    "rating_text": "4.8",
                    "review_count_text": "187",
                    "maps_url": "https://www.google.com/maps/place/competitor",
                    "text": "Competitor Dental\nDentist\n4.8 187 reviews",
                },
                {
                    "rank": 2,
                    "name": "Edison Family Dental",
                    "category": "Dentist",
                    "rating_text": "4.6",
                    "review_count_text": "32",
                    "maps_url": "https://www.google.com/maps/place/edison",
                    "text": "Edison Family Dental\nDentist\n4.6 32 reviews",
                },
            ]
        if selector == "a[href]":
            return [
                "https://edisonfamilydental.com",
                "https://www.google.com/privacy",
            ]
        if selector == "img":
            return 5
        return []


class _FakeContext:
    def __init__(self, pages: list[_FakePage] | None = None) -> None:
        self.pages = list(pages or [])
        self.new_page_calls = 0

    def new_page(self):
        self.new_page_calls += 1
        page = _FakePage(url="about:blank")
        self.pages.append(page)
        return page

    def close(self) -> None:
        return None


class _FakeChromium:
    def __init__(self, context: _FakeContext) -> None:
        self._context = context
        self.persistent_launches: list[dict[str, object]] = []

    def launch_persistent_context(self, user_data_dir, **kwargs):  # noqa: ANN001
        self.persistent_launches.append({"user_data_dir": user_data_dir, **kwargs})
        return self._context


class _FakePlaywright:
    def __init__(self, context: _FakeContext) -> None:
        self.chromium = _FakeChromium(context)

    def stop(self) -> None:
        return None


class _FakePlaywrightStarter:
    def __init__(self, context: _FakeContext) -> None:
        self._playwright = _FakePlaywright(context)

    def start(self) -> _FakePlaywright:
        return self._playwright


class GoogleMapsPlaywrightTests(unittest.TestCase):
    def test_start_navigates_bootstrap_page_to_google_maps(self) -> None:
        page = _FakePage(url="about:blank")
        context = _FakeContext([page])

        with patch(
            "playwright.sync_api.sync_playwright",
            return_value=_FakePlaywrightStarter(context),
        ):
            session = PlaywrightGoogleMapsSession(
                session_dir=Path("memory/prospecting/test/browser-data"),
                headless=True,
                channel="chrome",
            )
            session.start()

        self.assertEqual(session.page.url, _GOOGLE_MAPS_BOOTSTRAP_URL)
        self.assertEqual(page.goto_calls[0][0], _GOOGLE_MAPS_BOOTSTRAP_URL)
        self.assertEqual(page.goto_calls[0][1]["wait_until"], "domcontentloaded")

    def test_build_tools_binds_all_shared_browser_handlers(self) -> None:
        session = PlaywrightGoogleMapsSession()
        session._page = _FakePage()  # type: ignore[attr-defined]

        tools = session.build_tools()

        self.assertEqual(len(tools), len(build_browser_tool_definitions()))
        registry = {tool.definition.name: tool for tool in tools}
        self.assertEqual(registry["get_current_url"].execute({}).output["url"], session.page.url)

    def test_extract_modes_return_structured_content(self) -> None:
        session = PlaywrightGoogleMapsSession()
        session._page = _FakePage()  # type: ignore[attr-defined]

        search_results = session._handle_extract_content({"mode": "maps_search_results", "max_items": 2})
        place_details = session._handle_extract_content({"mode": "maps_place_details"})
        website = session._handle_extract_content({"mode": "website_quality_snapshot"})

        self.assertEqual(search_results["count"], 2)
        self.assertEqual(search_results["results"][1]["top_competitor_review_count"], 187)
        self.assertEqual(place_details["review_count"], 32)
        self.assertTrue(place_details["owner_responds_to_reviews"])
        self.assertIn("functional", website["website_quality_assessment"])

    def test_basic_browser_tools_operate_on_page(self) -> None:
        session = PlaywrightGoogleMapsSession()
        session._page = _FakePage()  # type: ignore[attr-defined]

        navigate = session._handle_navigate({"url": "https://example.com"})
        find = session._handle_find_element({"selector": ".exists"})
        screenshot = session._handle_screenshot({})

        self.assertEqual(navigate["current_url"], "https://example.com")
        self.assertTrue(find["found"])
        self.assertEqual(screenshot["size_bytes"], 3)


if __name__ == "__main__":
    unittest.main()
