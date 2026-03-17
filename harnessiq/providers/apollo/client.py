"""Apollo.io credentials and HTTP client."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from harnessiq.providers.apollo.api import DEFAULT_BASE_URL
from harnessiq.providers.http import RequestExecutor, request_json


@dataclass(frozen=True, slots=True)
class ApolloCredentials:
    """Runtime credentials for the Apollo.io sales intelligence API.

    ``api_key`` is issued from the Apollo.io dashboard under Settings >
    Integrations > API and sent via the ``X-Api-Key`` header on every
    request.  Many write and administrative endpoints require a master API
    key; scoped keys are accepted only for read-only search operations.
    """

    api_key: str
    base_url: str = DEFAULT_BASE_URL
    timeout_seconds: float = 60.0

    def __post_init__(self) -> None:
        if not self.api_key.strip():
            raise ValueError("Apollo api_key must not be blank.")
        if not self.base_url.strip():
            raise ValueError("Apollo base_url must not be blank.")
        if self.timeout_seconds <= 0:
            raise ValueError("Apollo timeout_seconds must be greater than zero.")

    def masked_api_key(self) -> str:
        """Return a redacted version of the API key safe for logging."""
        key = self.api_key
        if len(key) <= 4:
            return "*" * len(key)
        return f"{key[:3]}{'*' * max(1, len(key) - 7)}{key[-4:]}"

    def as_redacted_dict(self) -> dict[str, object]:
        """Return a safe-to-log credential summary."""
        return {
            "api_key_masked": self.masked_api_key(),
            "base_url": self.base_url,
            "timeout_seconds": self.timeout_seconds,
        }


@dataclass(frozen=True, slots=True)
class ApolloClient:
    """Minimal Apollo.io HTTP client suitable for tool execution and tests."""

    credentials: ApolloCredentials
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
        from harnessiq.providers.apollo.operations import _build_prepared_request
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
        """Execute one validated Apollo.io operation and return the decoded response."""
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
