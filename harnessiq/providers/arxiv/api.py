"""arXiv API endpoint constants, URL builders, and Atom feed parser."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any
from urllib import parse

from harnessiq.shared.arxiv import (
    ARXIV_AUTHOR_NAME_TAG,
    ARXIV_AUTHOR_TAG,
    ARXIV_CATEGORY_TAG,
    ARXIV_ENTRY_TAG,
    ARXIV_ID_TAG,
    ARXIV_LINK_TAG,
    ARXIV_PDF_BASE_URL,
    ARXIV_PRIMARY_CATEGORY_TAG,
    ARXIV_PUBLISHED_TAG,
    ARXIV_SUMMARY_TAG,
    ARXIV_TITLE_TAG,
    ARXIV_UPDATED_TAG,
    ARXIV_VERSION_SUFFIX_RE,
)
from harnessiq.shared.providers import ARXIV_DEFAULT_BASE_URL as DEFAULT_BASE_URL


# ---------------------------------------------------------------------------
# URL builders
# ---------------------------------------------------------------------------


def search_url(
    base_url: str,
    *,
    query: str,
    max_results: int,
    start: int,
    sort_by: str,
    sort_order: str,
) -> str:
    """Build a fully-qualified arXiv search URL."""
    base = base_url.rstrip("/")
    encoded = parse.urlencode(
        {
            "search_query": query,
            "start": start,
            "max_results": max_results,
            "sortBy": sort_by,
            "sortOrder": sort_order,
        }
    )
    return f"{base}/api/query?{encoded}"


def get_paper_url(base_url: str, paper_id: str) -> str:
    """Build the URL to retrieve a single paper by arXiv ID."""
    base = base_url.rstrip("/")
    encoded = parse.urlencode({"search_query": f"id:{paper_id}", "max_results": 1})
    return f"{base}/api/query?{encoded}"


def pdf_url(paper_id: str) -> str:
    """Return the direct PDF download URL for an arXiv paper."""
    return f"{ARXIV_PDF_BASE_URL}/pdf/{paper_id}"


# ---------------------------------------------------------------------------
# Atom XML parser
# ---------------------------------------------------------------------------


def parse_arxiv_feed(xml_text: str) -> list[dict[str, Any]]:
    """Parse an Atom 1.0 arXiv feed into a list of normalized paper records.

    Returns an empty list for zero-result feeds.

    Raises:
        ValueError: If *xml_text* cannot be parsed as valid XML.
    """
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise ValueError(f"arXiv feed is not valid XML: {exc}") from exc

    return [parse_arxiv_entry(entry) for entry in root.findall(ARXIV_ENTRY_TAG)]


def parse_arxiv_entry(entry: ET.Element) -> dict[str, Any]:
    """Extract a normalized paper record from a single Atom <entry> element.

    Returned keys: ``id``, ``arxiv_id``, ``title``, ``authors``,
    ``summary``, ``published``, ``updated``, ``categories``,
    ``primary_category``, ``pdf_url``, ``abs_url``.
    """
    raw_id = _text(entry, ARXIV_ID_TAG) or ""
    arxiv_id = _extract_arxiv_id(raw_id)

    abs_url = ""
    entry_pdf_url = ""
    for link in entry.findall(ARXIV_LINK_TAG):
        rel = link.get("rel", "")
        href = link.get("href", "")
        link_type = link.get("type", "")
        if rel == "alternate" and "html" in link_type:
            abs_url = href
        elif rel == "related" and "pdf" in link_type:
            entry_pdf_url = href

    if not entry_pdf_url and arxiv_id:
        entry_pdf_url = pdf_url(arxiv_id)

    return {
        "id": raw_id,
        "arxiv_id": arxiv_id,
        "title": _text(entry, ARXIV_TITLE_TAG) or "",
        "authors": [
            _text(author, ARXIV_AUTHOR_NAME_TAG) or ""
            for author in entry.findall(ARXIV_AUTHOR_TAG)
        ],
        "summary": (_text(entry, ARXIV_SUMMARY_TAG) or "").strip(),
        "published": _text(entry, ARXIV_PUBLISHED_TAG) or "",
        "updated": _text(entry, ARXIV_UPDATED_TAG) or "",
        "categories": [cat.get("term", "") for cat in entry.findall(ARXIV_CATEGORY_TAG)],
        "primary_category": _primary_category(entry),
        "pdf_url": entry_pdf_url,
        "abs_url": abs_url,
    }


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _text(element: ET.Element, tag: str) -> str | None:
    """Return stripped text of the first matching child, or ``None``."""
    child = element.find(tag)
    if child is None:
        return None
    return (child.text or "").strip() or None


def _extract_arxiv_id(raw_id: str) -> str:
    """Extract the bare arXiv ID from a canonical abs URL.

    Examples::

        "http://arxiv.org/abs/2301.12345v1"  â†’  "2301.12345"
        "http://arxiv.org/abs/hep-ph/9901257v2"  â†’  "hep-ph/9901257"
    """
    if "/abs/" in raw_id:
        arxiv_id = raw_id.split("/abs/", 1)[1]
    else:
        arxiv_id = raw_id
    return ARXIV_VERSION_SUFFIX_RE.sub("", arxiv_id)


def _primary_category(entry: ET.Element) -> str:
    """Return the primary_category term for an entry, or empty string."""
    pc = entry.find(ARXIV_PRIMARY_CATEGORY_TAG)
    if pc is None:
        first_cat = entry.find(ARXIV_CATEGORY_TAG)
        return first_cat.get("term", "") if first_cat is not None else ""
    return pc.get("term", "")

