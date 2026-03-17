"""Playwright-backed browser tool handlers for the LinkedIn agent.

Factory usage (CLI):
    --browser-tools-factory harnessiq.integrations.linkedin_playwright:create_browser_tools

Environment variables read by the factory:
    HARNESSIQ_BROWSER_SESSION_DIR — path to a persistent Playwright user-data
                                    directory (optional).  When set the browser
                                    reopens with the saved session so the user
                                    does not need to log in again.

The linkedin init-browser CLI command sets HARNESSIQ_BROWSER_SESSION_DIR to the
agent's memory path before calling the factory so the session is automatically
reused across runs.
"""

from __future__ import annotations

import base64
import os
from pathlib import Path
from typing import Any

from harnessiq.agents.linkedin import build_linkedin_browser_tool_definitions
from harnessiq.shared.tools import RegisteredTool

_LINKEDIN_LOGIN_URL = "https://www.linkedin.com/login"
_LINKEDIN_JOBS_URL = "https://www.linkedin.com/jobs/search/"

# HTML truncation limit — avoids sending enormous DOM payloads to the model.
_MAX_HTML_CHARS = 50_000
_MAX_TEXT_CHARS = 20_000


class PlaywrightLinkedInSession:
    """Manages a Playwright browser session for the LinkedIn job-applier agent.

    Uses a persistent user-data directory when `session_dir` is provided so
    that cookies and local-storage survive between agent runs.  On the first
    run (or whenever the user needs to re-authenticate) the browser navigates
    to the LinkedIn login page and waits for the user to press Enter before
    handing control to the agent.
    """

    def __init__(
        self,
        *,
        session_dir: str | Path | None = None,
        headless: bool = False,
    ) -> None:
        self._session_dir = Path(session_dir) if session_dir else None
        self._headless = headless
        self._pw: Any = None
        self._browser: Any = None
        self._context: Any = None
        self._page: Any = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Launch the browser, navigate to LinkedIn, and wait for the user to log in."""
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise RuntimeError(
                "playwright is required for browser tools.\n"
                "Install with: pip install playwright && python -m playwright install chromium"
            ) from exc

        self._pw = sync_playwright().start()

        print()
        print("=" * 64)
        print("  LINKEDIN BROWSER INITIALIZATION")
        print("=" * 64)

        if self._session_dir:
            self._session_dir.mkdir(parents=True, exist_ok=True)
            print(f"  Session dir : {self._session_dir}")
            # launch_persistent_context keeps cookies / localStorage on disk.
            self._context = self._pw.chromium.launch_persistent_context(
                str(self._session_dir),
                headless=self._headless,
                viewport={"width": 1280, "height": 900},
                args=["--start-maximized"],
            )
            self._page = (
                self._context.pages[0] if self._context.pages else self._context.new_page()
            )
        else:
            self._browser = self._pw.chromium.launch(
                headless=self._headless,
                args=["--start-maximized"],
            )
            self._context = self._browser.new_context(viewport={"width": 1280, "height": 900})
            self._page = self._context.new_page()

        print("  Opening LinkedIn login page …")
        self._page.goto(_LINKEDIN_LOGIN_URL, timeout=30_000)
        print()
        print("  ACTION REQUIRED")
        print("  ─────────────────────────────────────────────────────────")
        print("  1. Log in to LinkedIn in the browser window that opened.")
        print("  2. Once your feed / home page is visible, return here.")
        print("  3. Press Enter to hand control to the agent.")
        print("  ─────────────────────────────────────────────────────────")
        print()
        input("  Press Enter when logged in › ")
        print()
        print("  Login confirmed — agent starting.")
        print("=" * 64)
        print()

    def stop(self) -> None:
        """Close the browser and stop Playwright."""
        try:
            if self._context:
                self._context.close()
            if self._browser:
                self._browser.close()
            if self._pw:
                self._pw.stop()
        except Exception:
            pass

    @property
    def page(self) -> Any:
        if self._page is None:
            raise RuntimeError("Browser session has not been started.")
        return self._page

    # ------------------------------------------------------------------
    # Tool factory
    # ------------------------------------------------------------------

    def build_tools(self) -> tuple[RegisteredTool, ...]:
        """Return RegisteredTool instances backed by this live browser session."""
        definitions = build_linkedin_browser_tool_definitions()
        handlers: dict[str, Any] = {
            "navigate": self._handle_navigate,
            "click": self._handle_click,
            "type": self._handle_type,
            "select_option": self._handle_select_option,
            "hover": self._handle_hover,
            "upload_file": self._handle_upload_file,
            "press_key": self._handle_press_key,
            "scroll": self._handle_scroll,
            "wait_for_element": self._handle_wait_for_element,
            "screenshot": self._handle_screenshot,
            "view_html": self._handle_view_html,
            "get_text": self._handle_get_text,
            "find_element": self._handle_find_element,
            "get_current_url": self._handle_get_current_url,
        }
        return tuple(
            RegisteredTool(definition=defn, handler=handlers[defn.name])
            for defn in definitions
            if defn.name in handlers
        )

    # ------------------------------------------------------------------
    # Browser tool handlers
    # ------------------------------------------------------------------

    def _handle_navigate(self, arguments: dict[str, Any]) -> dict[str, Any]:
        url = str(arguments["url"])
        self.page.goto(url, timeout=30_000)
        return {"url": url, "status": "navigated", "current_url": self.page.url}

    def _handle_click(self, arguments: dict[str, Any]) -> dict[str, Any]:
        selector = str(arguments["selector"])
        try:
            self.page.click(selector, timeout=10_000)
            return {"selector": selector, "status": "clicked"}
        except Exception as exc:
            return {"selector": selector, "status": "error", "error": str(exc)}

    def _handle_type(self, arguments: dict[str, Any]) -> dict[str, Any]:
        selector = str(arguments["selector"])
        text = str(arguments["text"])
        self.page.fill(selector, "")
        self.page.type(selector, text)
        return {"selector": selector, "text": text, "status": "typed"}

    def _handle_select_option(self, arguments: dict[str, Any]) -> dict[str, Any]:
        selector = str(arguments["selector"])
        value = str(arguments["value"])
        self.page.select_option(selector, value)
        return {"selector": selector, "value": value, "status": "selected"}

    def _handle_hover(self, arguments: dict[str, Any]) -> dict[str, Any]:
        selector = str(arguments["selector"])
        try:
            self.page.hover(selector, timeout=10_000)
            return {"selector": selector, "status": "hovered"}
        except Exception as exc:
            return {"selector": selector, "status": "error", "error": str(exc)}

    def _handle_upload_file(self, arguments: dict[str, Any]) -> dict[str, Any]:
        selector = str(arguments["selector"])
        file_path = str(arguments["file_path"])
        self.page.set_input_files(selector, file_path)
        return {"selector": selector, "file_path": file_path, "status": "uploaded"}

    def _handle_press_key(self, arguments: dict[str, Any]) -> dict[str, Any]:
        key = str(arguments["key"])
        self.page.keyboard.press(key)
        return {"key": key, "status": "pressed"}

    def _handle_scroll(self, arguments: dict[str, Any]) -> dict[str, Any]:
        direction = str(arguments["direction"])
        amount = int(arguments["amount"])
        delta = amount if direction == "down" else -amount
        self.page.evaluate(f"window.scrollBy(0, {delta})")
        return {"direction": direction, "amount": amount, "status": "scrolled"}

    def _handle_wait_for_element(self, arguments: dict[str, Any]) -> dict[str, Any]:
        selector = str(arguments["selector"])
        timeout_ms = int(arguments.get("timeout_ms", 10_000))
        try:
            self.page.wait_for_selector(selector, timeout=timeout_ms)
            return {"selector": selector, "status": "found"}
        except Exception as exc:
            return {"selector": selector, "status": "timeout", "error": str(exc)}

    def _handle_screenshot(self, arguments: dict[str, Any]) -> dict[str, Any]:
        png_bytes: bytes = self.page.screenshot(full_page=False)
        b64 = base64.b64encode(png_bytes).decode("ascii")
        return {
            "url": self.page.url,
            "screenshot_base64_png": b64,
            "size_bytes": len(png_bytes),
        }

    def _handle_view_html(self, arguments: dict[str, Any]) -> dict[str, Any]:
        html: str = self.page.content()
        truncated = len(html) > _MAX_HTML_CHARS
        return {
            "html": html[:_MAX_HTML_CHARS] if truncated else html,
            "truncated": truncated,
            "total_chars": len(html),
        }

    def _handle_get_text(self, arguments: dict[str, Any]) -> dict[str, Any]:
        text: str = self.page.inner_text("body")
        truncated = len(text) > _MAX_TEXT_CHARS
        return {
            "text": text[:_MAX_TEXT_CHARS] if truncated else text,
            "truncated": truncated,
            "total_chars": len(text),
        }

    def _handle_find_element(self, arguments: dict[str, Any]) -> dict[str, Any]:
        selector = str(arguments["selector"])
        element = self.page.query_selector(selector)
        return {"selector": selector, "found": element is not None}

    def _handle_get_current_url(self, arguments: dict[str, Any]) -> dict[str, Any]:
        return {"url": self.page.url}


def create_browser_tools() -> tuple[RegisteredTool, ...]:
    """Factory for --browser-tools-factory CLI argument.

    Opens a Playwright Chromium browser, waits for the user to log in to
    LinkedIn, then returns live RegisteredTool instances backed by that
    browser session.

    Reads from environment:
        HARNESSIQ_BROWSER_SESSION_DIR — persistent session directory (optional).
                                        Set automatically by 'linkedin init-browser'.
    """
    session_dir_env = os.environ.get("HARNESSIQ_BROWSER_SESSION_DIR", "").strip()
    session_dir = Path(session_dir_env) if session_dir_env else None

    session = PlaywrightLinkedInSession(session_dir=session_dir)
    session.start()
    return session.build_tools()


__all__ = ["PlaywrightLinkedInSession", "create_browser_tools"]
