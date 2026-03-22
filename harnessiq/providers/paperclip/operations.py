"""Paperclip operation catalog and prepared-request helpers."""

from __future__ import annotations

from collections import OrderedDict
from copy import deepcopy
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal, Mapping, Sequence
from urllib.parse import quote

from harnessiq.providers.http import join_url

if TYPE_CHECKING:
    from harnessiq.providers.paperclip.client import PaperclipCredentials

PayloadKind = Literal["none", "object"]


@dataclass(frozen=True, slots=True)
class PaperclipOperation:
    """Declarative metadata for one Paperclip API operation."""

    name: str
    category: str
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"]
    path_hint: str
    required_path_params: tuple[str, ...] = ()
    payload_kind: PayloadKind = "none"
    payload_required: bool = False
    allow_query: bool = False
    supports_run_id: bool = False

    def summary(self) -> str:
        return f"{self.name} ({self.method} {self.path_hint})"


@dataclass(frozen=True, slots=True)
class PaperclipPreparedRequest:
    """A validated Paperclip request ready for execution."""

    operation: PaperclipOperation
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
    supports_run_id: bool = False,
) -> tuple[str, PaperclipOperation]:
    return (
        name,
        PaperclipOperation(
            name=name,
            category=category,
            method=method,
            path_hint=path_hint,
            required_path_params=tuple(required_path_params),
            payload_kind=payload_kind,
            payload_required=payload_required,
            allow_query=allow_query,
            supports_run_id=supports_run_id,
        ),
    )


_PAPERCLIP_CATALOG: OrderedDict[str, PaperclipOperation] = OrderedDict(
    (
        # Companies
        _op("list_companies", "Companies", "GET", "/companies"),
        _op("get_company", "Companies", "GET", "/companies/{company_id}", required_path_params=("company_id",)),
        _op("create_company", "Companies", "POST", "/companies", payload_kind="object", payload_required=True),
        _op(
            "update_company",
            "Companies",
            "PATCH",
            "/companies/{company_id}",
            required_path_params=("company_id",),
            payload_kind="object",
            payload_required=True,
            supports_run_id=True,
        ),
        _op(
            "archive_company",
            "Companies",
            "POST",
            "/companies/{company_id}/archive",
            required_path_params=("company_id",),
            supports_run_id=True,
        ),
        # Agents
        _op("list_agents", "Agents", "GET", "/companies/{company_id}/agents", required_path_params=("company_id",)),
        _op("get_agent", "Agents", "GET", "/agents/{agent_id}", required_path_params=("agent_id",)),
        _op("get_current_agent", "Agents", "GET", "/agents/me"),
        _op(
            "create_agent",
            "Agents",
            "POST",
            "/companies/{company_id}/agents",
            required_path_params=("company_id",),
            payload_kind="object",
            payload_required=True,
            supports_run_id=True,
        ),
        _op(
            "update_agent",
            "Agents",
            "PATCH",
            "/agents/{agent_id}",
            required_path_params=("agent_id",),
            payload_kind="object",
            payload_required=True,
            supports_run_id=True,
        ),
        _op("pause_agent", "Agents", "POST", "/agents/{agent_id}/pause", required_path_params=("agent_id",), supports_run_id=True),
        _op("resume_agent", "Agents", "POST", "/agents/{agent_id}/resume", required_path_params=("agent_id",), supports_run_id=True),
        _op(
            "terminate_agent",
            "Agents",
            "POST",
            "/agents/{agent_id}/terminate",
            required_path_params=("agent_id",),
            supports_run_id=True,
        ),
        _op(
            "create_agent_api_key",
            "Agents",
            "POST",
            "/agents/{agent_id}/keys",
            required_path_params=("agent_id",),
            supports_run_id=True,
        ),
        _op(
            "invoke_agent_heartbeat",
            "Agents",
            "POST",
            "/agents/{agent_id}/heartbeat/invoke",
            required_path_params=("agent_id",),
            supports_run_id=True,
        ),
        _op("get_org_chart", "Agents", "GET", "/companies/{company_id}/org", required_path_params=("company_id",)),
        _op(
            "list_adapter_models",
            "Agents",
            "GET",
            "/companies/{company_id}/adapters/{adapter_type}/models",
            required_path_params=("company_id", "adapter_type"),
        ),
        _op(
            "list_agent_config_revisions",
            "Agents",
            "GET",
            "/agents/{agent_id}/config-revisions",
            required_path_params=("agent_id",),
        ),
        _op(
            "rollback_agent_config_revision",
            "Agents",
            "POST",
            "/agents/{agent_id}/config-revisions/{revision_id}/rollback",
            required_path_params=("agent_id", "revision_id"),
            supports_run_id=True,
        ),
        # Issues
        _op("list_issues", "Issues", "GET", "/companies/{company_id}/issues", required_path_params=("company_id",), allow_query=True),
        _op("get_issue", "Issues", "GET", "/issues/{issue_id}", required_path_params=("issue_id",)),
        _op(
            "create_issue",
            "Issues",
            "POST",
            "/companies/{company_id}/issues",
            required_path_params=("company_id",),
            payload_kind="object",
            payload_required=True,
            supports_run_id=True,
        ),
        _op(
            "update_issue",
            "Issues",
            "PATCH",
            "/issues/{issue_id}",
            required_path_params=("issue_id",),
            payload_kind="object",
            payload_required=True,
            supports_run_id=True,
        ),
        _op(
            "checkout_issue",
            "Issues",
            "POST",
            "/issues/{issue_id}/checkout",
            required_path_params=("issue_id",),
            payload_kind="object",
            payload_required=True,
            supports_run_id=True,
        ),
        _op("release_issue", "Issues", "POST", "/issues/{issue_id}/release", required_path_params=("issue_id",), supports_run_id=True),
        _op("list_issue_comments", "Issues", "GET", "/issues/{issue_id}/comments", required_path_params=("issue_id",)),
        _op(
            "add_issue_comment",
            "Issues",
            "POST",
            "/issues/{issue_id}/comments",
            required_path_params=("issue_id",),
            payload_kind="object",
            payload_required=True,
            supports_run_id=True,
        ),
        _op("list_issue_documents", "Issues", "GET", "/issues/{issue_id}/documents", required_path_params=("issue_id",)),
        _op(
            "get_issue_document",
            "Issues",
            "GET",
            "/issues/{issue_id}/documents/{key}",
            required_path_params=("issue_id", "key"),
        ),
        _op(
            "upsert_issue_document",
            "Issues",
            "PUT",
            "/issues/{issue_id}/documents/{key}",
            required_path_params=("issue_id", "key"),
            payload_kind="object",
            payload_required=True,
            supports_run_id=True,
        ),
        _op(
            "list_issue_document_revisions",
            "Issues",
            "GET",
            "/issues/{issue_id}/documents/{key}/revisions",
            required_path_params=("issue_id", "key"),
        ),
        _op(
            "delete_issue_document",
            "Issues",
            "DELETE",
            "/issues/{issue_id}/documents/{key}",
            required_path_params=("issue_id", "key"),
            supports_run_id=True,
        ),
        # Approvals
        _op(
            "list_approvals",
            "Approvals",
            "GET",
            "/companies/{company_id}/approvals",
            required_path_params=("company_id",),
            allow_query=True,
        ),
        _op("get_approval", "Approvals", "GET", "/approvals/{approval_id}", required_path_params=("approval_id",)),
        _op(
            "create_approval_request",
            "Approvals",
            "POST",
            "/companies/{company_id}/approvals",
            required_path_params=("company_id",),
            payload_kind="object",
            payload_required=True,
            supports_run_id=True,
        ),
        _op(
            "create_agent_hire_request",
            "Approvals",
            "POST",
            "/companies/{company_id}/agent-hires",
            required_path_params=("company_id",),
            payload_kind="object",
            payload_required=True,
            supports_run_id=True,
        ),
        _op(
            "approve_approval",
            "Approvals",
            "POST",
            "/approvals/{approval_id}/approve",
            required_path_params=("approval_id",),
            payload_kind="object",
            supports_run_id=True,
        ),
        _op(
            "reject_approval",
            "Approvals",
            "POST",
            "/approvals/{approval_id}/reject",
            required_path_params=("approval_id",),
            payload_kind="object",
            supports_run_id=True,
        ),
        _op(
            "request_approval_revision",
            "Approvals",
            "POST",
            "/approvals/{approval_id}/request-revision",
            required_path_params=("approval_id",),
            payload_kind="object",
            supports_run_id=True,
        ),
        _op(
            "resubmit_approval",
            "Approvals",
            "POST",
            "/approvals/{approval_id}/resubmit",
            required_path_params=("approval_id",),
            payload_kind="object",
            payload_required=True,
            supports_run_id=True,
        ),
        _op(
            "list_approval_issues",
            "Approvals",
            "GET",
            "/approvals/{approval_id}/issues",
            required_path_params=("approval_id",),
        ),
        _op(
            "list_approval_comments",
            "Approvals",
            "GET",
            "/approvals/{approval_id}/comments",
            required_path_params=("approval_id",),
        ),
        _op(
            "add_approval_comment",
            "Approvals",
            "POST",
            "/approvals/{approval_id}/comments",
            required_path_params=("approval_id",),
            payload_kind="object",
            payload_required=True,
            supports_run_id=True,
        ),
        # Activity
        _op(
            "list_activity",
            "Activity",
            "GET",
            "/companies/{company_id}/activity",
            required_path_params=("company_id",),
            allow_query=True,
        ),
        # Costs
        _op(
            "report_cost_event",
            "Costs",
            "POST",
            "/companies/{company_id}/cost-events",
            required_path_params=("company_id",),
            payload_kind="object",
            payload_required=True,
            supports_run_id=True,
        ),
        _op(
            "get_company_cost_summary",
            "Costs",
            "GET",
            "/companies/{company_id}/costs/summary",
            required_path_params=("company_id",),
        ),
        _op(
            "get_costs_by_agent",
            "Costs",
            "GET",
            "/companies/{company_id}/costs/by-agent",
            required_path_params=("company_id",),
        ),
        _op(
            "get_costs_by_project",
            "Costs",
            "GET",
            "/companies/{company_id}/costs/by-project",
            required_path_params=("company_id",),
        ),
    )
)


def build_paperclip_operation_catalog() -> tuple[PaperclipOperation, ...]:
    """Return the supported Paperclip operation catalog in stable order."""
    return tuple(_PAPERCLIP_CATALOG.values())


def get_paperclip_operation(operation_name: str) -> PaperclipOperation:
    """Return a supported Paperclip operation or raise a clear error."""
    operation = _PAPERCLIP_CATALOG.get(operation_name)
    if operation is None:
        available = ", ".join(_PAPERCLIP_CATALOG)
        raise ValueError(
            f"Unsupported Paperclip operation '{operation_name}'. Available: {available}."
        )
    return operation


def _build_prepared_request(
    *,
    operation_name: str,
    credentials: "PaperclipCredentials",
    path_params: Mapping[str, object] | None,
    query: Mapping[str, object] | None,
    payload: Any | None,
    run_id: str | None,
) -> PaperclipPreparedRequest:
    from harnessiq.providers.paperclip.api import build_headers

    operation = get_paperclip_operation(operation_name)
    normalized_path_params = _normalize_path_params(path_params)
    _validate_path_params(operation, normalized_path_params)
    normalized_query = _normalize_query(query)
    _validate_query(operation, normalized_query)
    normalized_payload = _normalize_payload(payload)
    _validate_payload(operation, normalized_payload)

    path = operation.path_hint
    for parameter_name, value in normalized_path_params.items():
        path = path.replace(f"{{{parameter_name}}}", quote(value, safe=""))

    full_url = join_url(credentials.base_url, path, query=normalized_query)  # type: ignore[arg-type]
    headers = build_headers(
        credentials.api_key,
        run_id=run_id if operation.supports_run_id else None,
    )

    return PaperclipPreparedRequest(
        operation=operation,
        method=operation.method,
        path=path,
        url=full_url,
        headers=headers,
        json_body=deepcopy(normalized_payload) if normalized_payload is not None else None,
    )


def _normalize_path_params(path_params: Mapping[str, object] | None) -> dict[str, str]:
    if path_params is None:
        return {}
    normalized: dict[str, str] = {}
    for key, value in path_params.items():
        if not isinstance(key, str):
            raise ValueError("All keys in 'path_params' must be strings.")
        normalized[key] = str(value)
    return normalized


def _normalize_query(query: Mapping[str, object] | None) -> dict[str, str | int | float | bool] | None:
    if query is None:
        return None
    normalized: dict[str, str | int | float | bool] = {}
    for key, value in query.items():
        if not isinstance(key, str):
            raise ValueError("All keys in 'query' must be strings.")
        if not isinstance(value, (str, int, float, bool)):
            raise ValueError(
                f"Query parameter '{key}' must be a string, number, or boolean."
            )
        normalized[key] = value
    return normalized


def _normalize_payload(payload: Any | None) -> Mapping[str, object] | None:
    if payload is None:
        return None
    if not isinstance(payload, Mapping):
        raise ValueError("The 'payload' argument must be an object when provided.")
    normalized: dict[str, object] = {}
    for key, value in payload.items():
        if not isinstance(key, str):
            raise ValueError("All keys in 'payload' must be strings.")
        normalized[key] = deepcopy(value)
    return normalized


def _validate_path_params(operation: PaperclipOperation, path_params: Mapping[str, str]) -> None:
    allowed = set(operation.required_path_params)
    unexpected = sorted(set(path_params) - allowed)
    if unexpected:
        raise ValueError(
            f"Operation '{operation.name}' received unexpected path parameters: {', '.join(unexpected)}."
        )

    missing = [key for key in operation.required_path_params if not path_params.get(key)]
    if missing:
        raise ValueError(
            f"Operation '{operation.name}' requires path parameters: {', '.join(missing)}."
        )


def _validate_query(
    operation: PaperclipOperation,
    query: Mapping[str, str | int | float | bool] | None,
) -> None:
    if query is not None and not operation.allow_query:
        raise ValueError(f"Operation '{operation.name}' does not accept query parameters.")


def _validate_payload(
    operation: PaperclipOperation,
    payload: Mapping[str, object] | None,
) -> None:
    if operation.payload_kind == "none":
        if payload is not None:
            raise ValueError(f"Operation '{operation.name}' does not accept a payload.")
        return

    if payload is None and operation.payload_required:
        raise ValueError(f"Operation '{operation.name}' requires a payload.")


__all__ = [
    "PaperclipOperation",
    "PaperclipPreparedRequest",
    "_build_prepared_request",
    "build_paperclip_operation_catalog",
    "get_paperclip_operation",
]
