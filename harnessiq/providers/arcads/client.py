"""Arcads credentials and HTTP client."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from harnessiq.providers.arcads.api import DEFAULT_BASE_URL
from harnessiq.providers.http import RequestExecutor, request_json


@dataclass(frozen=True, slots=True)
class ArcadsCredentials:
    """Runtime credentials for the Arcads AI video ad API.

    ``client_id`` and ``client_secret`` are issued from the Arcads
    dashboard and used for HTTP Basic Auth on every request.
    """

    client_id: str
    client_secret: str
    base_url: str = DEFAULT_BASE_URL
    timeout_seconds: float = 60.0

    def __post_init__(self) -> None:
        if not self.client_id.strip():
            raise ValueError("Arcads client_id must not be blank.")
        if not self.client_secret.strip():
            raise ValueError("Arcads client_secret must not be blank.")
        if not self.base_url.strip():
            raise ValueError("Arcads base_url must not be blank.")
        if self.timeout_seconds <= 0:
            raise ValueError("Arcads timeout_seconds must be greater than zero.")

    def masked_client_secret(self) -> str:
        """Return a redacted version of the client secret."""
        secret = self.client_secret
        if len(secret) <= 4:
            return "*" * len(secret)
        return f"{secret[:3]}{'*' * max(1, len(secret) - 7)}{secret[-4:]}"

    def as_redacted_dict(self) -> dict[str, object]:
        """Return a safe-to-log credential summary."""
        return {
            "client_id": self.client_id,
            "client_secret_masked": self.masked_client_secret(),
            "base_url": self.base_url,
            "timeout_seconds": self.timeout_seconds,
        }


@dataclass(frozen=True, slots=True)
class ArcadsClient:
    """Minimal Arcads HTTP client suitable for tool execution and tests."""

    credentials: ArcadsCredentials
    request_executor: RequestExecutor = request_json

    def prepare_request(
        self,
        operation_name: str,
        *,
        path_params: Mapping[str, object] | None = None,
        query: Mapping[str, object] | None = None,
        payload: Any | None = None,
    ) -> Any:
        """Validate inputs and build an executable request."""
        from harnessiq.providers.arcads.operations import _build_prepared_request
        return _build_prepared_request(
            operation_name=operation_name,
            credentials=self.credentials,
            path_params=path_params,
            query=query,
            payload=payload,
        )

    def execute_operation(
        self,
        operation_name: str,
        *,
        path_params: Mapping[str, object] | None = None,
        query: Mapping[str, object] | None = None,
        payload: Any | None = None,
    ) -> Any:
        """Execute one validated Arcads operation and return the decoded response."""
        prepared = self.prepare_request(
            operation_name,
            path_params=path_params,
            query=query,
            payload=payload,
        )
        return self.request_executor(
            prepared.method,
            prepared.url,
            headers=prepared.headers,
            json_body=prepared.json_body,
            timeout_seconds=self.credentials.timeout_seconds,
        )
