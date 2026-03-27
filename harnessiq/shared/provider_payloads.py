"""Shared helpers for DTO-backed provider payload dispatch."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from harnessiq.shared.dtos import ProviderPayloadRequestDTO, ProviderPayloadResultDTO


def require_payload_string(payload: Mapping[str, object], key: str) -> str:
    """Return one required non-empty string field from a provider payload."""

    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"The '{key}' field must be a non-empty string.")
    return value.strip()


def optional_payload_string(payload: Mapping[str, object], key: str) -> str | None:
    """Return one optional normalized string field from a provider payload."""

    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"The '{key}' field must be a string when provided.")
    normalized = value.strip()
    return normalized or None


def optional_payload_int(payload: Mapping[str, object], key: str) -> int | None:
    """Return one optional integer field from a provider payload."""

    value = payload.get(key)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"The '{key}' field must be an integer when provided.")
    return value


def optional_payload_bool(payload: Mapping[str, object], key: str) -> bool | None:
    """Return one optional boolean field from a provider payload."""

    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, bool):
        raise ValueError(f"The '{key}' field must be a boolean when provided.")
    return value


def optional_payload_string_list(payload: Mapping[str, object], key: str) -> list[str] | None:
    """Return one optional list of non-empty strings from a provider payload."""

    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, list):
        raise ValueError(f"The '{key}' field must be a list of strings when provided.")
    normalized: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"The '{key}' field must contain only non-empty strings.")
        normalized.append(item.strip())
    return normalized


def execute_payload_operation(
    target: object,
    request: ProviderPayloadRequestDTO,
) -> ProviderPayloadResultDTO:
    """Execute one reflected payload-based provider operation safely."""

    operation_name = request.operation
    if operation_name.startswith("_"):
        raise ValueError(f"Unsupported provider operation '{operation_name}'.")

    operation = getattr(target, operation_name, None)
    if not callable(operation):
        raise ValueError(f"Unsupported provider operation '{operation_name}'.")

    result = operation(**dict(request.payload))
    return ProviderPayloadResultDTO(operation=operation_name, result=result)


__all__ = [
    "execute_payload_operation",
    "optional_payload_bool",
    "optional_payload_int",
    "optional_payload_string",
    "optional_payload_string_list",
    "require_payload_string",
]
