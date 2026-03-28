"""Shared agent constants, aliases, and runtime data models."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal, Protocol, Sequence, TypedDict

from harnessiq.shared.hooks import (
    DEFAULT_APPROVAL_POLICY,
    SUPPORTED_APPROVAL_POLICIES,
    ApprovalPolicy,
)
from harnessiq.shared.tool_selection import ToolSelectionConfig
from harnessiq.shared.tools import ToolCall, ToolDefinition, ToolResult

if TYPE_CHECKING:
    from harnessiq.shared.hooks import RegisteredHook
    from harnessiq.utils.ledger import OutputSink

DEFAULT_AGENT_MAX_TOKENS = 80_000
DEFAULT_AGENT_RESET_THRESHOLD = 0.9
DEFAULT_AGENT_PRUNE_PROGRESS_INTERVAL: int | None = None
DEFAULT_AGENT_PRUNE_TOKEN_LIMIT: int | None = None
DEFAULT_AGENT_LANGSMITH_TRACING_ENABLED = True
_UNSET = object()

AgentContextEntryKind = Literal["parameter", "message", "assistant", "tool_call", "tool_result", "summary", "context"]
AgentMessageRole = Literal["system", "user", "assistant"]
AgentTranscriptEntryType = Literal["assistant", "user", "tool_call", "tool_result", "summary", "context"]
AgentRunStatus = Literal["completed", "paused", "max_cycles_reached"]
AgentContextDirectivePriority = Literal["critical", "standard", "advisory"]
AgentContextSectionPosition = Literal["first", "last", "after_master_prompt", "before_memory"]
AgentContextMemoryUpdateRule = Literal["overwrite", "append", "write_once"]

DEFAULT_AGENT_CONTEXT_MEMORY_FIELD_RULES: dict[str, AgentContextMemoryUpdateRule] = {
    "completed_steps": "append",
    "continuation_pointer": "overwrite",
    "current_phase": "overwrite",
    "discovered_entities": "append",
    "input_hash": "write_once",
    "last_completed_step": "overwrite",
    "open_questions": "append",
    "original_objective": "write_once",
    "reset_history": "append",
    "task_start_timestamp": "write_once",
    "verified_outputs": "append",
}


class _AgentContextEntryRequired(TypedDict):
    kind: AgentContextEntryKind


class AgentContextEntry(_AgentContextEntryRequired, total=False):
    """A normalized agent context-window entry."""

    role: AgentMessageRole
    content: str
    label: str
    tool_key: str
    tool_call_id: str
    arguments: dict[str, Any]
    output: Any
    metadata: dict[str, Any]
    tag: str
    note_type: str
    synthetic: bool


AgentContextWindow = list[AgentContextEntry]


def estimate_text_tokens(text: str) -> int:
    """Estimate token usage without depending on a tokenizer library."""
    if not text:
        return 0
    return max(1, (len(text) + 3) // 4)


@dataclass(frozen=True, slots=True)
class AgentRuntimeConfig:
    """Runtime controls for the generic agent loop."""

    max_tokens: int = DEFAULT_AGENT_MAX_TOKENS
    reset_threshold: float = DEFAULT_AGENT_RESET_THRESHOLD
    hooks: tuple["RegisteredHook", ...] = ()
    include_default_hooks: bool = True
    approval_policy: ApprovalPolicy = DEFAULT_APPROVAL_POLICY
    allowed_tools: tuple[str, ...] = ()
    tool_selection: ToolSelectionConfig = field(default_factory=ToolSelectionConfig)
    output_sinks: tuple["OutputSink", ...] = ()
    include_default_output_sink: bool = True
    prune_progress_interval: int | None = DEFAULT_AGENT_PRUNE_PROGRESS_INTERVAL
    prune_token_limit: int | None = DEFAULT_AGENT_PRUNE_TOKEN_LIMIT
    langsmith_tracing_enabled: bool = DEFAULT_AGENT_LANGSMITH_TRACING_ENABLED
    langsmith_api_key: str | None = None
    langsmith_project: str | None = None
    langsmith_api_url: str | None = None
    session_id: str | None = None

    def __post_init__(self) -> None:
        if self.max_tokens <= 0:
            message = "max_tokens must be greater than zero."
            raise ValueError(message)
        if not 0 < self.reset_threshold <= 1:
            message = "reset_threshold must be between 0 and 1."
            raise ValueError(message)
        object.__setattr__(self, "hooks", tuple(self.hooks))
        normalized_approval_policy = str(self.approval_policy).strip().lower()
        if normalized_approval_policy not in set(SUPPORTED_APPROVAL_POLICIES):
            message = (
                f"approval_policy must be one of {', '.join(SUPPORTED_APPROVAL_POLICIES)}."
            )
            raise ValueError(message)
        object.__setattr__(self, "approval_policy", normalized_approval_policy)
        normalized_allowed_tools: list[str] = []
        seen_allowed_tools: set[str] = set()
        for pattern in self.allowed_tools:
            candidate = str(pattern).strip()
            if not candidate or candidate in seen_allowed_tools:
                continue
            seen_allowed_tools.add(candidate)
            normalized_allowed_tools.append(candidate)
        object.__setattr__(self, "allowed_tools", tuple(normalized_allowed_tools))
        if not isinstance(self.tool_selection, ToolSelectionConfig):
            raise ValueError("tool_selection must be a ToolSelectionConfig instance.")
        object.__setattr__(self, "output_sinks", tuple(self.output_sinks))
        if self.prune_progress_interval is not None and self.prune_progress_interval <= 0:
            message = "prune_progress_interval must be greater than zero when provided."
            raise ValueError(message)
        if self.prune_token_limit is not None and self.prune_token_limit <= 0:
            message = "prune_token_limit must be greater than zero when provided."
            raise ValueError(message)
        if self.langsmith_api_key is not None:
            normalized_api_key = self.langsmith_api_key.strip()
            object.__setattr__(self, "langsmith_api_key", normalized_api_key or None)
        if self.langsmith_project is not None:
            normalized_project = self.langsmith_project.strip()
            object.__setattr__(self, "langsmith_project", normalized_project or None)
        if self.langsmith_api_url is not None:
            normalized_api_url = self.langsmith_api_url.strip()
            object.__setattr__(self, "langsmith_api_url", normalized_api_url or None)
        if self.session_id is not None:
            normalized_session_id = self.session_id.strip()
            object.__setattr__(self, "session_id", normalized_session_id or None)

    @property
    def reset_token_limit(self) -> int:
        """Return the token estimate that should trigger a transcript reset."""
        return max(1, int(self.max_tokens * self.reset_threshold))


def merge_agent_runtime_config(
    runtime_config: AgentRuntimeConfig | None,
    *,
    max_tokens: int,
    reset_threshold: float,
    prune_progress_interval: int | None | object = _UNSET,
    prune_token_limit: int | None | object = _UNSET,
) -> AgentRuntimeConfig:
    """Return a runtime config with shared settings preserved and scalar limits overridden."""
    if runtime_config is None:
        return AgentRuntimeConfig(
            max_tokens=max_tokens,
            reset_threshold=reset_threshold,
            prune_progress_interval=(
                DEFAULT_AGENT_PRUNE_PROGRESS_INTERVAL
                if prune_progress_interval is _UNSET
                else prune_progress_interval
            ),
            prune_token_limit=(
                DEFAULT_AGENT_PRUNE_TOKEN_LIMIT
                if prune_token_limit is _UNSET
                else prune_token_limit
            ),
        )
    return AgentRuntimeConfig(
        max_tokens=max_tokens,
        reset_threshold=reset_threshold,
        hooks=runtime_config.hooks,
        include_default_hooks=runtime_config.include_default_hooks,
        approval_policy=runtime_config.approval_policy,
        allowed_tools=runtime_config.allowed_tools,
        tool_selection=runtime_config.tool_selection,
        output_sinks=runtime_config.output_sinks,
        include_default_output_sink=runtime_config.include_default_output_sink,
        prune_progress_interval=(
            runtime_config.prune_progress_interval
            if prune_progress_interval is _UNSET
            else prune_progress_interval
        ),
        prune_token_limit=(
            runtime_config.prune_token_limit
            if prune_token_limit is _UNSET
            else prune_token_limit
        ),
        langsmith_tracing_enabled=runtime_config.langsmith_tracing_enabled,
        langsmith_api_key=runtime_config.langsmith_api_key,
        langsmith_project=runtime_config.langsmith_project,
        langsmith_api_url=runtime_config.langsmith_api_url,
        session_id=runtime_config.session_id,
    )


@dataclass(frozen=True, slots=True)
class AgentParameterSection:
    """A named durable parameter block injected into model context."""

    title: str
    content: str

    def render(self) -> str:
        return f"## {self.title}\n{self.content}".rstrip()


def render_json_parameter_content(
    payload: Any,
    *,
    indent: int = 2,
    sort_keys: bool = True,
) -> str:
    """Render JSON payloads for durable parameter sections."""
    return json.dumps(payload, indent=indent, sort_keys=sort_keys, default=str)


def json_parameter_section(
    title: str,
    payload: Any,
    *,
    indent: int = 2,
    sort_keys: bool = True,
) -> AgentParameterSection:
    """Return an ``AgentParameterSection`` backed by JSON content."""
    return AgentParameterSection(
        title=title,
        content=render_json_parameter_content(payload, indent=indent, sort_keys=sort_keys),
    )


@dataclass(frozen=True, slots=True)
class AgentTranscriptEntry:
    """A single rolling transcript entry managed by the harness."""

    entry_type: AgentTranscriptEntryType
    content: str = ""
    role: AgentMessageRole = "assistant"
    tool_key: str | None = None
    tool_call_id: str | None = None
    arguments: dict[str, Any] | None = None
    output: Any = None
    label: str | None = None
    metadata: dict[str, Any] | None = None

    def render(self) -> str:
        if self.entry_type == "assistant":
            label = "[ASSISTANT TURN]"
        elif self.entry_type == "user":
            label = "[USER TURN]"
        elif self.entry_type == "tool_call":
            label = "[TOOL CALL]"
        elif self.entry_type == "summary":
            label = "[SUMMARY]"
        elif self.entry_type == "context":
            context_label = self.label or "CONTEXT"
            return f"[CONTEXT: {context_label}]\n{self.content}".rstrip()
        else:
            label = "[TOOL RESULT]"
        if self.entry_type == "tool_call" and (self.tool_key or self.arguments is not None):
            rendered_arguments = json.dumps(self.arguments or {}, sort_keys=True, default=str)
            body = self.content or f"{self.tool_key or 'tool'}\n{rendered_arguments}"
            return f"{label}\n{body}".rstrip()
        if self.entry_type == "tool_result" and (self.tool_key or self.output is not None):
            rendered_output = json.dumps(self.output, indent=2, sort_keys=True, default=str)
            body = self.content or f"{self.tool_key or 'tool'}\n{rendered_output}"
            return f"{label}\n{body}".rstrip()
        return f"{label}\n{self.content}".rstrip()


@dataclass(frozen=True, slots=True)
class AgentContextDirective:
    """One durable system-prompt extension directive."""

    directive_id: str
    directive: str
    priority: AgentContextDirectivePriority
    created_at_reset: int
    expires_after_resets: int | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "directive_id": self.directive_id,
            "directive": self.directive,
            "priority": self.priority,
            "created_at_reset": self.created_at_reset,
            "expires_after_resets": self.expires_after_resets,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "AgentContextDirective":
        expires_after_resets = payload.get("expires_after_resets")
        return cls(
            directive_id=str(payload["directive_id"]),
            directive=str(payload["directive"]),
            priority=str(payload["priority"]),
            created_at_reset=int(payload.get("created_at_reset", 0)),
            expires_after_resets=(
                int(expires_after_resets)
                if expires_after_resets is not None
                else None
            ),
        )

    def is_active(self, reset_count: int) -> bool:
        if self.expires_after_resets is None:
            return True
        return reset_count < self.created_at_reset + self.expires_after_resets


@dataclass(frozen=True, slots=True)
class AgentInjectedSection:
    """One BaseAgent-owned durable parameter section."""

    label: str
    content: str
    position: AgentContextSectionPosition = "last"

    def as_dict(self) -> dict[str, str]:
        return {
            "label": self.label,
            "content": self.content,
            "position": self.position,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "AgentInjectedSection":
        return cls(
            label=str(payload["label"]),
            content=str(payload["content"]),
            position=str(payload.get("position", "last")),
        )


@dataclass(frozen=True, slots=True)
class AgentContextCheckpoint:
    """Persisted audit checkpoint for the full context window."""

    key: str
    checkpoint_name: str
    description: str | None
    token_count: int
    saved_at_reset: int
    saved_at_cycle: int
    context_window: tuple[AgentContextEntry, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "checkpoint_name": self.checkpoint_name,
            "description": self.description,
            "token_count": self.token_count,
            "saved_at_reset": self.saved_at_reset,
            "saved_at_cycle": self.saved_at_cycle,
            "context_window": list(self.context_window),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "AgentContextCheckpoint":
        context_window = payload.get("context_window", ())
        return cls(
            key=str(payload["key"]),
            checkpoint_name=str(payload["checkpoint_name"]),
            description=(
                str(payload["description"])
                if payload.get("description") is not None
                else None
            ),
            token_count=int(payload.get("token_count", 0)),
            saved_at_reset=int(payload.get("saved_at_reset", 0)),
            saved_at_cycle=int(payload.get("saved_at_cycle", 0)),
            context_window=tuple(context_window if isinstance(context_window, list) else ()),
        )


@dataclass(slots=True)
class AgentContextRuntimeState:
    """BaseAgent-owned durable state used by the generic context tools."""

    injected_sections: list[AgentInjectedSection] = field(default_factory=list)
    section_overrides: dict[str, str] = field(default_factory=dict)
    memory_fields: dict[str, Any] = field(default_factory=dict)
    memory_field_rules: dict[str, AgentContextMemoryUpdateRule] = field(
        default_factory=lambda: dict(DEFAULT_AGENT_CONTEXT_MEMORY_FIELD_RULES)
    )
    directives: list[AgentContextDirective] = field(default_factory=list)
    checkpoints: dict[str, AgentContextCheckpoint] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "checkpoints": {
                key: checkpoint.as_dict()
                for key, checkpoint in sorted(self.checkpoints.items())
            },
            "directives": [directive.as_dict() for directive in self.directives],
            "injected_sections": [section.as_dict() for section in self.injected_sections],
            "memory_field_rules": dict(self.memory_field_rules),
            "memory_fields": dict(self.memory_fields),
            "section_overrides": dict(self.section_overrides),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "AgentContextRuntimeState":
        raw_memory_field_rules = payload.get("memory_field_rules", {})
        raw_checkpoints = payload.get("checkpoints", {})
        return cls(
            injected_sections=[
                AgentInjectedSection.from_dict(item)
                for item in payload.get("injected_sections", ())
                if isinstance(item, dict)
            ],
            section_overrides={
                str(key): str(value)
                for key, value in dict(payload.get("section_overrides", {})).items()
            },
            memory_fields=dict(payload.get("memory_fields", {})),
            memory_field_rules={
                str(key): str(value)
                for key, value in (
                    dict(raw_memory_field_rules).items()
                    if isinstance(raw_memory_field_rules, dict)
                    else ()
                )
            } or dict(DEFAULT_AGENT_CONTEXT_MEMORY_FIELD_RULES),
            directives=[
                AgentContextDirective.from_dict(item)
                for item in payload.get("directives", ())
                if isinstance(item, dict)
            ],
            checkpoints={
                str(key): AgentContextCheckpoint.from_dict(value)
                for key, value in (
                    dict(raw_checkpoints).items()
                    if isinstance(raw_checkpoints, dict)
                    else ()
                )
                if isinstance(value, dict)
            },
        )

    def active_directives(self, reset_count: int) -> list[AgentContextDirective]:
        return [directive for directive in self.directives if directive.is_active(reset_count)]


@dataclass(frozen=True, slots=True)
class AgentModelRequest:
    """Normalized request handed to a provider-agnostic model adapter."""

    agent_name: str
    system_prompt: str
    parameter_sections: tuple[AgentParameterSection, ...]
    transcript: tuple[AgentTranscriptEntry, ...]
    tools: tuple[ToolDefinition, ...]

    def render_parameter_block(self) -> str:
        return "\n\n".join(section.render() for section in self.parameter_sections)

    def render_transcript(self) -> str:
        return "\n\n".join(entry.render() for entry in self.transcript)

    def estimated_tokens(self) -> int:
        """Estimate the full request size including tool metadata."""
        tool_payload = json.dumps([tool.as_dict() for tool in self.tools], sort_keys=True)
        segments = (
            self.system_prompt,
            self.render_parameter_block(),
            self.render_transcript(),
            tool_payload,
        )
        combined = "\n\n".join(segment for segment in segments if segment)
        return estimate_text_tokens(combined)


@dataclass(frozen=True, slots=True)
class AgentModelResponse:
    """A provider-independent model turn returned to the harness."""

    assistant_message: str
    tool_calls: tuple[ToolCall, ...] = ()
    should_continue: bool = True
    pause_reason: str | None = None


@dataclass(frozen=True, slots=True)
class AgentPauseSignal:
    """Structured signal returned by a tool when human intervention is required."""

    reason: str
    details: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class AgentRunResult:
    """Terminal outcome for one invocation of the agent loop."""

    status: AgentRunStatus
    cycles_completed: int
    resets: int
    pause_reason: str | None = None


class AgentModel(Protocol):
    """Provider-agnostic execution contract used by the base agent loop."""

    def generate_turn(self, request: AgentModelRequest) -> AgentModelResponse:
        """Return the next assistant turn for the provided context."""


class AgentToolExecutor(Protocol):
    """Small execution surface shared by tool registries and custom executors."""

    def definitions(self, tool_keys: Sequence[str] | None = None) -> list[ToolDefinition]:
        """Return canonical tool definitions for all or selected tools."""

    def execute(self, tool_key: str, arguments: dict[str, Any]) -> ToolResult:
        """Execute a tool and return a normalized result."""


__all__ = [
    "AgentContextCheckpoint",
    "AgentContextEntry",
    "AgentContextEntryKind",
    "AgentContextDirective",
    "AgentContextDirectivePriority",
    "AgentContextMemoryUpdateRule",
    "AgentContextRuntimeState",
    "AgentContextSectionPosition",
    "AgentContextWindow",
    "AgentInjectedSection",
    "AgentMessageRole",
    "AgentModel",
    "AgentModelRequest",
    "AgentModelResponse",
    "AgentParameterSection",
    "AgentPauseSignal",
    "AgentRunResult",
    "AgentRunStatus",
    "AgentRuntimeConfig",
    "AgentToolExecutor",
    "AgentTranscriptEntry",
    "AgentTranscriptEntryType",
    "DEFAULT_AGENT_MAX_TOKENS",
    "DEFAULT_AGENT_LANGSMITH_TRACING_ENABLED",
    "DEFAULT_AGENT_CONTEXT_MEMORY_FIELD_RULES",
    "DEFAULT_AGENT_PRUNE_PROGRESS_INTERVAL",
    "DEFAULT_AGENT_PRUNE_TOKEN_LIMIT",
    "DEFAULT_AGENT_RESET_THRESHOLD",
    "json_parameter_section",
    "merge_agent_runtime_config",
    "render_json_parameter_content",
    "estimate_text_tokens",
]
