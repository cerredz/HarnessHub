"""Shared DTOs for agent-layer boundaries."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any
import json

from harnessiq.shared.agents import DEFAULT_AGENT_MAX_TOKENS, DEFAULT_AGENT_RESET_THRESHOLD
from harnessiq.shared.dtos.base import SerializableDTO, coerce_serializable_mapping
from harnessiq.shared.tools import RegisteredTool

if TYPE_CHECKING:
    from harnessiq.providers.apollo import ApolloCredentials
    from harnessiq.providers.exa import ExaCredentials
    from harnessiq.providers.instantly import InstantlyCredentials
    from harnessiq.providers.outreach import OutreachCredentials
    from harnessiq.tools.resend import ResendCredentials


@dataclass(frozen=True, slots=True)
class AgentInstancePayload(Mapping[str, Any]):
    """Typed envelope for persisted agent instance payload data."""

    entries: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "entries", _normalize_payload(self.entries))

    def __getitem__(self, key: str) -> Any:
        return self.entries[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self.entries)

    def __len__(self) -> int:
        return len(self.entries)

    def to_dict(self) -> dict[str, Any]:
        """Return a detached JSON-safe mapping."""
        return dict(self.entries)

    @classmethod
    def from_dict(
        cls,
        payload: SerializableDTO | Mapping[str, Any] | None,
    ) -> "AgentInstancePayload":
        """Build a payload envelope from a DTO, mapping, or null input."""
        return cls(entries=coerce_serializable_mapping(payload))


@dataclass(frozen=True, slots=True)
class StatelessAgentInstancePayload(SerializableDTO):
    """Explicit DTO for agent families that persist no instance-specific state."""

    def to_dict(self) -> dict[str, Any]:
        return {}


@dataclass(frozen=True, slots=True)
class LinkedInAgentInstancePayload(SerializableDTO):
    """Explicit DTO for the LinkedIn durable-memory agent boundary."""

    runtime: Mapping[str, Any]
    memory_path: Path | None = None
    job_preferences: str | None = None
    user_profile: str | None = None
    agent_identity: str | None = None
    additional_prompt: str | None = None
    custom: Mapping[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"runtime": _normalize_value(self.runtime)}
        if self.memory_path is not None:
            payload["memory_path"] = self.memory_path.as_posix()
        if self.job_preferences is not None:
            payload["job_preferences"] = self.job_preferences
        if self.user_profile is not None:
            payload["user_profile"] = self.user_profile
        if self.agent_identity is not None:
            payload["agent_identity"] = self.agent_identity
        if self.additional_prompt is not None:
            payload["additional_prompt"] = self.additional_prompt
        if self.custom:
            payload["custom"] = _normalize_value(self.custom)
        return payload


@dataclass(frozen=True, slots=True)
class ExaOutreachAgentInstancePayload(SerializableDTO):
    """Explicit DTO for the ExaOutreach durable-memory agent boundary."""

    email_data: tuple[Mapping[str, Any], ...]
    search_query: str
    max_tokens: int
    reset_threshold: float
    allowed_resend_operations: tuple[str, ...] | None = None
    allowed_exa_operations: tuple[str, ...] | None = None
    memory_path: Path | None = None
    agent_identity: str | None = None
    additional_prompt: str | None = None
    query_config: Mapping[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "allowed_exa_operations": (
                list(self.allowed_exa_operations) if self.allowed_exa_operations is not None else None
            ),
            "allowed_resend_operations": (
                list(self.allowed_resend_operations) if self.allowed_resend_operations is not None else None
            ),
            "email_data": _normalize_value(self.email_data),
            "max_tokens": self.max_tokens,
            "reset_threshold": self.reset_threshold,
            "search_query": self.search_query,
        }
        if self.memory_path is not None:
            payload["memory_path"] = self.memory_path.as_posix()
        if self.agent_identity is not None:
            payload["agent_identity"] = self.agent_identity
        if self.additional_prompt is not None:
            payload["additional_prompt"] = self.additional_prompt
        if self.query_config:
            payload["query_config"] = _normalize_value(self.query_config)
        return payload


@dataclass(frozen=True, slots=True)
class KnowtAgentInstancePayload(SerializableDTO):
    """Explicit DTO for the Knowt durable-memory agent boundary."""

    memory_path: Path
    runtime: Mapping[str, Any]
    files: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "files": _normalize_value(self.files),
            "memory_path": self.memory_path.as_posix(),
            "runtime": _normalize_value(self.runtime),
        }


@dataclass(frozen=True, slots=True)
class InstagramAgentInstancePayload(SerializableDTO):
    """Explicit DTO for the Instagram durable-memory agent boundary."""

    icp_descriptions: tuple[str, ...]
    runtime: Mapping[str, Any]
    memory_path: Path | None = None
    custom_parameters: Mapping[str, Any] | None = None
    agent_identity: str | None = None
    additional_prompt: str | None = None
    run_state: Mapping[str, Any] | None = None
    icp_progress: tuple[Mapping[str, Any], ...] | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "icp_descriptions": list(self.icp_descriptions),
            "runtime": _normalize_value(self.runtime),
        }
        if self.memory_path is not None:
            payload["memory_path"] = self.memory_path.as_posix()
        if self.custom_parameters:
            payload["custom_parameters"] = _normalize_value(self.custom_parameters)
        if self.agent_identity is not None:
            payload["agent_identity"] = self.agent_identity
        if self.additional_prompt is not None:
            payload["additional_prompt"] = self.additional_prompt
        if self.run_state is not None:
            payload["run_state"] = _normalize_value(self.run_state)
        if self.icp_progress:
            payload["icp_progress"] = _normalize_value(self.icp_progress)
        return payload


@dataclass(frozen=True, slots=True)
class LeadsAgentInstancePayload(SerializableDTO):
    """Explicit DTO for the Leads durable-memory agent boundary."""

    memory_path: Path
    run_config: Mapping[str, Any]
    runtime: Mapping[str, Any]
    run_state: Mapping[str, Any] | None = None
    icp_progress: tuple[Mapping[str, Any], ...] | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "memory_path": self.memory_path.as_posix(),
            "run_config": _normalize_value(self.run_config),
            "runtime": _normalize_value(self.runtime),
        }
        if self.run_state is not None:
            payload["run_state"] = _normalize_value(self.run_state)
        if self.icp_progress:
            payload["icp_progress"] = _normalize_value(self.icp_progress)
        return payload


@dataclass(frozen=True, slots=True)
class ProspectingAgentInstancePayload(SerializableDTO):
    """Explicit DTO for the prospecting durable-memory agent boundary."""

    company_description: str
    runtime: Mapping[str, Any]
    custom: Mapping[str, Any]
    memory_path: Path | None = None
    agent_identity: str | None = None
    additional_prompt: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "company_description": self.company_description,
            "custom": _normalize_value(self.custom),
            "runtime": _normalize_value(self.runtime),
        }
        if self.memory_path is not None:
            payload["memory_path"] = self.memory_path.as_posix()
        if self.agent_identity is not None:
            payload["agent_identity"] = self.agent_identity
        if self.additional_prompt is not None:
            payload["additional_prompt"] = self.additional_prompt
        return payload


@dataclass(frozen=True, slots=True)
class ResearchSweepAgentInstancePayload(SerializableDTO):
    """Explicit DTO for the Research Sweep durable-memory agent boundary."""

    memory_path: Path
    config: Mapping[str, Any]
    runtime: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "config": _normalize_value(self.config),
            "memory_path": self.memory_path.as_posix(),
            "runtime": _normalize_value(self.runtime),
        }


@dataclass(frozen=True, slots=True)
class ProviderToolAgentRequest:
    """Typed request for the shared provider-backed agent scaffold."""

    provider_name: str
    provider_tools: tuple[RegisteredTool, ...]
    max_tokens: int = DEFAULT_AGENT_MAX_TOKENS
    reset_threshold: float = DEFAULT_AGENT_RESET_THRESHOLD

    def __post_init__(self) -> None:
        object.__setattr__(self, "provider_name", self.provider_name.strip())
        object.__setattr__(self, "provider_tools", tuple(self.provider_tools))


@dataclass(frozen=True, slots=True)
class ApolloAgentRequest:
    """Public DTO for constructing reusable Apollo-backed agents."""

    apollo_credentials: ApolloCredentials
    allowed_apollo_operations: tuple[str, ...] | None = None
    max_tokens: int = DEFAULT_AGENT_MAX_TOKENS
    reset_threshold: float = DEFAULT_AGENT_RESET_THRESHOLD

    def __post_init__(self) -> None:
        from harnessiq.shared.apollo import get_apollo_operation

        normalized_operations = _normalize_optional_operations(
            self.allowed_apollo_operations,
            validator=get_apollo_operation,
            field_name="allowed_apollo_operations",
        )
        object.__setattr__(self, "allowed_apollo_operations", normalized_operations)

    def to_config(self):
        from harnessiq.shared.apollo_agent import ApolloAgentConfig

        return ApolloAgentConfig(
            apollo_credentials=self.apollo_credentials,
            allowed_apollo_operations=self.allowed_apollo_operations,
            max_tokens=self.max_tokens,
            reset_threshold=self.reset_threshold,
        )


@dataclass(frozen=True, slots=True)
class ExaAgentRequest:
    """Public DTO for constructing reusable Exa-backed agents."""

    exa_credentials: ExaCredentials
    allowed_exa_operations: tuple[str, ...] | None = None
    max_tokens: int = DEFAULT_AGENT_MAX_TOKENS
    reset_threshold: float = DEFAULT_AGENT_RESET_THRESHOLD

    def __post_init__(self) -> None:
        from harnessiq.providers.exa import get_exa_operation

        normalized_operations = _normalize_optional_operations(
            self.allowed_exa_operations,
            validator=get_exa_operation,
            field_name="allowed_exa_operations",
        )
        object.__setattr__(self, "allowed_exa_operations", normalized_operations)

    def to_config(self):
        from harnessiq.shared.exa_agent import ExaAgentConfig

        return ExaAgentConfig(
            exa_credentials=self.exa_credentials,
            allowed_exa_operations=self.allowed_exa_operations,
            max_tokens=self.max_tokens,
            reset_threshold=self.reset_threshold,
        )


@dataclass(frozen=True, slots=True)
class EmailAgentRequest:
    """Public DTO for constructing reusable email-capable agents."""

    resend_credentials: ResendCredentials
    allowed_resend_operations: tuple[str, ...] | None = None
    max_tokens: int = DEFAULT_AGENT_MAX_TOKENS
    reset_threshold: float = DEFAULT_AGENT_RESET_THRESHOLD

    def __post_init__(self) -> None:
        from harnessiq.tools.resend import get_resend_operation

        normalized_operations = _normalize_optional_operations(
            self.allowed_resend_operations,
            validator=get_resend_operation,
            field_name="allowed_resend_operations",
        )
        object.__setattr__(self, "allowed_resend_operations", normalized_operations)

    def to_config(self):
        from harnessiq.shared.email import EmailAgentConfig

        return EmailAgentConfig(
            resend_credentials=self.resend_credentials,
            allowed_resend_operations=self.allowed_resend_operations,
            max_tokens=self.max_tokens,
            reset_threshold=self.reset_threshold,
        )


@dataclass(frozen=True, slots=True)
class InstantlyAgentRequest:
    """Public DTO for constructing reusable Instantly-backed agents."""

    instantly_credentials: InstantlyCredentials
    allowed_instantly_operations: tuple[str, ...] | None = None
    max_tokens: int = DEFAULT_AGENT_MAX_TOKENS
    reset_threshold: float = DEFAULT_AGENT_RESET_THRESHOLD

    def __post_init__(self) -> None:
        from harnessiq.providers.instantly import get_instantly_operation

        normalized_operations = _normalize_optional_operations(
            self.allowed_instantly_operations,
            validator=get_instantly_operation,
            field_name="allowed_instantly_operations",
        )
        object.__setattr__(self, "allowed_instantly_operations", normalized_operations)

    def to_config(self):
        from harnessiq.shared.instantly_agent import InstantlyAgentConfig

        return InstantlyAgentConfig(
            instantly_credentials=self.instantly_credentials,
            allowed_instantly_operations=self.allowed_instantly_operations,
            max_tokens=self.max_tokens,
            reset_threshold=self.reset_threshold,
        )


@dataclass(frozen=True, slots=True)
class OutreachAgentRequest:
    """Public DTO for constructing reusable Outreach-backed agents."""

    outreach_credentials: OutreachCredentials
    allowed_outreach_operations: tuple[str, ...] | None = None
    max_tokens: int = DEFAULT_AGENT_MAX_TOKENS
    reset_threshold: float = DEFAULT_AGENT_RESET_THRESHOLD

    def __post_init__(self) -> None:
        from harnessiq.providers.outreach import get_outreach_operation

        normalized_operations = _normalize_optional_operations(
            self.allowed_outreach_operations,
            validator=get_outreach_operation,
            field_name="allowed_outreach_operations",
        )
        object.__setattr__(self, "allowed_outreach_operations", normalized_operations)

    def to_config(self):
        from harnessiq.shared.outreach_agent import OutreachAgentConfig

        return OutreachAgentConfig(
            outreach_credentials=self.outreach_credentials,
            allowed_outreach_operations=self.allowed_outreach_operations,
            max_tokens=self.max_tokens,
            reset_threshold=self.reset_threshold,
        )


def _normalize_payload(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    if payload is None:
        return {}
    return {
        str(key): _normalize_value(value)
        for key, value in sorted(payload.items(), key=lambda item: str(item[0]))
    }


def _normalize_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, Mapping):
        return {
            str(key): _normalize_value(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (list, tuple)):
        return [_normalize_value(item) for item in value]
    if isinstance(value, set):
        normalized_items = [_normalize_value(item) for item in value]
        return sorted(
            normalized_items,
            key=lambda item: json.dumps(item, sort_keys=True, ensure_ascii=True),
        )
    return str(value)

def _normalize_optional_operations(
    operations: tuple[str, ...] | None,
    *,
    validator,
    field_name: str,
) -> tuple[str, ...] | None:
    if operations is None:
        return None
    normalized = tuple(operations)
    if not normalized:
        raise ValueError(f"{field_name} must not be empty when provided.")
    for operation_name in normalized:
        validator(operation_name)
    return normalized


__all__ = [
    "AgentInstancePayload",
    "ApolloAgentRequest",
    "EmailAgentRequest",
    "ExaOutreachAgentInstancePayload",
    "ExaAgentRequest",
    "InstagramAgentInstancePayload",
    "InstantlyAgentRequest",
    "KnowtAgentInstancePayload",
    "LeadsAgentInstancePayload",
    "LinkedInAgentInstancePayload",
    "OutreachAgentRequest",
    "ProspectingAgentInstancePayload",
    "ProviderToolAgentRequest",
    "ResearchSweepAgentInstancePayload",
    "StatelessAgentInstancePayload",
]
