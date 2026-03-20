"""Exa operation catalog, tool definition, and MCP-style tool factory."""

from __future__ import annotations
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Literal, Sequence

PayloadKind = Literal["none", "object"]


@dataclass(frozen=True, slots=True)
class ExaOperation:
    """Declarative metadata for one Exa API operation."""

    name: str
    category: str
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"]
    path_hint: str
    required_path_params: tuple[str, ...] = ()
    payload_kind: PayloadKind = "none"
    payload_required: bool = False
    allow_query: bool = False

    def summary(self) -> str:
        return f"{self.name} ({self.method} {self.path_hint})"


@dataclass(frozen=True, slots=True)
class ExaPreparedRequest:
    """A validated Exa request ready for execution."""

    operation: ExaOperation
    method: str
    path: str
    url: str
    headers: dict[str, str]
    json_body: Any | None


# ---------------------------------------------------------------------------
# Catalog
# ---------------------------------------------------------------------------

def _op(
    name: str,
    category: str,
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"],
    path_hint: str,
    *,
    required_path_params: Sequence[str] = (),
    payload_kind: PayloadKind = "none",
    payload_required: bool = False,
    allow_query: bool = False,
) -> tuple[str, ExaOperation]:
    return (
        name,
        ExaOperation(
            name=name,
            category=category,
            method=method,
            path_hint=path_hint,
            required_path_params=tuple(required_path_params),
            payload_kind=payload_kind,
            payload_required=payload_required,
            allow_query=allow_query,
        ),
    )


_EXA_CATALOG: OrderedDict[str, ExaOperation] = OrderedDict(
    (
        # Search
        _op("search", "Search", "POST", "/search", payload_kind="object", payload_required=True),
        # Contents
        _op("get_contents", "Contents", "POST", "/contents", payload_kind="object", payload_required=True),
        # Find Similar
        _op("find_similar", "Find Similar", "POST", "/findSimilar", payload_kind="object", payload_required=True),
        # Answer
        _op("get_answer", "Answer", "POST", "/answer", payload_kind="object", payload_required=True),
        # Research (search + contents combined)
        _op("search_and_contents", "Research", "POST", "/searchAndContents", payload_kind="object", payload_required=True),
        # Websets (saved search collections)
        _op("list_websets", "Webset", "GET", "/websets", allow_query=True),
        _op("get_webset", "Webset", "GET", "/websets/{webset_id}", required_path_params=("webset_id",)),
        _op("create_webset", "Webset", "POST", "/websets", payload_kind="object", payload_required=True),
        _op("update_webset", "Webset", "PATCH", "/websets/{webset_id}", required_path_params=("webset_id",), payload_kind="object", payload_required=True),
        _op("delete_webset", "Webset", "DELETE", "/websets/{webset_id}", required_path_params=("webset_id",)),
        # Webset Items
        _op("list_webset_items", "Webset Item", "GET", "/websets/{webset_id}/items", required_path_params=("webset_id",), allow_query=True),
        _op("get_webset_item", "Webset Item", "GET", "/websets/{webset_id}/items/{item_id}", required_path_params=("webset_id", "item_id")),
        # Webset Searches (automated search schedules)
        _op("list_webset_searches", "Webset Search", "GET", "/websets/{webset_id}/searches", required_path_params=("webset_id",)),
        _op("create_webset_search", "Webset Search", "POST", "/websets/{webset_id}/searches", required_path_params=("webset_id",), payload_kind="object", payload_required=True),
        _op("delete_webset_search", "Webset Search", "DELETE", "/websets/{webset_id}/searches/{search_id}", required_path_params=("webset_id", "search_id")),
    )
)


def build_exa_operation_catalog() -> tuple[ExaOperation, ...]:
    """Return the supported Exa operation catalog in stable order."""
    return tuple(_EXA_CATALOG.values())


def get_exa_operation(operation_name: str) -> ExaOperation:
    """Return a supported Exa operation or raise a clear error."""
    op = _EXA_CATALOG.get(operation_name)
    if op is None:
        available = ", ".join(_EXA_CATALOG)
        raise ValueError(f"Unsupported Exa operation '{operation_name}'. Available: {available}.")
    return op

__all__ = [
    "ExaOperation",
    "ExaPreparedRequest",
    "build_exa_operation_catalog",
    "get_exa_operation",
]
