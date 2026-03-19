"""Playwright-backed deterministic search backend for the Instagram discovery agent."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, quote_plus, urljoin, urlparse

from harnessiq.providers.playwright import (
    chromium_context,
    get_or_create_page,
    goto_page,
    playwright_runtime,
    read_page_text,
    safe_page_title,
    wait_for_page_ready,
)
from harnessiq.shared.instagram import (
    DEFAULT_INSTAGRAM_BROWSER_CHANNEL,
    DEFAULT_INSTAGRAM_BROWSER_VIEWPORT,
    DEFAULT_INSTAGRAM_NETWORK_IDLE_TIMEOUT_MS,
    DEFAULT_INSTAGRAM_TIMEOUT_MS,
    INSTAGRAM_GOOGLE_SEARCH_URL,
    InstagramLeadRecord,
    InstagramSearchBackend,
    InstagramSearchExecution,
    InstagramSearchRecord,
    build_instagram_google_query,
    extract_emails,
)


class PlaywrightInstagramSearchBackend:
    """Deterministic Google-to-Instagram search executor using Playwright."""

    def __init__(
        self,
        *,
        session_dir: str | Path | None = None,
        headless: bool = True,
        channel: str = DEFAULT_INSTAGRAM_BROWSER_CHANNEL,
        timeout_ms: int = DEFAULT_INSTAGRAM_TIMEOUT_MS,
        network_idle_timeout_ms: int = DEFAULT_INSTAGRAM_NETWORK_IDLE_TIMEOUT_MS,
    ) -> None:
        self._session_dir = Path(session_dir) if session_dir else None
        self._headless = headless
        self._channel = channel
        self._timeout_ms = timeout_ms
        self._network_idle_timeout_ms = network_idle_timeout_ms

    def search_keyword(self, *, keyword: str, max_results: int) -> InstagramSearchExecution:
        query = build_instagram_google_query(keyword)
        search_url = f"{INSTAGRAM_GOOGLE_SEARCH_URL}?q={quote_plus(query)}"

        with playwright_runtime(
            import_error_message=(
                "playwright is required for instagram search.\n"
                "Install with: pip install playwright && python -m playwright install chromium"
            )
        ) as playwright:
            with chromium_context(
                playwright,
                session_dir=self._session_dir,
                channel=self._channel,
                headless=self._headless,
                viewport=DEFAULT_INSTAGRAM_BROWSER_VIEWPORT,
            ) as context:
                search_page = get_or_create_page(context)
                goto_page(search_page, url=search_url, timeout_ms=self._timeout_ms)
                wait_for_page_ready(
                    search_page,
                    timeout_ms=self._timeout_ms,
                    network_idle_timeout_ms=self._network_idle_timeout_ms,
                )
                candidate_urls = self._extract_instagram_urls(search_page, max_results=max_results)
                visited_urls: list[str] = []
                leads: list[InstagramLeadRecord] = []

                for url in candidate_urls:
                    detail_page = context.new_page()
                    try:
                        goto_page(detail_page, url=url, timeout_ms=self._timeout_ms)
                        wait_for_page_ready(
                            detail_page,
                            timeout_ms=self._timeout_ms,
                            network_idle_timeout_ms=self._network_idle_timeout_ms,
                        )
                        visited_urls.append(detail_page.url)
                        text = read_page_text(detail_page)
                        emails = extract_emails(text)
                        if not emails:
                            continue
                        leads.append(
                            InstagramLeadRecord(
                                source_url=detail_page.url,
                                source_keyword=keyword,
                                found_at=_utcnow(),
                                emails=tuple(emails),
                                title=safe_page_title(detail_page),
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


def create_search_backend() -> InstagramSearchBackend:
    """Factory for CLI usage via --search-backend-factory."""
    session_dir_env = os.environ.get("HARNESSIQ_INSTAGRAM_SESSION_DIR", "").strip()
    channel = (
        os.environ.get("HARNESSIQ_INSTAGRAM_BROWSER_CHANNEL", DEFAULT_INSTAGRAM_BROWSER_CHANNEL).strip()
        or DEFAULT_INSTAGRAM_BROWSER_CHANNEL
    )
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
