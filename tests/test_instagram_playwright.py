"""Tests for the Instagram Playwright integration helpers."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from harnessiq.integrations.instagram_playwright import (
    PlaywrightInstagramSearchBackend,
    _normalize_candidate_url,
)


class _FakePage:
    def __init__(
        self,
        *,
        url: str = "https://www.google.com/search?q=ugc",
        body_text: str = "",
        title_text: str = "",
        entries: list[dict[str, str]] | None = None,
    ) -> None:
        self.url = url
        self._body_text = body_text
        self._title_text = title_text
        self._entries = list(entries or [])
        self.goto_calls: list[str] = []
        self.closed = False

    def goto(self, url: str, *, wait_until: str, timeout: int) -> None:
        self.goto_calls.append(url)
        self.url = url

    def wait_for_load_state(self, state: str, *, timeout: int) -> None:
        return None

    def eval_on_selector_all(self, selector: str, script: str):
        return list(self._entries)

    def inner_text(self, selector: str) -> str:
        return self._body_text

    def content(self) -> str:
        return self._body_text

    def title(self) -> str:
        return self._title_text

    def close(self) -> None:
        self.closed = True


class _FakeSession:
    def __init__(self, *, search_page: _FakePage, detail_pages: list[_FakePage]) -> None:
        self._search_page = search_page
        self._detail_pages = list(detail_pages)
        self.start_calls = 0
        self.get_or_create_page_calls = 0
        self.new_page_calls = 0
        self.close_calls = 0

    def start(self) -> None:
        self.start_calls += 1

    def get_or_create_page(self) -> _FakePage:
        self.get_or_create_page_calls += 1
        return self._search_page

    def new_page(self) -> _FakePage:
        self.new_page_calls += 1
        return self._detail_pages.pop(0)

    def close(self) -> None:
        self.close_calls += 1


class InstagramPlaywrightTests(unittest.TestCase):
    def test_normalize_candidate_url_unwraps_google_redirects(self) -> None:
        normalized = _normalize_candidate_url(
            "/url?q=https://www.instagram.com/creator-a/&sa=U&ved=2ah",
            base_url="https://www.google.com/search?q=ugc",
        )

        self.assertEqual(normalized, "https://www.instagram.com/creator-a/")

    def test_normalize_candidate_url_filters_non_instagram_targets(self) -> None:
        normalized = _normalize_candidate_url(
            "https://www.example.com/profile",
            base_url="https://www.google.com/search?q=ugc",
        )

        self.assertIsNone(normalized)

    def test_backend_reuses_one_session_and_search_page_across_searches(self) -> None:
        search_page = _FakePage(
            entries=[
                {"href": "/url?q=https://www.instagram.com/creator-a/&sa=U", "text": "Creator A"},
            ]
        )
        detail_pages = [
            _FakePage(
                url="https://www.instagram.com/creator-a/",
                body_text="creator@example.com ai educator",
                title_text="Creator A",
            ),
            _FakePage(
                url="https://www.instagram.com/creator-a/",
                body_text="creator@example.com ai educator",
                title_text="Creator A",
            ),
        ]
        fake_session = _FakeSession(search_page=search_page, detail_pages=detail_pages)

        with patch(
            "harnessiq.integrations.instagram_playwright.PlaywrightBrowserSession",
            return_value=fake_session,
        ):
            backend = PlaywrightInstagramSearchBackend(search_interval_seconds=0)
            first = backend.search_keyword(keyword="ai educator", max_results=1)
            second = backend.search_keyword(keyword="edtech creator", max_results=1)

        self.assertEqual(fake_session.start_calls, 1)
        self.assertEqual(fake_session.get_or_create_page_calls, 1)
        self.assertEqual(fake_session.new_page_calls, 2)
        self.assertEqual(len(search_page.goto_calls), 2)
        self.assertEqual(first.search_record.lead_count, 1)
        self.assertEqual(second.search_record.lead_count, 1)

    def test_backend_raises_explicit_error_for_google_sorry_page(self) -> None:
        search_page = _FakePage(
            url="https://www.google.com/sorry/index?continue=https://www.google.com/search?q=ugc",
            body_text="About this page. Our systems have detected unusual traffic. not a robot.",
        )
        fake_session = _FakeSession(search_page=search_page, detail_pages=[])

        with patch(
            "harnessiq.integrations.instagram_playwright.PlaywrightBrowserSession",
            return_value=fake_session,
        ):
            backend = PlaywrightInstagramSearchBackend(search_interval_seconds=0)
            with self.assertRaisesRegex(RuntimeError, "Google blocked Instagram discovery search"):
                backend.search_keyword(keyword="ai educator", max_results=1)

    def test_backend_close_releases_reusable_session(self) -> None:
        search_page = _FakePage()
        fake_session = _FakeSession(search_page=search_page, detail_pages=[])

        with patch(
            "harnessiq.integrations.instagram_playwright.PlaywrightBrowserSession",
            return_value=fake_session,
        ):
            backend = PlaywrightInstagramSearchBackend(search_interval_seconds=0)
            backend._session = fake_session
            backend._search_page = search_page
            backend.close()

        self.assertEqual(fake_session.close_calls, 1)
        self.assertIsNone(backend._session)
        self.assertIsNone(backend._search_page)


if __name__ == "__main__":
    unittest.main()
