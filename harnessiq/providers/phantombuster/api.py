"""PhantomBuster endpoint and authentication helpers."""

from __future__ import annotations

from typing import Mapping

from harnessiq.providers.base import omit_none_values
from harnessiq.providers.http import join_url

DEFAULT_BASE_URL = "https://api.phantombuster.com"


def build_headers(
    api_key: str,
    *,
    extra_headers: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Build the headers required for PhantomBuster API requests."""
    headers = omit_none_values({"X-Phantombuster-Key": api_key})
    if extra_headers:
        headers.update(extra_headers)
    return headers


# --- Agent endpoints ---


def agent_fetch_url(agent_id: str | int, base_url: str = DEFAULT_BASE_URL) -> str:
    """Return the URL to fetch a single agent."""
    return join_url(base_url, "/api/v2/agents/fetch", query={"id": str(agent_id)})


def agents_fetch_all_url(base_url: str = DEFAULT_BASE_URL) -> str:
    """Return the URL to list all agents."""
    return join_url(base_url, "/api/v2/agents/fetch-all")


def agents_launch_url(base_url: str = DEFAULT_BASE_URL) -> str:
    """Return the URL to launch an agent."""
    return join_url(base_url, "/api/v2/agents/launch")


def agents_abort_url(base_url: str = DEFAULT_BASE_URL) -> str:
    """Return the URL to abort an agent."""
    return join_url(base_url, "/api/v2/agents/abort")


def agents_delete_url(base_url: str = DEFAULT_BASE_URL) -> str:
    """Return the URL to delete an agent."""
    return join_url(base_url, "/api/v2/agents/delete")


def agent_fetch_output_url(
    agent_id: str | int,
    *,
    mode: str | None = None,
    base_url: str = DEFAULT_BASE_URL,
) -> str:
    """Return the URL to fetch agent output."""
    query: dict[str, str] = {"id": str(agent_id), "withOutput": "true"}
    if mode is not None:
        query["mode"] = mode
    return join_url(base_url, "/api/v2/agents/fetch-output", query=query)


def agents_save_argument_url(base_url: str = DEFAULT_BASE_URL) -> str:
    """Return the URL to save an agent argument."""
    return join_url(base_url, "/api/v2/agents/save-agent-argument")


# --- Container endpoints ---


def container_fetch_url(container_id: str | int, base_url: str = DEFAULT_BASE_URL) -> str:
    """Return the URL to fetch a single container."""
    return join_url(base_url, "/api/v2/containers/fetch", query={"id": str(container_id)})


def containers_fetch_all_url(
    agent_id: str | int,
    *,
    status: str | None = None,
    base_url: str = DEFAULT_BASE_URL,
) -> str:
    """Return the URL to list containers for an agent."""
    query: dict[str, str] = {"agentId": str(agent_id)}
    if status is not None:
        query["status"] = status
    return join_url(base_url, "/api/v2/containers/fetch-all", query=query)


# --- Phantom endpoints ---


def phantoms_fetch_url(base_url: str = DEFAULT_BASE_URL) -> str:
    """Return the URL to fetch a phantom."""
    return join_url(base_url, "/api/v2/phantoms/fetch")


def phantoms_fetch_all_url(base_url: str = DEFAULT_BASE_URL) -> str:
    """Return the URL to list all phantoms."""
    return join_url(base_url, "/api/v2/phantoms/fetch-all")


# --- User / Org endpoints ---


def user_me_url(base_url: str = DEFAULT_BASE_URL) -> str:
    """Return the URL to get user info."""
    return join_url(base_url, "/api/v2/user/me")


def org_members_url(base_url: str = DEFAULT_BASE_URL) -> str:
    """Return the URL to list org members."""
    return join_url(base_url, "/api/v2/orgs/fetch-members")


# --- Script endpoints ---


def scripts_fetch_all_url(base_url: str = DEFAULT_BASE_URL) -> str:
    """Return the URL to list all scripts."""
    return join_url(base_url, "/api/v2/scripts/fetch-all")


def script_fetch_url(script_id: str | int, base_url: str = DEFAULT_BASE_URL) -> str:
    """Return the URL to fetch a single script."""
    return join_url(base_url, "/api/v2/scripts/fetch", query={"id": str(script_id)})
