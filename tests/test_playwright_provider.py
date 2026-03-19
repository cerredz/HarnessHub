"""Tests for shared Playwright provider helpers."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, call

from harnessiq.providers.playwright import read_page_text, safe_page_title, wait_for_page_ready


class PlaywrightProviderTests(unittest.TestCase):
    def test_wait_for_page_ready_waits_for_dom_load_and_network_idle(self) -> None:
        page = MagicMock()

        wait_for_page_ready(page, timeout_ms=1234, network_idle_timeout_ms=567)

        self.assertEqual(
            page.wait_for_load_state.call_args_list,
            [
                call("domcontentloaded", timeout=1234),
                call("load", timeout=1234),
                call("networkidle", timeout=567),
            ],
        )

    def test_read_page_text_falls_back_to_page_content(self) -> None:
        page = MagicMock()
        page.inner_text.side_effect = RuntimeError("boom")
        page.content.return_value = "<html>fallback</html>"

        self.assertEqual(read_page_text(page), "<html>fallback</html>")

    def test_safe_page_title_returns_empty_string_on_error(self) -> None:
        page = MagicMock()
        page.title.side_effect = RuntimeError("boom")

        self.assertEqual(safe_page_title(page), "")


if __name__ == "__main__":
    unittest.main()
