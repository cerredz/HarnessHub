"""PhantomBuster REST API request payload builders."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from harnessiq.providers.base import omit_none_values


def build_launch_agent_request(
    agent_id: str | int,
    *,
    output: str | None = None,
    arguments: dict[str, Any] | None = None,
    manual_launch: bool | None = None,
) -> dict[str, object]:
    """Build a request body to launch an agent."""
    return omit_none_values(
        {
            "id": agent_id,
            "output": output,
            "arguments": deepcopy(arguments) if arguments is not None else None,
            "manualLaunch": manual_launch,
        }
    )


def build_abort_agent_request(agent_id: str | int) -> dict[str, object]:
    """Build a request body to abort a running agent."""
    return {"id": agent_id}


def build_delete_agent_request(agent_id: str | int) -> dict[str, object]:
    """Build a request body to delete an agent."""
    return {"id": agent_id}


def build_save_agent_argument_request(
    agent_id: str | int,
    argument: dict[str, Any],
) -> dict[str, object]:
    """Build a request body to save an agent argument."""
    return {"id": agent_id, "argument": deepcopy(argument)}


def build_fetch_phantom_request(phantom_id: str | int) -> dict[str, object]:
    """Build a request body to fetch a phantom by ID."""
    return {"id": phantom_id}
