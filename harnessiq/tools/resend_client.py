"""Resend client and request-preparation helpers."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Mapping
from urllib.parse import urlencode

from harnessiq.providers.http import RequestExecutor, request_json
from harnessiq.shared.resend import ResendCredentials, ResendOperation, ResendPreparedRequest
from harnessiq.tools.resend_catalog import _BATCH_VALIDATION_MODES, get_resend_operation


@dataclass(frozen=True, slots=True)
class ResendClient:
    """Small Resend HTTP client suitable for tool execution and tests."""

    credentials: ResendCredentials
    request_executor: RequestExecutor = request_json

    def prepare_request(
        self,
        operation_name: str,
        *,
        path_params: Mapping[str, object] | None = None,
        query: Mapping[str, object] | None = None,
        payload: Any | None = None,
        idempotency_key: str | None = None,
        batch_validation: str | None = None,
    ) -> ResendPreparedRequest:
        """Validate the operation inputs and build an executable request."""
        operation = get_resend_operation(operation_name)
        normalized_path_params = _normalize_path_params(path_params)
        _validate_path_params(operation, normalized_path_params)
        normalized_query = _normalize_mapping(query, field_name="query") if query is not None else None
        _validate_payload(operation, payload)
        _validate_headers(
            operation,
            idempotency_key=idempotency_key,
            batch_validation=batch_validation,
        )

        path = operation.path_builder(normalized_path_params)
        url = _build_url(self.credentials.base_url, path, query=normalized_query)
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.credentials.api_key}",
            "User-Agent": self.credentials.user_agent,
        }
        if idempotency_key is not None:
            headers["Idempotency-Key"] = idempotency_key
        if batch_validation is not None:
            headers["x-batch-validation"] = batch_validation

        return ResendPreparedRequest(
            operation=operation,
            method=operation.method,
            path=path,
            url=url,
            headers=headers,
            json_body=_copy_payload(payload),
        )

    def execute_operation(
        self,
        operation_name: str,
        *,
        path_params: Mapping[str, object] | None = None,
        query: Mapping[str, object] | None = None,
        payload: Any | None = None,
        idempotency_key: str | None = None,
        batch_validation: str | None = None,
    ) -> Any:
        """Execute one validated Resend operation and return the decoded response."""
        prepared = self.prepare_request(
            operation_name,
            path_params=path_params,
            query=query,
            payload=payload,
            idempotency_key=idempotency_key,
            batch_validation=batch_validation,
        )
        return self.request_executor(
            prepared.method,
            prepared.url,
            headers=prepared.headers,
            json_body=prepared.json_body,
            timeout_seconds=self.credentials.timeout_seconds,
        )


def coerce_resend_client(
    *,
    credentials: ResendCredentials | None,
    client: ResendClient | None,
) -> ResendClient:
    if client is not None:
        return client
    if credentials is None:
        raise ValueError("Either Resend credentials or a Resend client must be provided.")
    return ResendClient(credentials=credentials)


def require_resend_operation_name(
    arguments: Mapping[str, object],
    allowed_names: set[str] | frozenset[str],
) -> str:
    value = arguments["operation"]
    if not isinstance(value, str):
        raise ValueError("The 'operation' argument must be a string.")
    if value not in allowed_names:
        allowed = ", ".join(sorted(allowed_names))
        raise ValueError(f"Unsupported Resend operation '{value}' for this tool configuration. Allowed: {allowed}.")
    return value


def optional_resend_mapping(arguments: Mapping[str, object], key: str) -> Mapping[str, object] | None:
    if key not in arguments or arguments[key] is None:
        return None
    value = arguments[key]
    if not isinstance(value, Mapping):
        raise ValueError(f"The '{key}' argument must be an object when provided.")
    return value


def optional_resend_string(arguments: Mapping[str, object], key: str) -> str | None:
    if key not in arguments or arguments[key] is None:
        return None
    value = arguments[key]
    if not isinstance(value, str):
        raise ValueError(f"The '{key}' argument must be a string when provided.")
    return value


def _normalize_path_params(path_params: Mapping[str, object] | None) -> dict[str, str]:
    if path_params is None:
        return {}
    normalized = _normalize_mapping(path_params, field_name="path_params")
    return {key: str(value) for key, value in normalized.items()}


def _normalize_mapping(mapping: Mapping[str, object], *, field_name: str) -> dict[str, object]:
    normalized: dict[str, object] = {}
    for key, value in mapping.items():
        if not isinstance(key, str):
            raise ValueError(f"All keys in '{field_name}' must be strings.")
        normalized[key] = deepcopy(value)
    return normalized


def _validate_path_params(operation: ResendOperation, path_params: Mapping[str, str]) -> None:
    allowed = set(operation.required_path_params) | set(operation.optional_path_params)
    unexpected = sorted(set(path_params) - allowed)
    if unexpected:
        raise ValueError(
            f"Operation '{operation.name}' received unexpected path parameters: {', '.join(unexpected)}."
        )

    missing = [key for key in operation.required_path_params if not path_params.get(key)]
    if missing:
        raise ValueError(f"Operation '{operation.name}' requires path parameters: {', '.join(missing)}.")


def _validate_payload(operation: ResendOperation, payload: Any | None) -> None:
    if operation.payload_kind == "none":
        if payload is not None:
            raise ValueError(f"Operation '{operation.name}' does not accept a payload.")
        return

    if payload is None:
        if operation.payload_required:
            raise ValueError(f"Operation '{operation.name}' requires a payload.")
        return

    if operation.payload_kind == "object" and not isinstance(payload, Mapping):
        raise ValueError(f"Operation '{operation.name}' requires an object payload.")
    if operation.payload_kind == "array":
        if not isinstance(payload, list):
            raise ValueError(f"Operation '{operation.name}' requires an array payload.")
        for index, item in enumerate(payload):
            if not isinstance(item, Mapping):
                raise ValueError(f"Operation '{operation.name}' requires payload item {index} to be an object.")


def _validate_headers(
    operation: ResendOperation,
    *,
    idempotency_key: str | None,
    batch_validation: str | None,
) -> None:
    if idempotency_key is not None and not operation.supports_idempotency_key:
        raise ValueError(f"Operation '{operation.name}' does not support idempotency_key.")
    if batch_validation is not None:
        if not operation.supports_batch_validation:
            raise ValueError(f"Operation '{operation.name}' does not support batch_validation.")
        if batch_validation not in _BATCH_VALIDATION_MODES:
            modes = ", ".join(sorted(_BATCH_VALIDATION_MODES))
            raise ValueError(f"batch_validation must be one of: {modes}.")


def _copy_payload(payload: Any | None) -> Any | None:
    if payload is None:
        return None
    return deepcopy(payload)


def _build_url(base_url: str, path: str, *, query: Mapping[str, object] | None = None) -> str:
    base = base_url.rstrip("/")
    if not query:
        return f"{base}{path}"

    encoded_query = urlencode(list(_flatten_query_items(query)), doseq=True)
    return f"{base}{path}?{encoded_query}"


def _flatten_query_items(query: Mapping[str, object]) -> list[tuple[str, object]]:
    items: list[tuple[str, object]] = []
    for key, value in query.items():
        if isinstance(value, (list, tuple)):
            for item in value:
                items.append((key, item))
            continue
        items.append((key, value))
    return items


__all__ = [
    "ResendClient",
    "ResendCredentials",
    "ResendPreparedRequest",
]
