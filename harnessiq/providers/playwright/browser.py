"""Reusable Playwright browser helpers for Harnessiq integrations."""

from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Any


class PlaywrightBrowserSession:
    """Manage a reusable Playwright runtime, browser, and context."""

    def __init__(
        self,
        *,
        session_dir: str | Path | None = None,
        channel: str,
        headless: bool,
        viewport: Mapping[str, int],
        import_error_message: str,
        launch_args: Sequence[str] = (),
        init_scripts: Sequence[str] = (),
    ) -> None:
        self._session_dir = Path(session_dir) if session_dir is not None else None
        self._channel = channel
        self._headless = headless
        self._viewport = dict(viewport)
        self._import_error_message = import_error_message
        self._launch_args = tuple(str(value) for value in launch_args)
        self._init_scripts = tuple(str(value) for value in init_scripts if str(value).strip())
        self._playwright: Any = None
        self._browser: Any = None
        self._context: Any = None

    @property
    def context(self) -> Any:
        if self._context is None:
            raise RuntimeError("Playwright browser session has not been started.")
        return self._context

    def start(self) -> None:
        """Start the Playwright runtime and Chromium context once."""
        if self._context is not None:
            return
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise RuntimeError(self._import_error_message) from exc

        self._playwright = sync_playwright().start()
        if self._session_dir is not None:
            self._session_dir.mkdir(parents=True, exist_ok=True)
            self._context = self._playwright.chromium.launch_persistent_context(
                str(self._session_dir),
                channel=self._channel,
                headless=self._headless,
                viewport=dict(self._viewport),
                args=list(self._launch_args),
            )
            self._browser = None
            self._apply_init_scripts()
            return
        self._browser = self._playwright.chromium.launch(
            channel=self._channel,
            headless=self._headless,
            args=list(self._launch_args),
        )
        self._context = self._browser.new_context(viewport=dict(self._viewport))
        self._apply_init_scripts()

    def get_or_create_page(self) -> Any:
        """Return the first existing page in the live context or create one."""
        return get_or_create_page(self.context)

    def new_page(self) -> Any:
        """Create a new page in the live context."""
        return self.context.new_page()

    def close(self) -> None:
        """Close the context, browser, and Playwright runtime safely."""
        try:
            if self._context is not None:
                self._context.close()
        finally:
            try:
                if self._browser is not None:
                    self._browser.close()
            finally:
                if self._playwright is not None:
                    self._playwright.stop()
        self._playwright = None
        self._browser = None
        self._context = None

    def _apply_init_scripts(self) -> None:
        if self._context is None:
            return
        for script in self._init_scripts:
            self._context.add_init_script(script)


@contextmanager
def playwright_runtime(*, import_error_message: str) -> Iterator[Any]:
    """Yield the Playwright runtime or raise a clear dependency error."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError(import_error_message) from exc

    with sync_playwright() as playwright:
        yield playwright


@contextmanager
def chromium_context(
    playwright: Any,
    *,
    session_dir: str | Path | None = None,
    channel: str,
    headless: bool,
    viewport: Mapping[str, int],
) -> Iterator[Any]:
    """Yield a Chromium browser context with optional persistent storage."""
    resolved_session_dir = Path(session_dir) if session_dir is not None else None
    if resolved_session_dir is not None:
        resolved_session_dir.mkdir(parents=True, exist_ok=True)
        context = playwright.chromium.launch_persistent_context(
            str(resolved_session_dir),
            channel=channel,
            headless=headless,
            viewport=dict(viewport),
        )
        browser = None
    else:
        browser = playwright.chromium.launch(channel=channel, headless=headless)
        context = browser.new_context(viewport=dict(viewport))

    try:
        yield context
    finally:
        context.close()
        if browser is not None:
            browser.close()


def get_or_create_page(context: Any) -> Any:
    """Return the first existing page in a context or create a new one."""
    return context.pages[0] if getattr(context, "pages", None) else context.new_page()


def goto_page(page: Any, *, url: str, timeout_ms: int, wait_until: str = "domcontentloaded") -> None:
    """Navigate a page to *url* with consistent timeout handling."""
    page.goto(url, wait_until=wait_until, timeout=timeout_ms)


def wait_for_page_ready(page: Any, *, timeout_ms: int, network_idle_timeout_ms: int) -> None:
    """Wait for a page's main load events and best-effort network idleness."""
    page.wait_for_load_state("domcontentloaded", timeout=timeout_ms)
    page.wait_for_load_state("load", timeout=timeout_ms)
    try:
        page.wait_for_load_state("networkidle", timeout=network_idle_timeout_ms)
    except Exception:
        pass


def read_page_text(page: Any, *, selector: str = "body") -> str:
    """Return page text, falling back to rendered HTML when inner_text fails."""
    try:
        return str(page.inner_text(selector))
    except Exception:
        return str(page.content())


def safe_page_title(page: Any) -> str:
    """Return a stripped page title or an empty string when unavailable."""
    try:
        return str(page.title()).strip()
    except Exception:
        return ""


__all__ = [
    "PlaywrightBrowserSession",
    "chromium_context",
    "get_or_create_page",
    "goto_page",
    "playwright_runtime",
    "read_page_text",
    "safe_page_title",
    "wait_for_page_ready",
]
