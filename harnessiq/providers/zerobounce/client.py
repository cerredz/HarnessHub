"""ZeroBounce credentials and HTTP client."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from harnessiq.providers.zerobounce.api import DEFAULT_BASE_URL, DEFAULT_BULK_BASE_URL
from harnessiq.providers.http import RequestExecutor, request_json


@dataclass(frozen=True, slots=True)
class ZeroBounceCredentials:
    """Runtime credentials for the ZeroBounce email validation API.

    ``api_key`` is passed as a query parameter on every request.
    ZeroBounce routes standard operations through ``base_url``
    (``api.zerobounce.net``) and bulk file operations through
    ``bulk_base_url`` (``bulkapi.zerobounce.net``).
    """

    api_key: str
    base_url: str = DEFAULT_BASE_URL
    bulk_base_url: str = DEFAULT_BULK_BASE_URL
    timeout_seconds: float = 60.0

    def __post_init__(self) -> None:
        if not self.api_key.strip():
            raise ValueError("ZeroBounce api_key must not be blank.")
        if not self.base_url.strip():
            raise ValueError("ZeroBounce base_url must not be blank.")
        if not self.bulk_base_url.strip():
            raise ValueError("ZeroBounce bulk_base_url must not be blank.")
        if self.timeout_seconds <= 0:
            raise ValueError("ZeroBounce timeout_seconds must be greater than zero.")

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
            "bulk_base_url": self.bulk_base_url,
            "timeout_seconds": self.timeout_seconds,
        }


@dataclass(frozen=True, slots=True)
class ZeroBounceClient:
    """Minimal ZeroBounce HTTP client suitable for tool execution and tests."""

    credentials: ZeroBounceCredentials
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
        from harnessiq.providers.zerobounce.operations import _build_prepared_request
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
        """Execute one validated ZeroBounce operation and return the decoded response."""
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
