"""InboxApp operation catalog, tool definition, and MCP-style tool factory."""

from __future__ import annotations
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Literal, Sequence

PayloadKind = Literal["none", "object"]


@dataclass(frozen=True, slots=True)
class InboxAppOperation:
    """Declarative metadata for one InboxApp API operation."""

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
class InboxAppPreparedRequest:
    """A validated InboxApp request ready for execution."""

    operation: InboxAppOperation
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
) -> tuple[str, InboxAppOperation]:
    return (
        name,
        InboxAppOperation(
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


_INBOXAPP_CATALOG: OrderedDict[str, InboxAppOperation] = OrderedDict(
    (
        _op("list_statuses", "Status", "GET", "/statuses"),
        _op("get_status", "Status", "GET", "/statuses/{status_id}", required_path_params=("status_id",)),
        _op("create_status", "Status", "POST", "/statuses", payload_kind="object", payload_required=True),
        _op(
            "update_status",
            "Status",
            "PATCH",
            "/statuses/{status_id}",
            required_path_params=("status_id",),
            payload_kind="object",
            payload_required=True,
        ),
        _op(
            "delete_status",
            "Status",
            "DELETE",
            "/statuses/{status_id}",
            required_path_params=("status_id",),
            payload_kind="object",
            payload_required=False,
        ),
        _op("list_threads", "Thread", "GET", "/threads", allow_query=True),
        _op("get_thread", "Thread", "GET", "/threads/{thread_id}", required_path_params=("thread_id",)),
        _op("create_thread", "Thread", "POST", "/threads", payload_kind="object", payload_required=True),
        _op(
            "get_prospect",
            "Prospect",
            "GET",
            "/prospects/{prospect_id}",
            required_path_params=("prospect_id",),
        ),
    )
)


def build_inboxapp_operation_catalog() -> tuple[InboxAppOperation, ...]:
    """Return the supported InboxApp operation catalog in stable order."""
    return tuple(_INBOXAPP_CATALOG.values())


def get_inboxapp_operation(operation_name: str) -> InboxAppOperation:
    """Return a supported InboxApp operation or raise a clear error."""
    op = _INBOXAPP_CATALOG.get(operation_name)
    if op is None:
        available = ", ".join(_INBOXAPP_CATALOG)
        raise ValueError(
            f"Unsupported InboxApp operation '{operation_name}'. Available: {available}."
        )
    return op

__all__ = [
    "InboxAppOperation",
    "InboxAppPreparedRequest",
    "build_inboxapp_operation_catalog",
    "get_inboxapp_operation",
]
