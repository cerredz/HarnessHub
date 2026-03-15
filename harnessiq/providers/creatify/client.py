"""Creatify credentials and HTTP client."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from harnessiq.providers.creatify.api import DEFAULT_BASE_URL, build_headers
from harnessiq.providers.creatify.operations import (
    CreatifyOperation,
    CreatifyPreparedRequest,
    get_creatify_operation,
)
from harnessiq.providers.http import RequestExecutor, join_url, request_json


@dataclass(frozen=True, slots=True)
class CreatifyCredentials:
    """Runtime credentials for the Creatify API.

    Both ``api_id`` and ``api_key`` are obtained from the Creatify
    dashboard (Settings → API).
    """

    api_id: str
    api_key: str
    base_url: str = DEFAULT_BASE_URL
    timeout_seconds: float = 60.0

    def __post_init__(self) -> None:
        if not self.api_id.strip():
            raise ValueError("Creatify api_id must not be blank.")
        if not self.api_key.strip():
            raise ValueError("Creatify api_key must not be blank.")
        if not self.base_url.strip():
            raise ValueError("Creatify base_url must not be blank.")
        if self.timeout_seconds <= 0:
            raise ValueError("Creatify timeout_seconds must be greater than zero.")

    def masked_api_key(self) -> str:
        """Return a redacted version of the API key."""
        key = self.api_key
        if len(key) <= 4:
            return "*" * len(key)
        return f"{key[:3]}{'*' * max(1, len(key) - 7)}{key[-4:]}"

    def as_redacted_dict(self) -> dict[str, object]:
        """Return a safe-to-log credential summary."""
        return {
            "api_id": self.api_id,
            "api_key_masked": self.masked_api_key(),
            "base_url": self.base_url,
            "timeout_seconds": self.timeout_seconds,
        }


@dataclass(frozen=True, slots=True)
class CreatifyClient:
    """Minimal Creatify HTTP client suitable for tool execution and tests."""

    credentials: CreatifyCredentials
    request_executor: RequestExecutor = request_json

    def prepare_request(
        self,
        operation_name: str,
        *,
        path_params: Mapping[str, object] | None = None,
        query: Mapping[str, object] | None = None,
        payload: Any | None = None,
    ) -> CreatifyPreparedRequest:
        """Validate the operation inputs and build an executable request."""
        from harnessiq.providers.creatify.operations import _build_prepared_request
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
        """Execute one validated Creatify operation and return the decoded response."""
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
