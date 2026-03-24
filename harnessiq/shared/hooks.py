"""Shared hook definitions and runtime data models."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

from harnessiq.shared.tools import ToolResult

HookPhase = Literal["before_run", "before_tool", "after_tool", "before_checkpoint"]
ApprovalPolicy = Literal["never", "on-request", "always"]

DEFAULT_APPROVAL_POLICY: ApprovalPolicy = "never"
SUPPORTED_APPROVAL_POLICIES: tuple[ApprovalPolicy, ...] = ("never", "on-request", "always")
SUPPORTED_HOOK_PHASES: tuple[HookPhase, ...] = (
    "before_run",
    "before_tool",
    "after_tool",
    "before_checkpoint",
)
_UNSET = object()


@dataclass(frozen=True, slots=True)
class HookContext:
    """Normalized runtime payload passed to one hook handler."""

    phase: HookPhase
    agent_name: str
    run_id: str | None
    cycle_index: int
    reset_count: int
    memory_path: str | None = None
    available_tool_keys: tuple[str, ...] = ()
    tool_key: str | None = None
    tool_name: str | None = None
    tool_arguments: dict[str, Any] | None = None
    tool_output: Any = None
    checkpoint_name: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        normalized_phase = str(self.phase).strip().lower()
        if normalized_phase not in set(SUPPORTED_HOOK_PHASES):
            raise ValueError(
                f"Unsupported hook phase '{self.phase}'. Supported phases: {', '.join(SUPPORTED_HOOK_PHASES)}."
            )
        object.__setattr__(self, "phase", normalized_phase)
        object.__setattr__(self, "agent_name", self.agent_name.strip())
        object.__setattr__(self, "available_tool_keys", tuple(str(key) for key in self.available_tool_keys))
        object.__setattr__(
            self,
            "tool_arguments",
            deepcopy(self.tool_arguments) if self.tool_arguments is not None else None,
        )
        object.__setattr__(self, "metadata", deepcopy(dict(self.metadata)))

    def with_updates(
        self,
        *,
        tool_arguments: dict[str, Any] | None = None,
        tool_output: Any | object = _UNSET,
        checkpoint_name: str | None | object = _UNSET,
        metadata: dict[str, Any] | None = None,
    ) -> "HookContext":
        return HookContext(
            phase=self.phase,
            agent_name=self.agent_name,
            run_id=self.run_id,
            cycle_index=self.cycle_index,
            reset_count=self.reset_count,
            memory_path=self.memory_path,
            available_tool_keys=self.available_tool_keys,
            tool_key=self.tool_key,
            tool_name=self.tool_name,
            tool_arguments=self.tool_arguments if tool_arguments is None else tool_arguments,
            tool_output=self.tool_output if tool_output is _UNSET else tool_output,
            checkpoint_name=self.checkpoint_name if checkpoint_name is _UNSET else checkpoint_name,
            metadata=self.metadata if metadata is None else metadata,
        )


@dataclass(frozen=True, slots=True)
class HookResponse:
    """Optional control payload returned by one hook."""

    tool_arguments: dict[str, Any] | None = None
    tool_result: ToolResult | None = None
    pause_reason: str | None = None
    pause_details: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if self.pause_reason is not None:
            normalized_reason = self.pause_reason.strip()
            if not normalized_reason:
                raise ValueError("pause_reason must not be blank when provided.")
            object.__setattr__(self, "pause_reason", normalized_reason)
        if self.tool_arguments is not None:
            object.__setattr__(self, "tool_arguments", deepcopy(self.tool_arguments))
        if self.pause_details is not None:
            object.__setattr__(self, "pause_details", deepcopy(self.pause_details))
        if self.pause_reason is not None and self.tool_result is not None:
            raise ValueError("HookResponse cannot define both pause_reason and tool_result.")
        if self.tool_result is not None and self.tool_arguments is not None:
            raise ValueError("HookResponse cannot define both tool_result and tool_arguments.")

    @property
    def pauses_run(self) -> bool:
        return self.pause_reason is not None


@dataclass(frozen=True, slots=True)
class HookDefinition:
    """Provider-agnostic metadata for a runtime hook."""

    key: str
    name: str
    description: str
    phases: tuple[HookPhase, ...]
    priority: int = 100

    def __post_init__(self) -> None:
        normalized_key = self.key.strip()
        normalized_name = self.name.strip()
        normalized_description = self.description.strip()
        if not normalized_key:
            raise ValueError("Hook key must not be blank.")
        if not normalized_name:
            raise ValueError("Hook name must not be blank.")
        if not normalized_description:
            raise ValueError("Hook description must not be blank.")
        normalized_phases = tuple(str(phase).strip().lower() for phase in self.phases)
        if not normalized_phases:
            raise ValueError("HookDefinition must declare at least one phase.")
        for phase in normalized_phases:
            if phase not in set(SUPPORTED_HOOK_PHASES):
                raise ValueError(
                    f"Unsupported hook phase '{phase}'. Supported phases: {', '.join(SUPPORTED_HOOK_PHASES)}."
                )
        object.__setattr__(self, "key", normalized_key)
        object.__setattr__(self, "name", normalized_name)
        object.__setattr__(self, "description", normalized_description)
        object.__setattr__(self, "phases", normalized_phases)

    def applies_to(self, phase: HookPhase) -> bool:
        return phase in self.phases

    def inspect(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "name": self.name,
            "description": self.description,
            "phases": list(self.phases),
            "priority": self.priority,
        }


class HookHandler(Protocol):
    """Callable runtime contract for hook handlers."""

    def __call__(self, context: HookContext) -> HookResponse | None:
        """Inspect one lifecycle event and optionally alter execution."""


@dataclass(frozen=True, slots=True)
class RegisteredHook:
    """Bind canonical hook metadata to an executable runtime handler."""

    definition: HookDefinition
    handler: HookHandler

    @property
    def key(self) -> str:
        return self.definition.key

    def applies_to(self, phase: HookPhase) -> bool:
        return self.definition.applies_to(phase)

    def execute(self, context: HookContext) -> HookResponse | None:
        return self.handler(context)

    def inspect(self) -> dict[str, Any]:
        payload = self.definition.inspect()
        payload["function"] = _describe_handler(self.handler)
        return payload


def _describe_handler(handler: HookHandler) -> dict[str, str]:
    handler_type = type(handler)
    module = getattr(handler, "__module__", handler_type.__module__)
    qualname = getattr(handler, "__qualname__", handler_type.__qualname__)
    name = getattr(handler, "__name__", qualname.split(".")[-1])
    return {
        "module": str(module),
        "qualname": str(qualname),
        "name": str(name),
    }


__all__ = [
    "ApprovalPolicy",
    "DEFAULT_APPROVAL_POLICY",
    "HookContext",
    "HookDefinition",
    "HookHandler",
    "HookPhase",
    "HookResponse",
    "RegisteredHook",
    "SUPPORTED_APPROVAL_POLICIES",
    "SUPPORTED_HOOK_PHASES",
]
