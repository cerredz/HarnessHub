"""Exa credentials and HTTP client."""

from __future__ import annotations

import os
from dataclasses import dataclass

from harnessiq.providers.http import RequestExecutor, request_json
from harnessiq.shared.credentials import ExaCredentials
from harnessiq.shared.dtos import PreparedProviderOperationResultDTO, ProviderOperationRequestDTO
from harnessiq.shared.validated import NonEmptyString


def create_exa_credentials() -> ExaCredentials:
    """Factory for --exa-credentials-factory CLI argument. Reads EXA_API_KEY from env."""
    raw_api_key = os.environ.get("EXA_API_KEY", "")
    if not raw_api_key.strip():
        raise RuntimeError("EXA_API_KEY environment variable is required.")
    return ExaCredentials(api_key=NonEmptyString(raw_api_key, field_name="EXA_API_KEY environment variable"))


@dataclass(frozen=True, slots=True)
class ExaClient:
    """Minimal Exa HTTP client suitable for tool execution and tests."""

    credentials: ExaCredentials
    request_executor: RequestExecutor = request_json

    def prepare_request(self, request: ProviderOperationRequestDTO) -> object:
        """Validate inputs and build an executable request."""
        from harnessiq.providers.exa.operations import _build_prepared_request
        return _build_prepared_request(
            operation_name=request.operation,
            credentials=self.credentials,
            path_params=request.path_params or None,
            query=request.query or None,
            payload=request.payload,
        )

    def execute_operation(
        self,
        request: ProviderOperationRequestDTO,
    ) -> PreparedProviderOperationResultDTO:
        """Execute one validated Exa operation and return the decoded response."""
        prepared = self.prepare_request(request)
        response = self.request_executor(
            prepared.method,
            prepared.url,
            headers=prepared.headers,
            json_body=prepared.json_body,
            timeout_seconds=self.credentials.timeout_seconds,
        )
        return PreparedProviderOperationResultDTO.from_prepared_request(
            prepared=prepared,
            response=response,
        )

