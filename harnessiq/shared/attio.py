"""Attio operation catalog, tool definition, and MCP-style tool factory."""

from __future__ import annotations
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Literal, Sequence

PayloadKind = Literal["none", "object"]


@dataclass(frozen=True, slots=True)
class AttioOperation:
    """Declarative metadata for one Attio API operation."""

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
class AttioPreparedRequest:
    """A validated Attio request ready for execution."""

    operation: AttioOperation
    method: str
    path: str
    url: str
    headers: dict[str, str]
    json_body: Any | None


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
) -> tuple[str, AttioOperation]:
    return (
        name,
        AttioOperation(
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


_ATTIO_CATALOG: OrderedDict[str, AttioOperation] = OrderedDict(
    (
        _op("list_objects", "Object", "GET", "/objects", allow_query=True),
        _op(
            "list_attributes",
            "Attribute",
            "GET",
            "/{target}/{identifier}/attributes",
            required_path_params=("target", "identifier"),
            allow_query=True,
        ),
        _op(
            "list_records",
            "Record",
            "POST",
            "/objects/{object}/records/query",
            required_path_params=("object",),
            payload_kind="object",
            payload_required=False,
        ),
        _op(
            "get_record",
            "Record",
            "GET",
            "/objects/{object}/records/{record_id}",
            required_path_params=("object", "record_id"),
        ),
        _op(
            "create_record",
            "Record",
            "POST",
            "/objects/{object}/records",
            required_path_params=("object",),
            payload_kind="object",
            payload_required=True,
        ),
        _op(
            "assert_record",
            "Record",
            "PUT",
            "/objects/{object}/records",
            required_path_params=("object",),
            payload_kind="object",
            payload_required=True,
        ),
        _op(
            "delete_record",
            "Record",
            "DELETE",
            "/objects/{object}/records/{record_id}",
            required_path_params=("object", "record_id"),
        ),
    )
)


def build_attio_operation_catalog() -> tuple[AttioOperation, ...]:
    """Return the supported Attio operation catalog in stable order."""
    return tuple(_ATTIO_CATALOG.values())


def get_attio_operation(operation_name: str) -> AttioOperation:
    """Return a supported Attio operation or raise a clear error."""
    op = _ATTIO_CATALOG.get(operation_name)
    if op is None:
        available = ", ".join(_ATTIO_CATALOG)
        raise ValueError(f"Unsupported Attio operation '{operation_name}'. Available: {available}.")
    return op

__all__ = [
    "AttioOperation",
    "AttioPreparedRequest",
    "build_attio_operation_catalog",
    "get_attio_operation",
]
