"""Interface contracts for provider and tool request clients."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Mapping, Protocol, runtime_checkable

from harnessiq.shared.dtos import (
    PreparedProviderOperationResultDTO,
    ProviderOperationRequestDTO,
)


@runtime_checkable
class TimeoutConfig(Protocol):
    """Describe credentials or config objects that expose a request timeout."""

    timeout_seconds: float


@runtime_checkable
class RequestExecutor(Protocol):
    """Describe the shared HTTP request-executor call shape used by provider clients."""

    def __call__(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str] | None = None,
        json_body: Any | None = None,
        timeout_seconds: float = 60.0,
    ) -> Any:
        """Execute one request and return the decoded payload."""


@runtime_checkable
class PreparedRequest(Protocol):
    """Describe the executable request payload produced by provider clients."""

    method: str
    path: str
    url: str
    headers: Mapping[str, str]
    json_body: Any | None


@runtime_checkable
class RequestPreparingClient(Protocol):
    """Describe provider clients that validate inputs and prepare executable requests."""

    credentials: TimeoutConfig
    request_executor: RequestExecutor

    def prepare_request(
        self,
        request: ProviderOperationRequestDTO,
    ) -> PreparedRequest:
        """Build an executable request for one provider operation."""

    def execute_operation(
        self,
        request: ProviderOperationRequestDTO,
    ) -> PreparedProviderOperationResultDTO:
        """Execute one provider operation and return a typed result envelope."""


@runtime_checkable
class ResendRequestClient(Protocol):
    """Describe the richer Resend request-preparation client surface."""

    credentials: TimeoutConfig
    request_executor: RequestExecutor

    def prepare_request(
        self,
        operation_name: str,
        *,
        path_params: Mapping[str, object] | None = None,
        query: Mapping[str, object] | None = None,
        payload: Any | None = None,
        idempotency_key: str | None = None,
        batch_validation: str | None = None,
    ) -> PreparedRequest:
        """Build an executable Resend request for one operation."""


ProviderClientBuilder = Callable[[Any], RequestPreparingClient]


__all__ = [
    "PreparedRequest",
    "ProviderClientBuilder",
    "RequestExecutor",
    "RequestPreparingClient",
    "ResendRequestClient",
    "TimeoutConfig",
]
