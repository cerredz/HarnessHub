"""Outreach credentials and HTTP client."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from harnessiq.providers.outreach.api import DEFAULT_BASE_URL
from harnessiq.providers.http import RequestExecutor, request_json


@dataclass(frozen=True, slots=True)
class OutreachCredentials:
    """Runtime credentials for the Outreach sales engagement API.

    ``access_token`` is an OAuth Bearer token issued via the Outreach
    OAuth 2.0 flow and used on every request.
    """

    access_token: str
    base_url: str = DEFAULT_BASE_URL
    timeout_seconds: float = 60.0

    def __post_init__(self) -> None:
        if not self.access_token.strip():
            raise ValueError("Outreach access_token must not be blank.")
        if not self.base_url.strip():
            raise ValueError("Outreach base_url must not be blank.")
        if self.timeout_seconds <= 0:
            raise ValueError("Outreach timeout_seconds must be greater than zero.")

    def masked_access_token(self) -> str:
        """Return a redacted version of the access token."""
        token = self.access_token
        if len(token) <= 4:
            return "*" * len(token)
        return f"{token[:3]}{'*' * max(1, len(token) - 7)}{token[-4:]}"

    def as_redacted_dict(self) -> dict[str, object]:
        """Return a safe-to-log credential summary."""
        return {
            "access_token_masked": self.masked_access_token(),
            "base_url": self.base_url,
            "timeout_seconds": self.timeout_seconds,
        }


@dataclass(frozen=True, slots=True)
class OutreachClient:
    """Minimal Outreach HTTP client suitable for tool execution and tests."""

    credentials: OutreachCredentials
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
        from harnessiq.providers.outreach.operations import _build_prepared_request
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
        """Execute one validated Outreach operation and return the decoded response."""
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
