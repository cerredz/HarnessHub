"""Tests for the Instagram Playwright integration helpers."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from harnessiq.integrations.instagram_playwright import (
    PlaywrightInstagramSearchBackend,
    _normalize_candidate_url,
)
from harnessiq.shared.instagram import (
    DEFAULT_INSTAGRAM_BROWSER_INIT_SCRIPT,
    DEFAULT_INSTAGRAM_BROWSER_LAUNCH_ARGS,
    DEFAULT_INSTAGRAM_BROWSER_LOCALE,
    DEFAULT_INSTAGRAM_BROWSER_TIMEZONE_ID,
    DEFAULT_INSTAGRAM_BROWSER_USER_AGENT,
    DEFAULT_INSTAGRAM_HEADLESS,
    build_instagram_google_fallback_query,
    build_instagram_google_query,
    extract_emails,
)


class _FakePage:
    def __init__(
        self,
        *,
        url: str = "https://www.google.com/search?q=ugc",
        body_text: str = "",
        title_text: str = "",
        entries: list[dict[str, str]] | None = None,
        states: dict[str, dict[str, object]] | None = None,
    ) -> None:
        self.url = url
        self._body_text = body_text
        self._title_text = title_text
        self._entries = list(entries or [])
        self._states = dict(states or {})
        self.goto_calls: list[str] = []
        self.closed = False

    def goto(self, url: str, *, wait_until: str, timeout: int) -> None:
        self.goto_calls.append(url)
        self.url = url
        for pattern, state in self._states.items():
            if pattern in url:
                self._body_text = str(state.get("body_text", self._body_text))
                self._title_text = str(state.get("title_text", self._title_text))
                self._entries = list(state.get("entries", self._entries))
                break

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
    def test_build_instagram_google_query_uses_spaced_email_pattern(self) -> None:
        self.assertEqual(
            build_instagram_google_query("ai educator"),
            'site:instagram .com "@gmail .com" ai educator',
        )

    def test_extract_emails_normalizes_spaced_google_snippet_addresses(self) -> None:
        self.assertEqual(
            extract_emails("Reach me at Creator@Gmail .com or creator@gmail.com"),
            ["creator@gmail.com"],
        )

    def test_extract_emails_ignores_sentence_text_after_email(self) -> None:
        self.assertEqual(
            extract_emails("Collab: iamchonchol94@gmail.com. Sharing the latest updates."),
            ["iamchonchol94@gmail.com"],
        )

    def test_build_instagram_google_fallback_query_uses_google_operator_form(self) -> None:
        self.assertEqual(
            build_instagram_google_fallback_query("ai educator"),
            'site:instagram.com "@gmail.com" ai educator',
        )

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

    def test_normalize_candidate_url_canonicalizes_instagram_fallback_domain(self) -> None:
        normalized = _normalize_candidate_url(
            "https://www-fallback.instagram.com/creator-a/?hl=en",
            base_url="https://www.google.com/search?q=ugc",
        )

        self.assertEqual(normalized, "https://www.instagram.com/creator-a/")

    def test_backend_reuses_one_session_and_search_page_across_searches(self) -> None:
        search_page = _FakePage(
            entries=[
                {
                    "href": "/url?q=https://www.instagram.com/creator-a/&sa=U",
                    "title": "Creator A",
                    "snippet": "creator@gmail .com ai educator",
                    "text": "Creator A creator@gmail .com ai educator",
                },
            ]
        )
        fake_session = _FakeSession(search_page=search_page, detail_pages=[])

        with patch(
            "harnessiq.integrations.instagram_playwright.PlaywrightBrowserSession",
            return_value=fake_session,
        ):
            backend = PlaywrightInstagramSearchBackend(search_interval_seconds=0)
            first = backend.search_keyword(keyword="ai educator", max_results=1)
            second = backend.search_keyword(keyword="edtech creator", max_results=1)

        self.assertEqual(fake_session.start_calls, 1)
        self.assertEqual(fake_session.get_or_create_page_calls, 1)
        self.assertEqual(fake_session.new_page_calls, 0)
        self.assertEqual(len(search_page.goto_calls), 2)
        self.assertEqual(first.search_record.lead_count, 1)
        self.assertEqual(second.search_record.lead_count, 1)
        self.assertEqual(first.search_record.visited_urls, ("https://www.instagram.com/creator-a/",))
        self.assertEqual(first.leads[0].emails, ("creator@gmail.com",))
        self.assertEqual(first.leads[0].source_url, "https://www.instagram.com/creator-a/")

    def test_backend_falls_back_when_spaced_query_returns_no_results(self) -> None:
        search_page = _FakePage(
            states={
                'site%3Ainstagram+.com+%22%40gmail+.com%22+ai+educator': {
                    "body_text": (
                        "No results found for site:instagram .com \"@gmail .com\" ai educator. "
                        "Your search did not match any documents."
                    ),
                    "entries": [],
                },
                'site%3Ainstagram.com+%22%40gmail.com%22+ai+educator': {
                    "body_text": "Search Results Creator A creator@gmail.com",
                    "entries": [
                        {
                            "href": "/url?q=https://www.instagram.com/creator-a/&sa=U",
                            "title": "Creator A",
                            "snippet": "creator@gmail.com ai educator",
                            "text": "Creator A creator@gmail.com ai educator",
                        }
                    ],
                },
            }
        )
        fake_session = _FakeSession(search_page=search_page, detail_pages=[])

        with patch(
            "harnessiq.integrations.instagram_playwright.PlaywrightBrowserSession",
            return_value=fake_session,
        ):
            backend = PlaywrightInstagramSearchBackend(search_interval_seconds=0)
            result = backend.search_keyword(keyword="ai educator", max_results=1)

        self.assertEqual(len(search_page.goto_calls), 2)
        self.assertEqual(
            result.search_record.query,
            'site:instagram.com "@gmail.com" ai educator',
        )
        self.assertEqual(result.search_record.lead_count, 1)

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

    def test_backend_creates_hardened_headed_session(self) -> None:
        search_page = _FakePage(entries=[])
        fake_session = _FakeSession(search_page=search_page, detail_pages=[])

        with patch(
            "harnessiq.integrations.instagram_playwright.PlaywrightBrowserSession",
            return_value=fake_session,
        ) as session_ctor:
            backend = PlaywrightInstagramSearchBackend(search_interval_seconds=0)
            backend._get_session()

        session_ctor.assert_called_once()
        kwargs = session_ctor.call_args.kwargs
        self.assertEqual(kwargs["headless"], DEFAULT_INSTAGRAM_HEADLESS)
        self.assertEqual(kwargs["launch_args"], DEFAULT_INSTAGRAM_BROWSER_LAUNCH_ARGS)
        self.assertEqual(kwargs["init_scripts"], (DEFAULT_INSTAGRAM_BROWSER_INIT_SCRIPT,))
        self.assertEqual(kwargs["context_options"]["locale"], DEFAULT_INSTAGRAM_BROWSER_LOCALE)
        self.assertEqual(kwargs["context_options"]["timezone_id"], DEFAULT_INSTAGRAM_BROWSER_TIMEZONE_ID)
        self.assertEqual(kwargs["context_options"]["user_agent"], DEFAULT_INSTAGRAM_BROWSER_USER_AGENT)

    def test_backend_allows_explicit_session_hardening_overrides(self) -> None:
        search_page = _FakePage(entries=[])
        fake_session = _FakeSession(search_page=search_page, detail_pages=[])

        with patch(
            "harnessiq.integrations.instagram_playwright.PlaywrightBrowserSession",
            return_value=fake_session,
        ) as session_ctor:
            backend = PlaywrightInstagramSearchBackend(
                search_interval_seconds=0,
                headless=True,
                launch_args=("--custom-arg",),
                init_scripts=("window.__custom = true;",),
                context_options={"locale": "fr-FR", "user_agent": "CustomAgent/1.0"},
            )
            backend._get_session()

        kwargs = session_ctor.call_args.kwargs
        self.assertTrue(kwargs["headless"])
        self.assertEqual(kwargs["launch_args"], ("--custom-arg",))
        self.assertEqual(kwargs["init_scripts"], ("window.__custom = true;",))
        self.assertEqual(kwargs["context_options"], {"locale": "fr-FR", "user_agent": "CustomAgent/1.0"})


if __name__ == "__main__":
    unittest.main()
