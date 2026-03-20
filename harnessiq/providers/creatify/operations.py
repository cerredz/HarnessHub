"""Creatify API operation catalog and request preparation primitives."""

from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING, Any, Mapping, Sequence
from urllib.parse import quote

from harnessiq.providers.http import join_url
from harnessiq.shared.tools import CREATIFY_REQUEST

if TYPE_CHECKING:
    from harnessiq.providers.creatify.client import CreatifyCredentials

from harnessiq.shared.creatify import CreatifyOperation, CreatifyPreparedRequest, build_creatify_operation_catalog, get_creatify_operation

def _build_prepared_request(
    *,
    operation_name: str,
    credentials: "CreatifyCredentials",
    path_params: Mapping[str, object] | None,
    query: Mapping[str, object] | None,
    payload: Any | None,
) -> CreatifyPreparedRequest:
    from harnessiq.providers.creatify.api import build_headers

    op = get_creatify_operation(operation_name)
    normalized_params = _normalize_path_params(path_params)
    _validate_path_params(op, normalized_params)
    _validate_payload(op, payload)

    path = _render_path(op.path_hint, normalized_params)
    full_url = join_url(credentials.base_url, path, query=_normalize_query(query) if query else None)
    headers = build_headers(credentials.api_id, credentials.api_key)

    return CreatifyPreparedRequest(
        operation=op,
        method=op.method,
        path=path,
        url=full_url,
        headers=headers,
        json_body=deepcopy(payload) if payload is not None else None,
    )


def _render_path(path_hint: str, path_params: dict[str, str]) -> str:
    rendered = path_hint
    for key, value in path_params.items():
        rendered = rendered.replace(f"{{{key}}}", quote(value, safe=""))
    return rendered


def _normalize_path_params(path_params: Mapping[str, object] | None) -> dict[str, str]:
    if not path_params:
        return {}
    return {str(k): str(v) for k, v in path_params.items()}


def _normalize_query(query: Mapping[str, object]) -> dict[str, str | int | float | bool]:
    return {str(k): v for k, v in query.items()}  # type: ignore[return-value]


def _validate_path_params(op: CreatifyOperation, params: dict[str, str]) -> None:
    missing = [k for k in op.required_path_params if not params.get(k)]
    if missing:
        raise ValueError(f"Operation '{op.name}' requires path parameters: {', '.join(missing)}.")


def _validate_payload(op: CreatifyOperation, payload: Any | None) -> None:
    if op.payload_kind == "none" and payload is not None:
        raise ValueError(f"Operation '{op.name}' does not accept a payload.")
    if op.payload_required and payload is None:
        raise ValueError(f"Operation '{op.name}' requires a payload.")


__all__ = [
    "CREATIFY_REQUEST",
    "CreatifyOperation",
    "CreatifyPreparedRequest",
    "_build_prepared_request",
    "build_creatify_operation_catalog",
    "get_creatify_operation",
]
