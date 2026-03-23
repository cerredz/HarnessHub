"""Typed declarative metadata for concrete Harnessiq harnesses."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Mapping

from harnessiq.utils.harness_manifest.coercion import (
    coerce_boolean,
    coerce_integer,
    coerce_number,
    coerce_parameters,
    coerce_string,
    is_empty_nullable,
)
from harnessiq.utils.harness_manifest.validation import validate_unique_keys

HarnessParameterType = Literal["string", "integer", "number", "boolean"]
HarnessMemoryEntryKind = Literal["file", "directory"]
HarnessMemoryEntryFormat = Literal["text", "markdown", "json", "jsonl", "directory", "other"]


@dataclass(frozen=True, slots=True)
class HarnessParameterSpec:
    """Typed declaration for one runtime or custom harness parameter."""

    key: str
    value_type: HarnessParameterType
    description: str
    nullable: bool = False
    default: Any = None
    choices: tuple[Any, ...] = ()

    def __post_init__(self) -> None:
        normalized_key = self.key.strip()
        if not normalized_key:
            raise ValueError("HarnessParameterSpec.key must not be blank.")
        if not self.description.strip():
            raise ValueError("HarnessParameterSpec.description must not be blank.")
        object.__setattr__(self, "key", normalized_key)
        object.__setattr__(self, "choices", tuple(self.choices))
        if self.default is not None:
            self.coerce(self.default)

    def coerce(self, value: Any) -> Any:
        """Normalize one parameter value using the declared type contract."""
        if self.nullable and is_empty_nullable(value):
            return None
        if self.value_type == "integer":
            coerced = coerce_integer(value)
        elif self.value_type == "number":
            coerced = coerce_number(value)
        elif self.value_type == "boolean":
            coerced = coerce_boolean(value)
        else:
            coerced = coerce_string(value)
        if self.choices and coerced not in self.choices:
            allowed = ", ".join(repr(choice) for choice in self.choices)
            raise ValueError(f"Parameter '{self.key}' must be one of: {allowed}.")
        return coerced


@dataclass(frozen=True, slots=True)
class HarnessMemoryFileSpec:
    """Declarative description of one durable memory entry used by a harness."""

    key: str
    relative_path: str
    description: str
    kind: HarnessMemoryEntryKind = "file"
    format: HarnessMemoryEntryFormat = "other"

    def __post_init__(self) -> None:
        normalized_key = self.key.strip()
        normalized_path = self.relative_path.strip()
        if not normalized_key:
            raise ValueError("HarnessMemoryFileSpec.key must not be blank.")
        if not normalized_path:
            raise ValueError("HarnessMemoryFileSpec.relative_path must not be blank.")
        if not self.description.strip():
            raise ValueError("HarnessMemoryFileSpec.description must not be blank.")
        object.__setattr__(self, "key", normalized_key)
        object.__setattr__(self, "relative_path", normalized_path)


@dataclass(frozen=True, slots=True)
class HarnessManifest:
    """Declarative contract for one concrete harness."""

    manifest_id: str
    agent_name: str
    display_name: str
    module_path: str
    class_name: str
    cli_command: str | None = None
    cli_adapter_path: str | None = None
    default_memory_root: str | None = None
    prompt_path: str | None = None
    runtime_parameters: tuple[HarnessParameterSpec, ...] = ()
    custom_parameters: tuple[HarnessParameterSpec, ...] = ()
    runtime_parameters_open_ended: bool = False
    custom_parameters_open_ended: bool = False
    memory_files: tuple[HarnessMemoryFileSpec, ...] = ()
    provider_families: tuple[str, ...] = ()
    output_schema: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        manifest_id = self.manifest_id.strip()
        agent_name = self.agent_name.strip()
        display_name = self.display_name.strip()
        module_path = self.module_path.strip()
        class_name = self.class_name.strip()
        cli_adapter_path = self.cli_adapter_path.strip() if self.cli_adapter_path is not None else None
        default_memory_root = self.default_memory_root.strip() if self.default_memory_root is not None else None
        if not manifest_id:
            raise ValueError("HarnessManifest.manifest_id must not be blank.")
        if not agent_name:
            raise ValueError("HarnessManifest.agent_name must not be blank.")
        if not display_name:
            raise ValueError("HarnessManifest.display_name must not be blank.")
        if not module_path:
            raise ValueError("HarnessManifest.module_path must not be blank.")
        if not class_name:
            raise ValueError("HarnessManifest.class_name must not be blank.")
        object.__setattr__(self, "manifest_id", manifest_id)
        object.__setattr__(self, "agent_name", agent_name)
        object.__setattr__(self, "display_name", display_name)
        object.__setattr__(self, "module_path", module_path)
        object.__setattr__(self, "class_name", class_name)
        object.__setattr__(self, "cli_adapter_path", cli_adapter_path or None)
        object.__setattr__(self, "default_memory_root", default_memory_root or None)
        object.__setattr__(self, "runtime_parameters", tuple(self.runtime_parameters))
        object.__setattr__(self, "custom_parameters", tuple(self.custom_parameters))
        object.__setattr__(self, "memory_files", tuple(self.memory_files))
        object.__setattr__(self, "provider_families", tuple(self.provider_families))
        validate_unique_keys(self.runtime_parameters, label="runtime parameter")
        validate_unique_keys(self.custom_parameters, label="custom parameter")
        validate_unique_keys(self.memory_files, label="memory file")
        duplicate_keys = set(self.runtime_parameter_names).intersection(self.custom_parameter_names)
        if duplicate_keys:
            rendered = ", ".join(sorted(duplicate_keys))
            raise ValueError(f"Runtime and custom parameter keys must be unique across scopes: {rendered}.")

    @property
    def import_path(self) -> str:
        return f"{self.module_path}:{self.class_name}"

    @property
    def runtime_parameter_names(self) -> tuple[str, ...]:
        return tuple(spec.key for spec in self.runtime_parameters)

    @property
    def custom_parameter_names(self) -> tuple[str, ...]:
        return tuple(spec.key for spec in self.custom_parameters)

    @property
    def resolved_default_memory_root(self) -> str:
        if self.default_memory_root is not None:
            return self.default_memory_root
        suffix = self.cli_command or self.manifest_id
        return f"memory/{suffix}"

    def get_memory_file(self, key: str) -> HarnessMemoryFileSpec | None:
        """Look up one declared memory entry by key."""
        normalized_key = key.strip()
        for entry in self.memory_files:
            if entry.key == normalized_key:
                return entry
        return None

    def coerce_runtime_parameters(self, parameters: Mapping[str, Any]) -> dict[str, Any]:
        """Coerce runtime parameters using the manifest's declared runtime schema."""
        return coerce_parameters(
            parameters,
            specs=self.runtime_parameters,
            open_ended=self.runtime_parameters_open_ended,
            label=f"{self.display_name} runtime",
        )

    def coerce_custom_parameters(self, parameters: Mapping[str, Any]) -> dict[str, Any]:
        """Coerce custom parameters using the manifest's declared custom schema."""
        return coerce_parameters(
            parameters,
            specs=self.custom_parameters,
            open_ended=self.custom_parameters_open_ended,
            label=f"{self.display_name} custom",
        )

    def default_runtime_parameters(self) -> dict[str, Any]:
        """Return runtime defaults declared directly on the manifest."""
        return {
            spec.key: spec.default
            for spec in self.runtime_parameters
            if spec.default is not None
        }

    def default_custom_parameters(self) -> dict[str, Any]:
        """Return custom defaults declared directly on the manifest."""
        return {
            spec.key: spec.default
            for spec in self.custom_parameters
            if spec.default is not None
        }

    def resolve_runtime_parameters(self, parameters: Mapping[str, Any]) -> dict[str, Any]:
        """Merge runtime defaults with explicitly provided runtime parameter values."""
        resolved = self.default_runtime_parameters()
        resolved.update(self.coerce_runtime_parameters(parameters))
        return resolved

    def resolve_custom_parameters(self, parameters: Mapping[str, Any]) -> dict[str, Any]:
        """Merge custom defaults with explicitly provided custom parameter values."""
        resolved = self.default_custom_parameters()
        resolved.update(self.coerce_custom_parameters(parameters))
        return resolved


__all__ = [
    "HarnessManifest",
    "HarnessMemoryEntryFormat",
    "HarnessMemoryEntryKind",
    "HarnessMemoryFileSpec",
    "HarnessParameterSpec",
    "HarnessParameterType",
]
