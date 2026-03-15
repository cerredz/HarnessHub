"""People Data Labs REST API request payload builders."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from harnessiq.providers.base import omit_none_values


# ── Person request builders ──────────────────────────────────────────────────


def build_person_search_request(
    *,
    query: dict[str, Any] | None = None,
    sql: str | None = None,
    size: int = 10,
    from_: int = 0,
) -> dict[str, object]:
    """Build a person search request body.

    Either *query* (Elasticsearch DSL) or *sql* must be provided.
    """
    payload: dict[str, object] = {"size": size, "from": from_}
    if query is not None:
        payload["query"] = deepcopy(query)
    if sql is not None:
        payload["sql"] = sql
    return payload


def build_person_bulk_request(
    requests: list[dict[str, Any]],
    *,
    size: int | None = None,
) -> dict[str, object]:
    """Build a person bulk enrich request body."""
    return omit_none_values(
        {
            "requests": deepcopy(requests),
            "size": size,
        }
    )


# ── Company request builders ─────────────────────────────────────────────────


def build_company_search_request(
    *,
    query: dict[str, Any] | None = None,
    sql: str | None = None,
    size: int = 10,
    from_: int = 0,
) -> dict[str, object]:
    """Build a company search request body.

    Either *query* (Elasticsearch DSL) or *sql* must be provided.
    """
    payload: dict[str, object] = {"size": size, "from": from_}
    if query is not None:
        payload["query"] = deepcopy(query)
    if sql is not None:
        payload["sql"] = sql
    return payload


def build_company_bulk_request(
    requests: list[dict[str, Any]],
    *,
    size: int | None = None,
) -> dict[str, object]:
    """Build a company bulk enrich request body."""
    return omit_none_values(
        {
            "requests": deepcopy(requests),
            "size": size,
        }
    )
