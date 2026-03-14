"""Credential config models and repo-local ``.env`` resolution helpers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

DEFAULT_CONFIG_DIRNAME = ".harnessiq"
DEFAULT_CREDENTIALS_CONFIG_FILENAME = "credentials.json"
DEFAULT_ENV_FILENAME = ".env"


class CredentialsConfigError(Exception):
    """Base error for credential config failures."""


class AgentCredentialsNotConfiguredError(CredentialsConfigError):
    """Raised when no binding exists for the requested agent."""


class DotEnvFileNotFoundError(CredentialsConfigError):
    """Raised when the repo-local ``.env`` file is missing."""


class MissingEnvironmentVariableError(CredentialsConfigError):
    """Raised when a required environment variable is not present in ``.env``."""


@dataclass(frozen=True, slots=True)
class CredentialEnvReference:
    """Map one agent credential field to a repo-local environment variable."""

    field_name: str
    env_var: str

    def __post_init__(self) -> None:
        if not self.field_name.strip():
            raise ValueError("field_name must not be blank.")
        if not self.env_var.strip():
            raise ValueError("env_var must not be blank.")

    def as_dict(self) -> dict[str, str]:
        return {
            "env_var": self.env_var,
            "field_name": self.field_name,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> "CredentialEnvReference":
        return cls(
            field_name=str(payload["field_name"]),
            env_var=str(payload["env_var"]),
        )


@dataclass(frozen=True, slots=True)
class AgentCredentialBinding:
    """Persisted credential binding for one logical agent."""

    agent_name: str
    references: tuple[CredentialEnvReference, ...]
    description: str | None = None

    def __post_init__(self) -> None:
        normalized_name = self.agent_name.strip()
        if not normalized_name:
            raise ValueError("agent_name must not be blank.")
        object.__setattr__(self, "agent_name", normalized_name)
        references = tuple(self.references)
        if not references:
            raise ValueError("references must contain at least one credential binding.")

        unique_fields: set[str] = set()
        normalized_references: list[CredentialEnvReference] = []
        for reference in references:
            if not isinstance(reference, CredentialEnvReference):
                raise TypeError("references must contain CredentialEnvReference instances.")
            if reference.field_name in unique_fields:
                raise ValueError(f"Duplicate credential field '{reference.field_name}' for agent '{self.agent_name}'.")
            unique_fields.add(reference.field_name)
            normalized_references.append(reference)
        object.__setattr__(self, "references", tuple(normalized_references))

        if self.description is not None:
            normalized_description = self.description.strip()
            object.__setattr__(self, "description", normalized_description or None)

    def required_env_vars(self) -> tuple[str, ...]:
        return tuple(reference.env_var for reference in self.references)

    def as_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "agent_name": self.agent_name,
            "references": [reference.as_dict() for reference in self.references],
        }
        if self.description is not None:
            payload["description"] = self.description
        return payload

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> "AgentCredentialBinding":
        references_payload = payload.get("references")
        if not isinstance(references_payload, list):
            raise ValueError("Agent credential bindings must define a list of references.")
        return cls(
            agent_name=str(payload["agent_name"]),
            references=tuple(CredentialEnvReference.from_dict(item) for item in references_payload),
            description=str(payload["description"]) if payload.get("description") is not None else None,
        )


@dataclass(frozen=True, slots=True)
class CredentialsConfig:
    """Persisted set of all agent credential bindings."""

    bindings: tuple[AgentCredentialBinding, ...] = ()

    def __post_init__(self) -> None:
        bindings = tuple(self.bindings)
        unique_agents: set[str] = set()
        normalized_bindings: list[AgentCredentialBinding] = []
        for binding in bindings:
            if not isinstance(binding, AgentCredentialBinding):
                raise TypeError("bindings must contain AgentCredentialBinding instances.")
            if binding.agent_name in unique_agents:
                raise ValueError(f"Duplicate credential binding for agent '{binding.agent_name}'.")
            unique_agents.add(binding.agent_name)
            normalized_bindings.append(binding)
        object.__setattr__(self, "bindings", tuple(normalized_bindings))

    def binding_for(self, agent_name: str) -> AgentCredentialBinding:
        normalized_name = agent_name.strip()
        for binding in self.bindings:
            if binding.agent_name == normalized_name:
                return binding
        raise AgentCredentialsNotConfiguredError(f"No credential binding exists for agent '{agent_name}'.")

    def upsert(self, binding: AgentCredentialBinding) -> "CredentialsConfig":
        updated = {item.agent_name: item for item in self.bindings}
        updated[binding.agent_name] = binding
        ordered = tuple(updated[name] for name in sorted(updated))
        return CredentialsConfig(bindings=ordered)

    def as_dict(self) -> dict[str, object]:
        return {"bindings": [binding.as_dict() for binding in self.bindings]}

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> "CredentialsConfig":
        bindings_payload = payload.get("bindings", [])
        if not isinstance(bindings_payload, list):
            raise ValueError("Credentials config payload must define 'bindings' as a list.")
        return cls(bindings=tuple(AgentCredentialBinding.from_dict(item) for item in bindings_payload))


@dataclass(frozen=True, slots=True)
class ResolvedAgentCredentials:
    """Concrete key/value credentials resolved from the repo-local ``.env`` file."""

    agent_name: str
    values: dict[str, str]
    env_path: Path

    def __post_init__(self) -> None:
        object.__setattr__(self, "env_path", Path(self.env_path))
        object.__setattr__(self, "values", dict(self.values))

    def require(self, field_name: str) -> str:
        if field_name not in self.values:
            raise KeyError(f"Credential field '{field_name}' was not resolved for agent '{self.agent_name}'.")
        return self.values[field_name]

    def as_dict(self) -> dict[str, str]:
        return dict(self.values)


@dataclass(slots=True)
class CredentialsConfigStore:
    """Persist and resolve agent credential bindings within one repo root."""

    repo_root: Path | str = "."

    def __post_init__(self) -> None:
        self.repo_root = Path(self.repo_root).expanduser().resolve()

    @property
    def config_dir(self) -> Path:
        return self.repo_root / DEFAULT_CONFIG_DIRNAME

    @property
    def config_path(self) -> Path:
        return self.config_dir / DEFAULT_CREDENTIALS_CONFIG_FILENAME

    @property
    def env_path(self) -> Path:
        return self.repo_root / DEFAULT_ENV_FILENAME

    def load(self) -> CredentialsConfig:
        if not self.config_path.exists():
            return CredentialsConfig()
        raw = self.config_path.read_text(encoding="utf-8").strip()
        if not raw:
            return CredentialsConfig()

        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise ValueError("Credential config file must contain a JSON object.")
        return CredentialsConfig.from_dict(payload)

    def save(self, config: CredentialsConfig) -> Path:
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(json.dumps(config.as_dict(), indent=2, sort_keys=True), encoding="utf-8")
        return self.config_path

    def upsert(self, binding: AgentCredentialBinding) -> Path:
        config = self.load().upsert(binding)
        return self.save(config)

    def resolve_agent(self, agent_name: str) -> ResolvedAgentCredentials:
        binding = self.load().binding_for(agent_name)
        return self.resolve_binding(binding)

    def resolve_binding(self, binding: AgentCredentialBinding) -> ResolvedAgentCredentials:
        env_values = parse_dotenv_file(self.env_path)
        resolved: dict[str, str] = {}
        for reference in binding.references:
            value = env_values.get(reference.env_var)
            if value is None:
                raise MissingEnvironmentVariableError(
                    f"Agent '{binding.agent_name}' requires env var '{reference.env_var}' for field '{reference.field_name}'."
                )
            resolved[reference.field_name] = value
        return ResolvedAgentCredentials(
            agent_name=binding.agent_name,
            values=resolved,
            env_path=self.env_path,
        )


def parse_dotenv_file(path: Path | str) -> dict[str, str]:
    """Parse a simple repo-local ``.env`` file into a string mapping."""

    env_path = Path(path)
    if not env_path.exists() or not env_path.is_file():
        raise DotEnvFileNotFoundError(f"Required env file '{env_path}' does not exist or is not a file.")

    parsed: dict[str, str] = {}
    for line_number, raw_line in enumerate(env_path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        key, separator, value = line.partition("=")
        if not separator:
            raise ValueError(f"Invalid .env assignment on line {line_number}: '{raw_line}'.")
        normalized_key = key.strip()
        if not normalized_key:
            raise ValueError(f"Invalid blank env key on line {line_number}.")
        parsed[normalized_key] = _normalize_env_value(value.strip())
    return parsed


def _normalize_env_value(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        inner = value[1:-1]
        if value[0] == '"':
            return (
                inner.replace("\\n", "\n")
                .replace("\\r", "\r")
                .replace("\\t", "\t")
                .replace('\\"', '"')
                .replace("\\\\", "\\")
            )
        return inner
    return _strip_unquoted_comment(value)


def _strip_unquoted_comment(value: str) -> str:
    comment_index = value.find(" #")
    if comment_index >= 0:
        return value[:comment_index].rstrip()
    return value


__all__ = [
    "AgentCredentialBinding",
    "AgentCredentialsNotConfiguredError",
    "CredentialEnvReference",
    "CredentialsConfig",
    "CredentialsConfigError",
    "CredentialsConfigStore",
    "DEFAULT_CONFIG_DIRNAME",
    "DEFAULT_CREDENTIALS_CONFIG_FILENAME",
    "DEFAULT_ENV_FILENAME",
    "DotEnvFileNotFoundError",
    "MissingEnvironmentVariableError",
    "ResolvedAgentCredentials",
    "parse_dotenv_file",
]
