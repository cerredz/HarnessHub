"""Serper operation catalog, tool definition, and MCP-style tool factory."""

from __future__ import annotations
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Literal

PayloadKind = Literal["object"]


@dataclass(frozen=True, slots=True)
class SerperOperation:
    """Declarative metadata for one Serper API operation."""

    name: str
    category: str
    method: Literal["POST"]
    path_hint: str
    payload_kind: PayloadKind = "object"
    payload_required: bool = True

    def summary(self) -> str:
        return f"{self.name} ({self.method} {self.path_hint})"


@dataclass(frozen=True, slots=True)
class SerperPreparedRequest:
    """A validated Serper request ready for execution."""

    operation: SerperOperation
    method: str
    path: str
    url: str
    headers: dict[str, str]
    json_body: Any | None


def _op(name: str, category: str, path_hint: str) -> tuple[str, SerperOperation]:
    return (
        name,
        SerperOperation(
            name=name,
            category=category,
            method="POST",
            path_hint=path_hint,
        ),
    )


_SERPER_CATALOG: OrderedDict[str, SerperOperation] = OrderedDict(
    (
        _op("search", "Search", "/search"),
        _op("images", "Search", "/images"),
        _op("news", "Search", "/news"),
        _op("videos", "Search", "/videos"),
        _op("shopping", "Search", "/shopping"),
        _op("places", "Maps", "/places"),
        _op("maps", "Maps", "/maps"),
        _op("autocomplete", "Discovery", "/autocomplete"),
        _op("scholar", "Research", "/scholar"),
        _op("patents", "Research", "/patents"),
    )
)


def build_serper_operation_catalog() -> tuple[SerperOperation, ...]:
    """Return the supported Serper operation catalog in stable order."""
    return tuple(_SERPER_CATALOG.values())


def get_serper_operation(operation_name: str) -> SerperOperation:
    """Return a supported Serper operation or raise a clear error."""
    op = _SERPER_CATALOG.get(operation_name)
    if op is None:
        available = ", ".join(_SERPER_CATALOG)
        raise ValueError(f"Unsupported Serper operation '{operation_name}'. Available: {available}.")
    return op

__all__ = [
    "SerperOperation",
    "SerperPreparedRequest",
    "build_serper_operation_catalog",
    "get_serper_operation",
]
