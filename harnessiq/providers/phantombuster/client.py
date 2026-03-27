"""Thin PhantomBuster API client wrapper."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from harnessiq.providers.http import RequestExecutor, request_json
from harnessiq.providers.phantombuster.operations import get_phantombuster_operation
from harnessiq.providers.phantombuster.api import (
    DEFAULT_BASE_URL,
    agent_fetch_output_url,
    agent_fetch_url,
    agents_abort_url,
    agents_delete_url,
    agents_fetch_all_url,
    agents_launch_url,
    agents_save_argument_url,
    build_headers,
    container_fetch_url,
    containers_fetch_all_url,
    org_members_url,
    phantoms_fetch_all_url,
    phantoms_fetch_url,
    script_fetch_url,
    scripts_fetch_all_url,
    user_me_url,
)
from harnessiq.providers.phantombuster.requests import (
    build_abort_agent_request,
    build_delete_agent_request,
    build_fetch_phantom_request,
    build_launch_agent_request,
    build_save_agent_argument_request,
)
from harnessiq.shared.dtos import ProviderPayloadRequestDTO, ProviderPayloadResultDTO
from harnessiq.shared.provider_payloads import execute_payload_operation


@dataclass(frozen=True, slots=True)
class PhantomBusterClient:
    """Minimal PhantomBuster API client.

    Args:
        api_key: PhantomBuster API key passed in ``X-Phantombuster-Key`` header.
        base_url: Override the default API base URL.
        timeout_seconds: Per-request timeout in seconds.
        request_executor: Pluggable HTTP executor for testing.
    """

    api_key: str
    base_url: str = DEFAULT_BASE_URL
    timeout_seconds: float = 60.0
    request_executor: RequestExecutor = request_json

    # --- Agent methods ---

    def get_agent(self, agent_id: str | int) -> Any:
        """Fetch a single agent by ID."""
        return self._request("GET", agent_fetch_url(agent_id, self.base_url))

    def list_agents(self) -> Any:
        """List all agents in the workspace."""
        return self._request("GET", agents_fetch_all_url(self.base_url))

    def launch_agent(
        self,
        agent_id: str | int,
        *,
        output: str | None = None,
        arguments: dict[str, Any] | None = None,
        manual_launch: bool | None = None,
    ) -> Any:
        """Launch an agent."""
        payload = build_launch_agent_request(
            agent_id,
            output=output,
            arguments=arguments,
            manual_launch=manual_launch,
        )
        return self._request("POST", agents_launch_url(self.base_url), json_body=payload)

    def abort_agent(self, agent_id: str | int) -> Any:
        """Abort a running agent."""
        payload = build_abort_agent_request(agent_id)
        return self._request("POST", agents_abort_url(self.base_url), json_body=payload)

    def delete_agent(self, agent_id: str | int) -> Any:
        """Delete an agent."""
        payload = build_delete_agent_request(agent_id)
        return self._request("DELETE", agents_delete_url(self.base_url), json_body=payload)

    def fetch_agent_output(
        self,
        agent_id: str | int,
        *,
        mode: str | None = None,
    ) -> Any:
        """Fetch output for a completed agent run."""
        return self._request("GET", agent_fetch_output_url(agent_id, mode=mode, base_url=self.base_url))

    def save_agent_argument(
        self,
        agent_id: str | int,
        argument: dict[str, Any],
    ) -> Any:
        """Save a reusable argument for an agent."""
        payload = build_save_agent_argument_request(agent_id, argument)
        return self._request("POST", agents_save_argument_url(self.base_url), json_body=payload)

    # --- Container methods ---

    def get_container(self, container_id: str | int) -> Any:
        """Fetch a single container by ID."""
        return self._request("GET", container_fetch_url(container_id, self.base_url))

    def list_containers(
        self,
        agent_id: str | int,
        *,
        status: str | None = None,
    ) -> Any:
        """List containers for an agent, optionally filtered by status."""
        return self._request("GET", containers_fetch_all_url(agent_id, status=status, base_url=self.base_url))

    # --- Phantom methods ---

    def get_phantom(self, phantom_id: str | int) -> Any:
        """Fetch a phantom by ID."""
        payload = build_fetch_phantom_request(phantom_id)
        return self._request("POST", phantoms_fetch_url(self.base_url), json_body=payload)

    def list_phantoms(self) -> Any:
        """List all available phantoms."""
        return self._request("GET", phantoms_fetch_all_url(self.base_url))

    # --- User / Org methods ---

    def get_user_info(self) -> Any:
        """Get information about the authenticated user."""
        return self._request("GET", user_me_url(self.base_url))

    def list_org_members(self) -> Any:
        """List members of the organisation."""
        return self._request("GET", org_members_url(self.base_url))

    # --- Script methods ---

    def list_scripts(self) -> Any:
        """List all available scripts."""
        return self._request("GET", scripts_fetch_all_url(self.base_url))

    def get_script(self, script_id: str | int) -> Any:
        """Fetch a single script by ID."""
        return self._request("GET", script_fetch_url(script_id, self.base_url))

    def execute_operation(self, request: ProviderPayloadRequestDTO) -> ProviderPayloadResultDTO:
        """Execute one PhantomBuster operation from a DTO envelope."""

        get_phantombuster_operation(request.operation)
        return execute_payload_operation(self, request)

    # --- Internal ---

    def _request(
        self,
        method: str,
        url: str,
        *,
        json_body: dict[str, Any] | None = None,
    ) -> Any:
        return self.request_executor(
            method,
            url,
            headers=build_headers(self.api_key),
            json_body=dict(json_body) if json_body is not None else None,
            timeout_seconds=self.timeout_seconds,
        )
