"""Tests for the Instagram Playwright integration helpers."""

from __future__ import annotations

import unittest

from harnessiq.integrations.instagram_playwright import (
    _normalize_candidate_url,
)


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


if __name__ == "__main__":
    unittest.main()
