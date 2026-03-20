"""Shared HTTP transport protocol and error types."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Protocol


class RequestExecutor(Protocol):
    """Callable contract for executing JSON HTTP requests."""

    def __call__(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str] | None = None,
        json_body: Any | None = None,
        timeout_seconds: float = 60.0,
    ) -> Any:
        """Execute an HTTP request and return the decoded JSON payload."""


@dataclass(frozen=True, slots=True)
class ProviderHTTPError(RuntimeError):
    """Raised when a provider HTTP request fails."""

    provider: str
    message: str
    status_code: int | None = None
    url: str | None = None
    body: Any | None = None

    def __str__(self) -> str:
        prefix = f"{self.provider} request failed"
        if self.status_code is not None:
            prefix = f"{prefix} ({self.status_code})"
        return f"{prefix}: {self.message}"


__all__ = [
    "ProviderHTTPError",
    "RequestExecutor",
]
