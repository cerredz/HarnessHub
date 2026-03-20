"""ZeroBounce operation catalog, tool definition, and MCP-style tool factory."""

from __future__ import annotations
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Literal, Sequence

PayloadKind = Literal["none", "object"]


@dataclass(frozen=True, slots=True)
class ZeroBounceOperation:
    """Declarative metadata for one ZeroBounce API operation."""

    name: str
    category: str
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"]
    path_hint: str
    required_path_params: tuple[str, ...] = ()
    payload_kind: PayloadKind = "none"
    payload_required: bool = False
    allow_query: bool = False
    use_bulk_base: bool = False

    def summary(self) -> str:
        return f"{self.name} ({self.method} {self.path_hint})"


@dataclass(frozen=True, slots=True)
class ZeroBouncePreparedRequest:
    """A validated ZeroBounce request ready for execution."""

    operation: ZeroBounceOperation
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
    use_bulk_base: bool = False,
) -> tuple[str, ZeroBounceOperation]:
    return (
        name,
        ZeroBounceOperation(
            name=name,
            category=category,
            method=method,
            path_hint=path_hint,
            required_path_params=tuple(required_path_params),
            payload_kind=payload_kind,
            payload_required=payload_required,
            allow_query=allow_query,
            use_bulk_base=use_bulk_base,
        ),
    )


_ZEROBOUNCE_CATALOG: OrderedDict[str, ZeroBounceOperation] = OrderedDict(
    (
        # Account
        _op("get_credits", "Account", "GET", "/v2/getcredits"),
        _op("get_api_usage", "Account", "GET", "/v2/getapiusage", allow_query=True),

        # Email Validation — real-time
        _op("validate_email", "Validation", "GET", "/v2/validate", allow_query=True),
        _op("validate_batch", "Validation", "POST", "/v2/validatebatch", payload_kind="object", payload_required=True),

        # Email Validation — bulk file (bulkapi.zerobounce.net)
        _op("bulk_send_file", "Bulk Validation", "POST", "/v2/sendfile", payload_kind="object", payload_required=True, use_bulk_base=True),
        _op("bulk_file_status", "Bulk Validation", "GET", "/v2/filestatus", allow_query=True, use_bulk_base=True),
        _op("bulk_get_file", "Bulk Validation", "GET", "/v2/getfile", allow_query=True, use_bulk_base=True),
        _op("bulk_delete_file", "Bulk Validation", "GET", "/v2/deletefile", allow_query=True, use_bulk_base=True),

        # AI Email Scoring
        _op("score_email", "Scoring", "GET", "/v2/scoring", allow_query=True),
        _op("bulk_scoring_send_file", "Bulk Scoring", "POST", "/v2/scoring/sendfile", payload_kind="object", payload_required=True, use_bulk_base=True),
        _op("bulk_scoring_file_status", "Bulk Scoring", "GET", "/v2/scoring/filestatus", allow_query=True, use_bulk_base=True),
        _op("bulk_scoring_get_file", "Bulk Scoring", "GET", "/v2/scoring/getfile", allow_query=True, use_bulk_base=True),
        _op("bulk_scoring_delete_file", "Bulk Scoring", "GET", "/v2/scoring/deletefile", allow_query=True, use_bulk_base=True),

        # Email Finder
        _op("find_email", "Email Finder", "GET", "/v2/guessformat", allow_query=True),
        _op("bulk_finder_send_file", "Bulk Email Finder", "POST", "/v2/email-finder/sendfile", payload_kind="object", payload_required=True, use_bulk_base=True),
        _op("bulk_finder_file_status", "Bulk Email Finder", "GET", "/v2/email-finder/filestatus", allow_query=True, use_bulk_base=True),
        _op("bulk_finder_get_file", "Bulk Email Finder", "GET", "/v2/email-finder/getfile", allow_query=True, use_bulk_base=True),
        _op("bulk_finder_delete_file", "Bulk Email Finder", "GET", "/v2/email-finder/deletefile", allow_query=True, use_bulk_base=True),

        # Activity Data
        _op("get_activity_data", "Activity", "GET", "/v2/activity", allow_query=True),

        # Filters (allowlist / blocklist)
        _op("list_filters", "Filters", "GET", "/v2/filters/list"),
        _op("add_filter", "Filters", "POST", "/v2/filters/add", payload_kind="object", payload_required=True),
        _op("delete_filter", "Filters", "POST", "/v2/filters/delete", payload_kind="object", payload_required=True),
    )
)


def build_zerobounce_operation_catalog() -> tuple[ZeroBounceOperation, ...]:
    """Return the supported ZeroBounce operation catalog in stable order."""
    return tuple(_ZEROBOUNCE_CATALOG.values())


def get_zerobounce_operation(operation_name: str) -> ZeroBounceOperation:
    """Return a supported ZeroBounce operation or raise a clear error."""
    op = _ZEROBOUNCE_CATALOG.get(operation_name)
    if op is None:
        available = ", ".join(_ZEROBOUNCE_CATALOG)
        raise ValueError(
            f"Unsupported ZeroBounce operation '{operation_name}'. Available: {available}."
        )
    return op

__all__ = [
    "ZeroBounceOperation",
    "ZeroBouncePreparedRequest",
    "build_zerobounce_operation_catalog",
    "get_zerobounce_operation",
]
