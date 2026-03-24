"""Playwright-backed browser tool handlers for the Google Maps prospecting agent."""

from __future__ import annotations

import base64
import os
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from harnessiq.shared.tools import RegisteredTool
from harnessiq.tools.browser import create_browser_tools as create_registered_browser_tools

_DEFAULT_TIMEOUT_MS = 30_000
_NETWORK_IDLE_TIMEOUT_MS = 5_000
_MAX_HTML_CHARS = 50_000
_MAX_TEXT_CHARS = 20_000
_SEARCH_RESULTS_SCRIPT = """
elements => elements.map((element, index) => {
  const container = element.closest('div.Nv2PK') || element.closest('div[role="article"]') || element.parentElement;
  const text = ((container && container.innerText) || element.innerText || '').trim();
  const href = element.href || '';
  const ariaLabel = (element.getAttribute('aria-label') || '').trim();
  const ratingNode = container ? container.querySelector('.MW4etd') : null;
  const ratingText = ratingNode ? (ratingNode.textContent || '').trim() : '';
  const ratingMatch = (ratingText || text).match(/(\\d\\.\\d)/);
  const reviewMatch = text.match(/([\\d,]+)\\s+reviews?/i);
  const lines = text
    .split('\\n')
    .map(line => line.trim())
    .filter(Boolean)
    .filter(line => line !== 'Website' && line !== 'Directions');
  const name = ariaLabel || lines[0] || '';
  const detailLines = lines.filter(line => line !== name && line !== ratingText);
  const primaryDetail = detailLines[0] || '';
  const secondaryDetail = detailLines[1] || '';
  const primaryParts = primaryDetail.split('?').map(part => part.trim()).filter(Boolean);
  const secondaryParts = secondaryDetail.split('?').map(part => part.trim()).filter(Boolean);
  const address = primaryParts.length > 1 ? primaryParts.slice(1).join(' ? ') : '';
  const phoneCandidate = secondaryParts[secondaryParts.length - 1] || '';
  return {
    rank: index + 1,
    name,
    category: primaryParts[0] || '',
    address,
    status_text: secondaryParts[0] || '',
    phone: /\\(?\\d{3}\\)?[-\\s]?\\d{3}[-\\s]?\\d{4}/.test(phoneCandidate) ? phoneCandidate : '',
    rating_text: ratingMatch ? ratingMatch[1] : '',
    review_count_text: reviewMatch ? reviewMatch[1] : '',
    maps_url: href,
    text,
  };
})
"""


class PlaywrightGoogleMapsSession:
    """Manage a Playwright browser session for Google Maps prospecting."""

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
        self._pw: Any = None
        self._browser: Any = None
        self._context: Any = None
        self._page: Any = None

    @property
    def page(self) -> Any:
        if self._page is None:
            raise RuntimeError("Browser session has not been started.")
        return self._page

    def start(self) -> None:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise RuntimeError(
                "playwright is required for Google Maps browser tools.\n"
                "Install with: pip install playwright && python -m playwright install chromium"
            ) from exc

        self._pw = sync_playwright().start()
        if self._session_dir is not None:
            self._session_dir.mkdir(parents=True, exist_ok=True)
            self._context = self._pw.chromium.launch_persistent_context(
                str(self._session_dir),
                channel=self._channel,
                headless=self._headless,
                viewport={"width": 1440, "height": 960},
            )
            self._page = self._context.pages[0] if self._context.pages else self._context.new_page()
        else:
            self._browser = self._pw.chromium.launch(
                channel=self._channel,
                headless=self._headless,
            )
            self._context = self._browser.new_context(viewport={"width": 1440, "height": 960})
            self._page = self._context.new_page()

    def stop(self) -> None:
        try:
            if self._context is not None:
                self._context.close()
            if self._browser is not None:
                self._browser.close()
            if self._pw is not None:
                self._pw.stop()
        except Exception:
            pass

    def build_tools(self) -> tuple[RegisteredTool, ...]:
        return create_registered_browser_tools(
            handlers={
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
                "extract_content": self._handle_extract_content,
            }
        )

    def _handle_navigate(self, arguments: dict[str, Any]) -> dict[str, Any]:
        url = str(arguments["url"])
        self.page.goto(url, wait_until="domcontentloaded", timeout=self._timeout_ms)
        self._wait_for_page_ready(self.page)
        return {"url": url, "current_url": self.page.url, "status": "navigated"}

    def _handle_click(self, arguments: dict[str, Any]) -> dict[str, Any]:
        selector = str(arguments["selector"])
        self.page.click(selector, timeout=10_000)
        return {"selector": selector, "status": "clicked"}

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
        self.page.hover(selector, timeout=10_000)
        return {"selector": selector, "status": "hovered"}

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
        del arguments
        png_bytes: bytes = self.page.screenshot(full_page=False)
        return {
            "url": self.page.url,
            "screenshot_base64_png": base64.b64encode(png_bytes).decode("ascii"),
            "size_bytes": len(png_bytes),
        }

    def _handle_view_html(self, arguments: dict[str, Any]) -> dict[str, Any]:
        del arguments
        html = self.page.content()
        truncated = len(html) > _MAX_HTML_CHARS
        return {
            "html": html[:_MAX_HTML_CHARS] if truncated else html,
            "truncated": truncated,
            "total_chars": len(html),
        }

    def _handle_get_text(self, arguments: dict[str, Any]) -> dict[str, Any]:
        del arguments
        text = self._read_page_text(self.page)
        truncated = len(text) > _MAX_TEXT_CHARS
        return {
            "text": text[:_MAX_TEXT_CHARS] if truncated else text,
            "truncated": truncated,
            "total_chars": len(text),
        }

    def _handle_find_element(self, arguments: dict[str, Any]) -> dict[str, Any]:
        selector = str(arguments["selector"])
        return {"selector": selector, "found": self.page.query_selector(selector) is not None}

    def _handle_get_current_url(self, arguments: dict[str, Any]) -> dict[str, Any]:
        del arguments
        return {"url": self.page.url}

    def _handle_extract_content(self, arguments: dict[str, Any]) -> dict[str, Any]:
        mode = str(arguments["mode"])
        max_items = int(arguments.get("max_items", 10))
        if mode == "maps_search_results":
            return self._extract_maps_search_results(max_items=max_items)
        if mode == "maps_place_details":
            return self._extract_maps_place_details()
        if mode == "website_quality_snapshot":
            return self._extract_website_quality_snapshot()
        raise ValueError(f"Unsupported browser extract_content mode '{mode}'.")

    def _wait_for_page_ready(self, page: Any) -> None:
        page.wait_for_load_state("domcontentloaded", timeout=self._timeout_ms)
        page.wait_for_load_state("load", timeout=self._timeout_ms)
        try:
            page.wait_for_load_state("networkidle", timeout=self._network_idle_timeout_ms)
        except Exception:
            pass

    def _extract_maps_search_results(self, *, max_items: int) -> dict[str, Any]:
        raw_entries = self.page.eval_on_selector_all('a[href*="/maps/place"], a[href*="google.com/maps/place"]', _SEARCH_RESULTS_SCRIPT)
        results: list[dict[str, Any]] = []
        seen_urls: set[str] = set()
        top_competitor_review_count = 0
        for entry in raw_entries:
            maps_url = str(entry.get("maps_url", "")).strip()
            if not maps_url or maps_url in seen_urls:
                continue
            seen_urls.add(maps_url)
            review_count = _safe_int(entry.get("review_count_text"))
            top_competitor_review_count = max(top_competitor_review_count, review_count)
            results.append(
                {
                    "rank": int(entry.get("rank", len(results) + 1)),
                    "name": str(entry.get("name", "")).strip(),
                    "category": str(entry.get("category", "")).strip(),
                    "address": str(entry.get("address", "")).strip(),
                    "status_text": str(entry.get("status_text", "")).strip(),
                    "phone": str(entry.get("phone", "")).strip(),
                    "rating": _safe_float(entry.get("rating_text")),
                    "review_count": review_count,
                    "maps_url": maps_url,
                    "top_competitor_review_count": review_count,
                }
            )
            if len(results) >= max_items:
                break
        for result in results:
            result["top_competitor_review_count"] = top_competitor_review_count
        return {"results": results, "count": len(results), "url": self.page.url}

    def _extract_maps_place_details(self) -> dict[str, Any]:
        page_text = self._read_page_text(self.page)
        links = self.page.eval_on_selector_all("a[href]", "elements => elements.map(element => element.href || '')")
        website_url = _pick_website_url(links)
        status = _extract_status(page_text)
        details = {
            "name": self._safe_title(self.page),
            "category": _extract_category(page_text),
            "rating": _extract_rating(page_text),
            "review_count": _extract_review_count(page_text),
            "last_review_date": _extract_last_review_date(page_text),
            "owner_responds_to_reviews": "owner response" in page_text.lower() or "response from the owner" in page_text.lower(),
            "google_posts_present": "updates" in page_text.lower() or "posts" in page_text.lower(),
            "website_url": website_url,
            "description_present": "from " in page_text.lower() or "about" in page_text.lower(),
            "photos_beyond_streetview": self._count_images() > 3,
            "qa_answered": "questions & answers" in page_text.lower() and "answer" in page_text.lower(),
            "maps_url": self.page.url,
            "chain_indicator": _is_probable_chain(self._safe_title(self.page), website_url, page_text),
            "status": status,
            "closed": status in {"temporarily_closed", "permanently_closed"},
        }
        return details

    def _extract_website_quality_snapshot(self) -> dict[str, Any]:
        page_text = self._read_page_text(self.page)
        metrics = self.page.evaluate(
            """() => ({
                title: document.title || '',
                imageCount: document.images.length,
                hasViewport: !!document.querySelector('meta[name="viewport"]'),
                hasNav: !!document.querySelector('nav'),
                hasForm: !!document.querySelector('form'),
                linkCount: document.querySelectorAll('a[href]').length,
            })"""
        )
        assessment = _assess_website_quality(metrics, page_text, self.page.url)
        return {
            "url": self.page.url,
            "title": str(metrics.get("title", "")).strip(),
            "has_viewport_meta": bool(metrics.get("hasViewport")),
            "image_count": int(metrics.get("imageCount", 0)),
            "link_count": int(metrics.get("linkCount", 0)),
            "has_nav": bool(metrics.get("hasNav")),
            "has_form": bool(metrics.get("hasForm")),
            "website_quality_assessment": assessment,
        }

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

    def _count_images(self) -> int:
        try:
            return int(self.page.eval_on_selector_all("img", "elements => elements.length"))
        except Exception:
            return 0


def create_browser_tools() -> tuple[RegisteredTool, ...]:
    session_dir_env = os.environ.get("HARNESSIQ_PROSPECTING_SESSION_DIR", "").strip()
    channel = os.environ.get("HARNESSIQ_PROSPECTING_BROWSER_CHANNEL", "chrome").strip() or "chrome"
    headless = _parse_bool(os.environ.get("HARNESSIQ_PROSPECTING_HEADLESS"), default=True)
    session = PlaywrightGoogleMapsSession(
        session_dir=Path(session_dir_env) if session_dir_env else None,
        channel=channel,
        headless=headless,
    )
    session.start()
    return session.build_tools()


def _safe_int(value: Any) -> int:
    text = str(value or "").replace(",", "").strip()
    return int(text) if text.isdigit() else 0


def _safe_float(value: Any) -> float | None:
    text = str(value or "").strip()
    try:
        return float(text)
    except ValueError:
        return None


def _extract_rating(text: str) -> float | None:
    match = re.search(r"(\d\.\d)", text)
    return float(match.group(1)) if match else None


def _extract_review_count(text: str) -> int:
    match = re.search(r"([\d,]+)\s+reviews?", text, re.IGNORECASE)
    return int(match.group(1).replace(",", "")) if match else 0


def _extract_last_review_date(text: str) -> str | None:
    match = re.search(r"([A-Z][a-z]+ \d{1,2}, \d{4})", text)
    return match.group(1) if match else None


def _extract_status(text: str) -> str:
    lowered = text.lower()
    if "permanently closed" in lowered:
        return "permanently_closed"
    if "temporarily closed" in lowered:
        return "temporarily_closed"
    return "open"


def _extract_category(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return lines[1] if len(lines) > 1 else ""


def _pick_website_url(links: list[str]) -> str | None:
    for link in links:
        parsed = urlparse(str(link))
        if parsed.scheme not in {"http", "https"}:
            continue
        hostname = parsed.netloc.lower()
        if not hostname or "google." in hostname or "gstatic." in hostname:
            continue
        return str(link)
    return None


def _is_probable_chain(name: str, website_url: str | None, text: str) -> bool:
    lowered = f"{name} {text}".lower()
    if any(token in lowered for token in ("locations", "franchise", "book at any location")):
        return True
    if website_url and re.search(r"\b(location|locations|franchise)\b", website_url.lower()):
        return True
    return False


def _assess_website_quality(metrics: dict[str, Any], page_text: str, url: str) -> str:
    lowered_url = url.lower()
    lowered_text = page_text.lower()
    if "facebook.com" in lowered_url:
        return "poor - Facebook page used as website"
    if not metrics.get("hasViewport"):
        return "poor - missing viewport meta suggests weak mobile optimization"
    if metrics.get("linkCount", 0) < 5 and metrics.get("imageCount", 0) < 2:
        return "poor - sparse site with thin content and weak navigation"
    if "blog" in lowered_text or "news" in lowered_text or "resources" in lowered_text:
        return "modern or actively maintained - content sections present"
    return "functional but dated - basic navigation present with limited freshness signals"


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


__all__ = ["PlaywrightGoogleMapsSession", "create_browser_tools"]
