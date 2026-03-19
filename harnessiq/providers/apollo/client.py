"""Apollo credentials and HTTP client."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from harnessiq.providers.apollo.credentials import ApolloCredentials
from harnessiq.providers.http import RequestExecutor, request_json


@dataclass(frozen=True, slots=True)
class ApolloClient:
    """Minimal Apollo HTTP client suitable for tool execution and tests."""

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
        """Execute one validated Apollo operation and return the decoded response."""
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


__all__ = [
    "ApolloClient",
    "ApolloCredentials",
]
