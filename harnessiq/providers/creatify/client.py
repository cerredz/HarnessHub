"""Creatify credentials and HTTP client."""

from __future__ import annotations

from dataclasses import dataclass

from harnessiq.providers.creatify.operations import CreatifyPreparedRequest
from harnessiq.providers.http import RequestExecutor, request_json
from harnessiq.shared.credentials import CreatifyCredentials
from harnessiq.shared.dtos import PreparedProviderOperationResultDTO, ProviderOperationRequestDTO


@dataclass(frozen=True, slots=True)
class CreatifyClient:
    """Minimal Creatify HTTP client suitable for tool execution and tests."""

    credentials: CreatifyCredentials
    request_executor: RequestExecutor = request_json

    def prepare_request(
        self,
        request: ProviderOperationRequestDTO,
    ) -> CreatifyPreparedRequest:
        """Validate the operation inputs and build an executable request."""
        from harnessiq.providers.creatify.operations import _build_prepared_request
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
        """Execute one validated Creatify operation and return the decoded response."""
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

