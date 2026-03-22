"""Playwright-backed deterministic search backend for the Instagram discovery agent."""

from __future__ import annotations

import os
import time
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, quote_plus, urljoin, urlparse

from harnessiq.providers.playwright import (
    PlaywrightBrowserSession,
    goto_page,
    read_page_text,
    wait_for_page_ready,
)
from harnessiq.shared.instagram import (
    DEFAULT_INSTAGRAM_BROWSER_CHANNEL,
    DEFAULT_INSTAGRAM_BROWSER_INIT_SCRIPT,
    DEFAULT_INSTAGRAM_BROWSER_LAUNCH_ARGS,
    DEFAULT_INSTAGRAM_BROWSER_VIEWPORT,
    DEFAULT_INSTAGRAM_HEADLESS,
    DEFAULT_INSTAGRAM_NETWORK_IDLE_TIMEOUT_MS,
    DEFAULT_INSTAGRAM_TIMEOUT_MS,
    INSTAGRAM_GOOGLE_SEARCH_URL,
    InstagramLeadRecord,
    InstagramSearchBackend,
    InstagramSearchExecution,
    InstagramSearchRecord,
    build_instagram_google_fallback_query,
    build_instagram_google_query,
    extract_emails,
)

_DEFAULT_IMPORT_ERROR_MESSAGE = (
    "playwright is required for instagram search.\n"
    "Install with: pip install playwright && python -m playwright install chromium"
)
_DEFAULT_SEARCH_INTERVAL_SECONDS = 2.0


class PlaywrightInstagramSearchBackend:
    """Deterministic Google-to-Instagram search executor using Playwright."""

    def __init__(
        self,
        *,
        session_dir: str | Path | None = None,
        headless: bool = DEFAULT_INSTAGRAM_HEADLESS,
        channel: str = DEFAULT_INSTAGRAM_BROWSER_CHANNEL,
        timeout_ms: int = DEFAULT_INSTAGRAM_TIMEOUT_MS,
        network_idle_timeout_ms: int = DEFAULT_INSTAGRAM_NETWORK_IDLE_TIMEOUT_MS,
        search_interval_seconds: float = _DEFAULT_SEARCH_INTERVAL_SECONDS,
        launch_args: Sequence[str] | None = None,
        init_scripts: Sequence[str] | None = None,
    ) -> None:
        self._session_dir = Path(session_dir) if session_dir else None
        self._headless = headless
        self._channel = channel
        self._timeout_ms = timeout_ms
        self._network_idle_timeout_ms = network_idle_timeout_ms
        self._search_interval_seconds = max(0.0, float(search_interval_seconds))
        self._launch_args = (
            tuple(str(value) for value in launch_args)
            if launch_args is not None
            else DEFAULT_INSTAGRAM_BROWSER_LAUNCH_ARGS
        )
        self._init_scripts = (
            tuple(str(value) for value in init_scripts if str(value).strip())
            if init_scripts is not None
            else (DEFAULT_INSTAGRAM_BROWSER_INIT_SCRIPT,)
        )
        self._session: PlaywrightBrowserSession | None = None
        self._search_page: Any = None
        self._last_search_started_at: float | None = None

    def search_keyword(self, *, keyword: str, max_results: int) -> InstagramSearchExecution:
        query = build_instagram_google_query(keyword)
        self._wait_for_next_search_slot()
        self._last_search_started_at = time.monotonic()

        search_page = self._get_search_page()
        executed_query = self._load_query(search_page, keyword=keyword, query=query)

        result_entries = self._extract_google_result_entries(search_page, max_results=max_results)
        visited_urls = [entry["source_url"] for entry in result_entries]
        leads: list[InstagramLeadRecord] = []

        for entry in result_entries:
            text = "\n".join(
                part for part in (entry["title"], entry["snippet"], entry["text"]) if part
            ).strip()
            emails = extract_emails(text)
            if not emails:
                continue
            leads.append(
                InstagramLeadRecord(
                    source_url=entry["source_url"],
                    source_keyword=keyword,
                    found_at=_utcnow(),
                    emails=tuple(emails),
                    title=entry["title"],
                    snippet=(entry["snippet"] or entry["text"])[:500].strip(),
                )
            )

        email_count = sum(len(lead.emails) for lead in leads)
        search_record = InstagramSearchRecord(
            keyword=keyword,
            query=executed_query,
            searched_at=_utcnow(),
            visited_urls=tuple(visited_urls),
            lead_count=len(leads),
            email_count=email_count,
        )
        return InstagramSearchExecution(search_record=search_record, leads=tuple(leads))

    def close(self) -> None:
        """Close the reusable browser session held by the backend."""
        if self._session is not None:
            self._session.close()
        self._session = None
        self._search_page = None
        self._last_search_started_at = None

    def _get_session(self) -> PlaywrightBrowserSession:
        if self._session is None:
            session = PlaywrightBrowserSession(
                session_dir=self._session_dir,
                channel=self._channel,
                headless=self._headless,
                viewport=DEFAULT_INSTAGRAM_BROWSER_VIEWPORT,
                import_error_message=_DEFAULT_IMPORT_ERROR_MESSAGE,
                launch_args=self._launch_args,
                init_scripts=self._init_scripts,
            )
            session.start()
            self._session = session
        return self._session

    def _get_search_page(self) -> Any:
        if self._search_page is None:
            self._search_page = self._get_session().get_or_create_page()
        return self._search_page

    def _wait_for_next_search_slot(self) -> None:
        if self._last_search_started_at is None or self._search_interval_seconds <= 0:
            return
        elapsed = time.monotonic() - self._last_search_started_at
        remaining = self._search_interval_seconds - elapsed
        if remaining > 0:
            time.sleep(remaining)

    def _raise_if_google_blocked(self, page: Any, *, keyword: str) -> None:
        current_url = str(getattr(page, "url", ""))
        if "google.com/sorry/" in current_url:
            raise RuntimeError(
                f"Google blocked Instagram discovery search for keyword '{keyword}' with a "
                f"sorry interstitial at '{current_url}'."
            )
        body_text = read_page_text(page).lower()
        if "unusual traffic" in body_text and "not a robot" in body_text:
            raise RuntimeError(
                f"Google blocked Instagram discovery search for keyword '{keyword}' with an "
                "anti-bot interstitial."
            )

    def _load_query(self, page: Any, *, keyword: str, query: str) -> str:
        self._navigate_to_query(page, query=query)
        self._raise_if_google_blocked(page, keyword=keyword)
        if self._has_no_search_results(page):
            fallback_query = build_instagram_google_fallback_query(keyword)
            if fallback_query != query:
                self._navigate_to_query(page, query=fallback_query)
                self._raise_if_google_blocked(page, keyword=keyword)
                return fallback_query
        return query

    def _navigate_to_query(self, page: Any, *, query: str) -> None:
        search_url = f"{INSTAGRAM_GOOGLE_SEARCH_URL}?q={quote_plus(query)}"
        goto_page(page, url=search_url, timeout_ms=self._timeout_ms)
        wait_for_page_ready(
            page,
            timeout_ms=self._timeout_ms,
            network_idle_timeout_ms=self._network_idle_timeout_ms,
        )

    def _has_no_search_results(self, page: Any) -> bool:
        body_text = read_page_text(page).lower()
        return "no results found for" in body_text or "your search did not match any documents" in body_text

    def _extract_google_result_entries(self, page: Any, *, max_results: int) -> list[dict[str, str]]:
        raw_entries = page.eval_on_selector_all(
            "a[href]",
            """
            elements => elements.map(element => ({
                href: element.getAttribute('href') || '',
                title: (
                    element.closest('div[data-ved], div.g, div.Gx5Zad, div.tF2Cxc')?.querySelector('h3')?.innerText
                    || ''
                ).trim(),
                snippet: (
                    element.closest('div[data-ved], div.g, div.Gx5Zad, div.tF2Cxc')
                        ?.querySelector('.VwiC3b, .yXK7lf, .MUxGbd, [data-sncf="1"]')
                        ?.innerText
                    || ''
                ).trim(),
                text: (
                    element.closest('div[data-ved], div.g, div.Gx5Zad, div.tF2Cxc')?.innerText
                    || element.innerText
                    || ''
                ).trim()
            }))
            """,
        )
        result: list[dict[str, str]] = []
        for entry in raw_entries:
            normalized = _normalize_candidate_url(str(entry.get("href", "")), base_url=page.url)
            if normalized is None or any(item["source_url"] == normalized for item in result):
                continue
            result.append(
                {
                    "source_url": normalized,
                    "title": str(entry.get("title", "")).strip(),
                    "snippet": str(entry.get("snippet", "")).strip(),
                    "text": str(entry.get("text", "")).strip(),
                }
            )
            if len(result) >= max_results:
                break
        return result


def create_search_backend() -> InstagramSearchBackend:
    """Factory for CLI usage via --search-backend-factory."""
    session_dir_env = os.environ.get("HARNESSIQ_INSTAGRAM_SESSION_DIR", "").strip()
    channel = (
        os.environ.get("HARNESSIQ_INSTAGRAM_BROWSER_CHANNEL", DEFAULT_INSTAGRAM_BROWSER_CHANNEL).strip()
        or DEFAULT_INSTAGRAM_BROWSER_CHANNEL
    )
    headless = _parse_bool(os.environ.get("HARNESSIQ_INSTAGRAM_HEADLESS"), default=DEFAULT_INSTAGRAM_HEADLESS)
    hardening_disabled = _parse_bool(
        os.environ.get("HARNESSIQ_INSTAGRAM_DISABLE_BROWSER_HARDENING"),
        default=False,
    )
    session_dir = Path(session_dir_env) if session_dir_env else None
    return PlaywrightInstagramSearchBackend(
        session_dir=session_dir,
        channel=channel,
        headless=headless,
        search_interval_seconds=_parse_float(
            os.environ.get("HARNESSIQ_INSTAGRAM_SEARCH_INTERVAL_SECONDS"),
            default=_DEFAULT_SEARCH_INTERVAL_SECONDS,
        ),
        launch_args=() if hardening_disabled else None,
        init_scripts=() if hardening_disabled else None,
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
    normalized_netloc = parsed.netloc.lower()
    if "instagram.com" not in normalized_netloc:
        return None
    if normalized_netloc.endswith("instagram.com"):
        normalized_netloc = "www.instagram.com"
    normalized_path = parsed.path or "/"
    return parsed._replace(netloc=normalized_netloc, path=normalized_path, query="", fragment="").geturl()


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


def _parse_float(value: str | None, *, default: float) -> float:
    if value is None:
        return default
    normalized = value.strip()
    if not normalized:
        return default
    return float(normalized)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


__all__ = ["PlaywrightInstagramSearchBackend", "create_search_backend"]
