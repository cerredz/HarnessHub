"""arXiv shared operation metadata."""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass


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
