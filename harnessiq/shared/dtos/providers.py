"""Shared DTOs for provider-layer request and result boundaries."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any

from harnessiq.shared.dtos.base import SerializableDTO


def _coerce_mapping(mapping: Mapping[str, object] | None) -> dict[str, object]:
    if mapping is None:
        return {}
    return {str(key): deepcopy(value) for key, value in mapping.items()}


@dataclass(frozen=True, slots=True)
class ProviderOperationRequestDTO(SerializableDTO):
    """Public DTO for prepared-request provider client calls."""

    operation: str
    path_params: dict[str, object] = field(default_factory=dict)
    query: dict[str, object] = field(default_factory=dict)
    payload: Any | None = None
    run_id: str | None = None

    def __post_init__(self) -> None:
        normalized_operation = self.operation.strip()
        if not normalized_operation:
            raise ValueError("Provider operation must not be blank.")
        object.__setattr__(self, "operation", normalized_operation)
        object.__setattr__(self, "path_params", _coerce_mapping(self.path_params))
        object.__setattr__(self, "query", _coerce_mapping(self.query))
        object.__setattr__(self, "payload", deepcopy(self.payload))
        if self.run_id is not None:
            normalized_run_id = self.run_id.strip()
            object.__setattr__(self, "run_id", normalized_run_id or None)

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"operation": self.operation}
        if self.path_params:
            payload["path_params"] = deepcopy(self.path_params)
        if self.query:
            payload["query"] = deepcopy(self.query)
        if self.payload is not None:
            payload["payload"] = deepcopy(self.payload)
        if self.run_id is not None:
            payload["run_id"] = self.run_id
        return payload


@dataclass(frozen=True, slots=True)
class PreparedProviderOperationResultDTO(SerializableDTO):
    """Public DTO for prepared-request provider execution results."""

    operation: str
    method: str
    path: str
    response: Any

    def __post_init__(self) -> None:
        object.__setattr__(self, "operation", self.operation.strip())
        object.__setattr__(self, "method", self.method.strip())
        object.__setattr__(self, "path", self.path.strip())
        object.__setattr__(self, "response", deepcopy(self.response))

    @classmethod
    def from_prepared_request(
        cls,
        *,
        prepared: Any,
        response: Any,
    ) -> "PreparedProviderOperationResultDTO":
        return cls(
            operation=str(prepared.operation.name),
            method=str(prepared.method),
            path=str(prepared.path),
            response=response,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "operation": self.operation,
            "method": self.method,
            "path": self.path,
            "response": deepcopy(self.response),
        }


@dataclass(frozen=True, slots=True)
class ProviderPayloadRequestDTO(SerializableDTO):
    """Public DTO for payload-dispatch provider tool and client calls."""

    operation: str
    payload: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        normalized_operation = self.operation.strip()
        if not normalized_operation:
            raise ValueError("Provider operation must not be blank.")
        object.__setattr__(self, "operation", normalized_operation)
        object.__setattr__(self, "payload", _coerce_mapping(self.payload))

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"operation": self.operation}
        if self.payload:
            payload["payload"] = deepcopy(self.payload)
        return payload


@dataclass(frozen=True, slots=True)
class ProviderPayloadResultDTO(SerializableDTO):
    """Public DTO for payload-dispatch provider execution results."""

    operation: str
    result: Any

    def __post_init__(self) -> None:
        object.__setattr__(self, "operation", self.operation.strip())
        object.__setattr__(self, "result", deepcopy(self.result))

    def to_dict(self) -> dict[str, Any]:
        return {
            "operation": self.operation,
            "result": deepcopy(self.result),
        }


@dataclass(frozen=True, slots=True)
class ArxivOperationResultDTO(SerializableDTO):
    """Public DTO for arXiv tool/client result envelopes."""

    operation: str
    result_fields: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        normalized_operation = self.operation.strip()
        if not normalized_operation:
            raise ValueError("Provider operation must not be blank.")
        object.__setattr__(self, "operation", normalized_operation)
        object.__setattr__(self, "result_fields", _coerce_mapping(self.result_fields))

    @classmethod
    def from_search(cls, *, results: list[dict[str, Any]]) -> "ArxivOperationResultDTO":
        return cls(operation="search", result_fields={"results": results, "count": len(results)})

    @classmethod
    def from_search_raw(cls, *, xml: str) -> "ArxivOperationResultDTO":
        return cls(operation="search_raw", result_fields={"xml": xml})

    @classmethod
    def from_get_paper(cls, *, paper: dict[str, Any] | None) -> "ArxivOperationResultDTO":
        return cls(operation="get_paper", result_fields={"paper": paper})

    @classmethod
    def from_download_paper(cls, *, saved_to: str) -> "ArxivOperationResultDTO":
        return cls(operation="download_paper", result_fields={"saved_to": saved_to})

    def to_dict(self) -> dict[str, Any]:
        payload = {"operation": self.operation}
        payload.update(deepcopy(self.result_fields))
        return payload


__all__ = [
    "ArxivOperationResultDTO",
    "PreparedProviderOperationResultDTO",
    "ProviderOperationRequestDTO",
    "ProviderPayloadRequestDTO",
    "ProviderPayloadResultDTO",
]
