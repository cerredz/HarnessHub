"""arXiv API endpoint constants, URL builders, and Atom feed parser."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from typing import Any
from urllib import parse

DEFAULT_BASE_URL = "https://export.arxiv.org"
_PDF_BASE_URL = "https://arxiv.org"

# Atom 1.0 and arXiv-extension namespaces used in feed responses.
_ATOM_NS = "http://www.w3.org/2005/Atom"
_ARXIV_NS = "http://arxiv.org/schemas/atom"

# Clark-notation tag shortcuts — avoids repetitive f-string construction.
_ENTRY = f"{{{_ATOM_NS}}}entry"
_ID = f"{{{_ATOM_NS}}}id"
_TITLE = f"{{{_ATOM_NS}}}title"
_SUMMARY = f"{{{_ATOM_NS}}}summary"
_PUBLISHED = f"{{{_ATOM_NS}}}published"
_UPDATED = f"{{{_ATOM_NS}}}updated"
_AUTHOR = f"{{{_ATOM_NS}}}author"
_AUTHOR_NAME = f"{{{_ATOM_NS}}}name"
_CATEGORY = f"{{{_ATOM_NS}}}category"
_LINK = f"{{{_ATOM_NS}}}link"
_PRIMARY_CATEGORY = f"{{{_ARXIV_NS}}}primary_category"

# Matches a version suffix like "v1", "v12" at the end of an arXiv ID.
_VERSION_SUFFIX_RE = re.compile(r"v\d+$")


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
    return f"{_PDF_BASE_URL}/pdf/{paper_id}"


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

    return [parse_arxiv_entry(entry) for entry in root.findall(_ENTRY)]


def parse_arxiv_entry(entry: ET.Element) -> dict[str, Any]:
    """Extract a normalized paper record from a single Atom <entry> element.

    Returned keys: ``id``, ``arxiv_id``, ``title``, ``authors``,
    ``summary``, ``published``, ``updated``, ``categories``,
    ``primary_category``, ``pdf_url``, ``abs_url``.
    """
    raw_id = _text(entry, _ID) or ""
    arxiv_id = _extract_arxiv_id(raw_id)

    abs_url = ""
    entry_pdf_url = ""
    for link in entry.findall(_LINK):
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
        "title": _text(entry, _TITLE) or "",
        "authors": [
            _text(author, _AUTHOR_NAME) or ""
            for author in entry.findall(_AUTHOR)
        ],
        "summary": (_text(entry, _SUMMARY) or "").strip(),
        "published": _text(entry, _PUBLISHED) or "",
        "updated": _text(entry, _UPDATED) or "",
        "categories": [cat.get("term", "") for cat in entry.findall(_CATEGORY)],
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

        "http://arxiv.org/abs/2301.12345v1"  →  "2301.12345"
        "http://arxiv.org/abs/hep-ph/9901257v2"  →  "hep-ph/9901257"
    """
    if "/abs/" in raw_id:
        arxiv_id = raw_id.split("/abs/", 1)[1]
    else:
        arxiv_id = raw_id
    return _VERSION_SUFFIX_RE.sub("", arxiv_id)


def _primary_category(entry: ET.Element) -> str:
    """Return the primary_category term for an entry, or empty string."""
    pc = entry.find(_PRIMARY_CATEGORY)
    if pc is None:
        first_cat = entry.find(_CATEGORY)
        return first_cat.get("term", "") if first_cat is not None else ""
    return pc.get("term", "")
