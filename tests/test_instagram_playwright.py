"""Tests for the Instagram Playwright integration helpers."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, call

from harnessiq.integrations.instagram_playwright import (
    PlaywrightInstagramSearchBackend,
    _normalize_candidate_url,
)


class InstagramPlaywrightTests(unittest.TestCase):
    def test_wait_for_page_ready_waits_for_dom_load_and_network_idle(self) -> None:
        page = MagicMock()
        backend = PlaywrightInstagramSearchBackend(timeout_ms=1234, network_idle_timeout_ms=567)

        backend._wait_for_page_ready(page)

        self.assertEqual(
            page.wait_for_load_state.call_args_list,
            [
                call("domcontentloaded", timeout=1234),
                call("load", timeout=1234),
                call("networkidle", timeout=567),
            ],
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


if __name__ == "__main__":
    unittest.main()
