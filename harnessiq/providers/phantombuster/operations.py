"""PhantomBuster operation catalog."""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PhantomBusterOperation:
    """Metadata for a single PhantomBuster API operation."""

    name: str
    category: str
    description: str

    def summary(self) -> str:
        return self.name


_CATALOG: OrderedDict[str, PhantomBusterOperation] = OrderedDict(
    [
        # ── Agents ────────────────────────────────────────────────────────
        (
            "get_agent",
            PhantomBusterOperation(
                name="get_agent",
                category="Agent",
                description="Fetch a single agent configuration by ID.",
            ),
        ),
        (
            "list_agents",
            PhantomBusterOperation(
                name="list_agents",
                category="Agent",
                description="List all automation agents in the workspace.",
            ),
        ),
        (
            "launch_agent",
            PhantomBusterOperation(
                name="launch_agent",
                category="Agent",
                description="Launch an agent, optionally with arguments and output format.",
            ),
        ),
        (
            "abort_agent",
            PhantomBusterOperation(
                name="abort_agent",
                category="Agent",
                description="Abort a currently running agent.",
            ),
        ),
        (
            "delete_agent",
            PhantomBusterOperation(
                name="delete_agent",
                category="Agent",
                description="Permanently delete an agent.",
            ),
        ),
        (
            "fetch_agent_output",
            PhantomBusterOperation(
                name="fetch_agent_output",
                category="Agent",
                description="Retrieve the output data from the last completed agent run.",
            ),
        ),
        (
            "save_agent_argument",
            PhantomBusterOperation(
                name="save_agent_argument",
                category="Agent",
                description="Save a reusable argument configuration for an agent.",
            ),
        ),
        # ── Containers ────────────────────────────────────────────────────
        (
            "get_container",
            PhantomBusterOperation(
                name="get_container",
                category="Container",
                description="Fetch details and output for a single container run by ID.",
            ),
        ),
        (
            "list_containers",
            PhantomBusterOperation(
                name="list_containers",
                category="Container",
                description="List containers (runs) for an agent, optionally filtered by status.",
            ),
        ),
        # ── Phantoms ──────────────────────────────────────────────────────
        (
            "get_phantom",
            PhantomBusterOperation(
                name="get_phantom",
                category="Phantom",
                description="Fetch a phantom (automation script template) by ID.",
            ),
        ),
        (
            "list_phantoms",
            PhantomBusterOperation(
                name="list_phantoms",
                category="Phantom",
                description="List all available phantom automation script templates.",
            ),
        ),
        # ── Scripts ───────────────────────────────────────────────────────
        (
            "list_scripts",
            PhantomBusterOperation(
                name="list_scripts",
                category="Script",
                description="List all available scripts.",
            ),
        ),
        (
            "get_script",
            PhantomBusterOperation(
                name="get_script",
                category="Script",
                description="Fetch a specific script by ID.",
            ),
        ),
        # ── Account ───────────────────────────────────────────────────────
        (
            "get_user_info",
            PhantomBusterOperation(
                name="get_user_info",
                category="Account",
                description="Get information about the authenticated user and credit balance.",
            ),
        ),
        (
            "list_org_members",
            PhantomBusterOperation(
                name="list_org_members",
                category="Account",
                description="List all members of the organisation.",
            ),
        ),
    ]
)


def build_phantombuster_operation_catalog() -> tuple[PhantomBusterOperation, ...]:
    """Return all registered PhantomBuster operations as an ordered tuple."""
    return tuple(_CATALOG.values())


def get_phantombuster_operation(name: str) -> PhantomBusterOperation:
    """Return the operation for *name*, raising :exc:`ValueError` if unknown."""
    try:
        return _CATALOG[name]
    except KeyError:
        known = ", ".join(_CATALOG)
        raise ValueError(f"Unknown PhantomBuster operation '{name}'. Known: {known}") from None


__all__ = [
    "PhantomBusterOperation",
    "build_phantombuster_operation_catalog",
    "get_phantombuster_operation",
]
