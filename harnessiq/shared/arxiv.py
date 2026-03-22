"""arXiv shared operation metadata."""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
import re

ARXIV_PDF_BASE_URL = "https://arxiv.org"
ARXIV_ATOM_NS = "http://www.w3.org/2005/Atom"
ARXIV_EXTENSION_NS = "http://arxiv.org/schemas/atom"
ARXIV_ENTRY_TAG = f"{{{ARXIV_ATOM_NS}}}entry"
ARXIV_ID_TAG = f"{{{ARXIV_ATOM_NS}}}id"
ARXIV_TITLE_TAG = f"{{{ARXIV_ATOM_NS}}}title"
ARXIV_SUMMARY_TAG = f"{{{ARXIV_ATOM_NS}}}summary"
ARXIV_PUBLISHED_TAG = f"{{{ARXIV_ATOM_NS}}}published"
ARXIV_UPDATED_TAG = f"{{{ARXIV_ATOM_NS}}}updated"
ARXIV_AUTHOR_TAG = f"{{{ARXIV_ATOM_NS}}}author"
ARXIV_AUTHOR_NAME_TAG = f"{{{ARXIV_ATOM_NS}}}name"
ARXIV_CATEGORY_TAG = f"{{{ARXIV_ATOM_NS}}}category"
ARXIV_LINK_TAG = f"{{{ARXIV_ATOM_NS}}}link"
ARXIV_PRIMARY_CATEGORY_TAG = f"{{{ARXIV_EXTENSION_NS}}}primary_category"
ARXIV_VERSION_SUFFIX_RE = re.compile(r"v\d+$")


@dataclass(frozen=True, slots=True)
class ArxivOperation:
    """Declarative metadata for one arXiv client operation."""

    name: str
    category: str
    description: str

    def summary(self) -> str:
        return self.name


# ---------------------------------------------------------------------------
# Catalog
# ---------------------------------------------------------------------------

_CATALOG: OrderedDict[str, ArxivOperation] = OrderedDict(
    [
        (
            "search",
            ArxivOperation(
                name="search",
                category="Search",
                description=(
                    "Search arXiv papers by keyword, author, title, or category; "
                    "returns normalized paper records."
                ),
            ),
        ),
        (
            "search_raw",
            ArxivOperation(
                name="search_raw",
                category="Search",
                description="Search arXiv papers; returns raw Atom 1.0 XML.",
            ),
        ),
        (
            "get_paper",
            ArxivOperation(
                name="get_paper",
                category="Retrieval",
                description=(
                    "Retrieve a single arXiv paper by ID; "
                    "returns a normalized paper record."
                ),
            ),
        ),
        (
            "download_paper",
            ArxivOperation(
                name="download_paper",
                category="Download",
                description="Download a paper PDF to a local path.",
            ),
        ),
    ]
)


def build_arxiv_operation_catalog() -> tuple[ArxivOperation, ...]:
    """Return all registered arXiv operations in insertion order."""
    return tuple(_CATALOG.values())


def get_arxiv_operation(name: str) -> ArxivOperation:
    """Return the ``ArxivOperation`` for *name*.

    Raises:
        ValueError: If *name* is not a known operation, with the known
            names listed in the message.
    """
    try:
        return _CATALOG[name]
    except KeyError:
        known = ", ".join(_CATALOG)
        raise ValueError(
            f"Unknown arXiv operation '{name}'. Known operations: {known}."
        ) from None


__all__ = [
    "ARXIV_ATOM_NS",
    "ARXIV_AUTHOR_NAME_TAG",
    "ARXIV_AUTHOR_TAG",
    "ARXIV_CATEGORY_TAG",
    "ARXIV_ENTRY_TAG",
    "ARXIV_EXTENSION_NS",
    "ARXIV_ID_TAG",
    "ARXIV_LINK_TAG",
    "ARXIV_PDF_BASE_URL",
    "ARXIV_PRIMARY_CATEGORY_TAG",
    "ARXIV_PUBLISHED_TAG",
    "ARXIV_SUMMARY_TAG",
    "ARXIV_TITLE_TAG",
    "ARXIV_UPDATED_TAG",
    "ARXIV_VERSION_SUFFIX_RE",
    "ArxivOperation",
    "build_arxiv_operation_catalog",
    "get_arxiv_operation",
]
