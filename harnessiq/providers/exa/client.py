"""Exa credentials and HTTP client."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Mapping

from harnessiq.providers.http import RequestExecutor, request_json
from harnessiq.shared.credentials import ExaCredentials


def create_exa_credentials() -> ExaCredentials:
    """Factory for --exa-credentials-factory CLI argument. Reads EXA_API_KEY from env."""
    api_key = os.environ.get("EXA_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("EXA_API_KEY environment variable is required.")
    return ExaCredentials(api_key=api_key)


@dataclass(frozen=True, slots=True)
class ExaClient:
    """Minimal Exa HTTP client suitable for tool execution and tests."""

    credentials: ExaCredentials
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
        from harnessiq.providers.exa.operations import _build_prepared_request
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
        """Execute one validated Exa operation and return the decoded response."""
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

