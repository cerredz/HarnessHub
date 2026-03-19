"""Playwright-backed deterministic search backend for the Instagram discovery agent."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, quote_plus, urljoin, urlparse

from harnessiq.shared.instagram import (
    InstagramLeadRecord,
    InstagramSearchBackend,
    InstagramSearchExecution,
    InstagramSearchRecord,
    build_instagram_google_query,
    extract_emails,
)

_GOOGLE_SEARCH_URL = "https://www.google.com/search"
_DEFAULT_TIMEOUT_MS = 30_000
_NETWORK_IDLE_TIMEOUT_MS = 5_000


class PlaywrightInstagramSearchBackend:
    """Deterministic Google-to-Instagram search executor using Playwright."""

    def __init__(
        self,
        *,
        session_dir: str | Path | None = None,
        headless: bool = True,
        channel: str = "chrome",
        timeout_ms: int = _DEFAULT_TIMEOUT_MS,
        network_idle_timeout_ms: int = _NETWORK_IDLE_TIMEOUT_MS,
    ) -> None:
        self._session_dir = Path(session_dir) if session_dir else None
        self._headless = headless
        self._channel = channel
        self._timeout_ms = timeout_ms
        self._network_idle_timeout_ms = network_idle_timeout_ms

    def search_keyword(self, *, keyword: str, max_results: int) -> InstagramSearchExecution:
        query = build_instagram_google_query(keyword)
        search_url = f"{_GOOGLE_SEARCH_URL}?q={quote_plus(query)}"

        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise RuntimeError(
                "playwright is required for instagram search.\n"
                "Install with: pip install playwright && python -m playwright install chromium"
            ) from exc

        with sync_playwright() as playwright:
            if self._session_dir is not None:
                self._session_dir.mkdir(parents=True, exist_ok=True)
                context = playwright.chromium.launch_persistent_context(
                    str(self._session_dir),
                    channel=self._channel,
                    headless=self._headless,
                    viewport={"width": 1280, "height": 900},
                )
                browser = None
            else:
                browser = playwright.chromium.launch(channel=self._channel, headless=self._headless)
                context = browser.new_context(viewport={"width": 1280, "height": 900})

            try:
                search_page = context.pages[0] if context.pages else context.new_page()
                search_page.goto(search_url, wait_until="domcontentloaded", timeout=self._timeout_ms)
                self._wait_for_page_ready(search_page)

                candidate_urls = self._extract_instagram_urls(search_page, max_results=max_results)
                visited_urls: list[str] = []
                leads: list[InstagramLeadRecord] = []

                for url in candidate_urls:
                    detail_page = context.new_page()
                    try:
                        detail_page.goto(url, wait_until="domcontentloaded", timeout=self._timeout_ms)
                        self._wait_for_page_ready(detail_page)
                        visited_urls.append(detail_page.url)
                        text = self._read_page_text(detail_page)
                        emails = extract_emails(text)
                        if not emails:
                            continue
                        leads.append(
                            InstagramLeadRecord(
                                source_url=detail_page.url,
                                source_keyword=keyword,
                                found_at=_utcnow(),
                                emails=tuple(emails),
                                title=self._safe_title(detail_page),
                                snippet=text[:500].strip(),
                            )
                        )
                    finally:
                        detail_page.close()

                email_count = sum(len(lead.emails) for lead in leads)
                search_record = InstagramSearchRecord(
                    keyword=keyword,
                    query=query,
                    searched_at=_utcnow(),
                    visited_urls=tuple(visited_urls),
                    lead_count=len(leads),
                    email_count=email_count,
                )
                return InstagramSearchExecution(search_record=search_record, leads=tuple(leads))
            finally:
                context.close()
                if browser is not None:
                    browser.close()

    def _wait_for_page_ready(self, page: Any) -> None:
        page.wait_for_load_state("domcontentloaded", timeout=self._timeout_ms)
        page.wait_for_load_state("load", timeout=self._timeout_ms)
        try:
            page.wait_for_load_state("networkidle", timeout=self._network_idle_timeout_ms)
        except Exception:
            pass

    def _extract_instagram_urls(self, page: Any, *, max_results: int) -> list[str]:
        raw_entries = page.eval_on_selector_all(
            "a[href]",
            """
            elements => elements.map(element => ({
                href: element.getAttribute('href') || '',
                text: (element.innerText || '').trim()
            }))
            """,
        )
        result: list[str] = []
        for entry in raw_entries:
            normalized = _normalize_candidate_url(str(entry.get("href", "")), base_url=page.url)
            if normalized is None or normalized in result:
                continue
            result.append(normalized)
            if len(result) >= max_results:
                break
        return result

    def _read_page_text(self, page: Any) -> str:
        try:
            return str(page.inner_text("body"))
        except Exception:
            return str(page.content())

    def _safe_title(self, page: Any) -> str:
        try:
            return str(page.title()).strip()
        except Exception:
            return ""


def create_search_backend() -> InstagramSearchBackend:
    """Factory for CLI usage via --search-backend-factory."""
    session_dir_env = os.environ.get("HARNESSIQ_INSTAGRAM_SESSION_DIR", "").strip()
    channel = os.environ.get("HARNESSIQ_INSTAGRAM_BROWSER_CHANNEL", "chrome").strip() or "chrome"
    headless = _parse_bool(os.environ.get("HARNESSIQ_INSTAGRAM_HEADLESS"), default=True)
    session_dir = Path(session_dir_env) if session_dir_env else None
    return PlaywrightInstagramSearchBackend(
        session_dir=session_dir,
        channel=channel,
        headless=headless,
    )


def _normalize_candidate_url(raw_url: str, *, base_url: str) -> str | None:
    candidate = raw_url.strip()
    if not candidate:
        return None
    if candidate.startswith("/url?"):
        query_payload = parse_qs(urlparse(candidate).query)
        candidate = str(query_payload.get("q", [""])[0]).strip()
    candidate = urljoin(base_url, candidate)
    parsed = urlparse(candidate)
    if parsed.scheme not in {"http", "https"}:
        return None
    if "instagram.com" not in parsed.netloc.lower():
        return None
    return parsed._replace(fragment="").geturl()


def _parse_bool(value: str | None, *, default: bool) -> bool:
    if value is None:
        return default
    normalized = value.strip().lower()
    if not normalized:
        return default
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"Unsupported boolean value '{value}'.")


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


__all__ = ["PlaywrightInstagramSearchBackend", "create_search_backend"]
