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

from harnessiq.shared.paperclip import PaperclipOperation, PaperclipPreparedRequest, build_paperclip_operation_catalog, get_paperclip_operation

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
    headers = build_headers(credentials.api_key, run_id=run_id if operation.supports_run_id else None)

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
            raise ValueError(f"Query parameter '{key}' must be a string, number, or boolean.")
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
        raise ValueError(f"Operation '{operation.name}' received unexpected path parameters: {', '.join(unexpected)}.")
    missing = [key for key in operation.required_path_params if not path_params.get(key)]
    if missing:
        raise ValueError(f"Operation '{operation.name}' requires path parameters: {', '.join(missing)}.")


def _validate_query(operation: PaperclipOperation, query: Mapping[str, str | int | float | bool] | None) -> None:
    if query is not None and not operation.allow_query:
        raise ValueError(f"Operation '{operation.name}' does not accept query parameters.")


def _validate_payload(operation: PaperclipOperation, payload: Mapping[str, object] | None) -> None:
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
