"""Typed declarative metadata for concrete Harnessiq harnesses."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Mapping

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

    def coerce(self, value: Any) -> Any:
        """Normalize one parameter value using the declared type contract."""
        if self.nullable and _is_empty_nullable(value):
            return None
        if self.value_type == "integer":
            coerced = _coerce_integer(value)
        elif self.value_type == "number":
            coerced = _coerce_number(value)
        elif self.value_type == "boolean":
            coerced = _coerce_boolean(value)
        else:
            coerced = _coerce_string(value)
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
        object.__setattr__(self, "runtime_parameters", tuple(self.runtime_parameters))
        object.__setattr__(self, "custom_parameters", tuple(self.custom_parameters))
        object.__setattr__(self, "memory_files", tuple(self.memory_files))
        object.__setattr__(self, "provider_families", tuple(self.provider_families))
        _validate_unique_keys(self.runtime_parameters, label="runtime parameter")
        _validate_unique_keys(self.custom_parameters, label="custom parameter")
        _validate_unique_keys(self.memory_files, label="memory file")

    @property
    def import_path(self) -> str:
        return f"{self.module_path}:{self.class_name}"

    @property
    def runtime_parameter_names(self) -> tuple[str, ...]:
        return tuple(spec.key for spec in self.runtime_parameters)

    @property
    def custom_parameter_names(self) -> tuple[str, ...]:
        return tuple(spec.key for spec in self.custom_parameters)

    def get_memory_file(self, key: str) -> HarnessMemoryFileSpec | None:
        normalized_key = key.strip()
        for entry in self.memory_files:
            if entry.key == normalized_key:
                return entry
        return None

    def coerce_runtime_parameters(self, parameters: Mapping[str, Any]) -> dict[str, Any]:
        return _coerce_parameters(
            parameters,
            specs=self.runtime_parameters,
            open_ended=self.runtime_parameters_open_ended,
            label=f"{self.display_name} runtime",
        )

    def coerce_custom_parameters(self, parameters: Mapping[str, Any]) -> dict[str, Any]:
        return _coerce_parameters(
            parameters,
            specs=self.custom_parameters,
            open_ended=self.custom_parameters_open_ended,
            label=f"{self.display_name} custom",
        )


def _coerce_parameters(
    parameters: Mapping[str, Any],
    *,
    specs: tuple[HarnessParameterSpec, ...],
    open_ended: bool,
    label: str,
) -> dict[str, Any]:
    if open_ended and not specs:
        return {str(key): value for key, value in parameters.items()}
    spec_index = {spec.key: spec for spec in specs}
    normalized: dict[str, Any] = {}
    for raw_key, value in parameters.items():
        key = str(raw_key).strip()
        spec = spec_index.get(key)
        if spec is None:
            if open_ended:
                normalized[key] = value
                continue
            supported = ", ".join(sorted(spec_index))
            raise ValueError(f"Unsupported {label} parameter '{key}'. Supported: {supported}.")
        normalized[key] = spec.coerce(value)
    return normalized


def _validate_unique_keys(items: tuple[Any, ...], *, label: str) -> None:
    seen: set[str] = set()
    for item in items:
        key = getattr(item, "key", "").strip()
        if key in seen:
            raise ValueError(f"Duplicate {label} key '{key}'.")
        seen.add(key)


def _is_empty_nullable(value: Any) -> bool:
    if value is None:
        return True
    return isinstance(value, str) and not value.strip()


def _coerce_integer(value: Any) -> int:
    if isinstance(value, bool):
        raise ValueError("Boolean values are not valid integer parameters.")
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip():
        return int(value)
    raise ValueError("Parameter must be an integer.")


def _coerce_number(value: Any) -> float:
    if isinstance(value, bool):
        raise ValueError("Boolean values are not valid numeric parameters.")
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str) and value.strip():
        return float(value)
    raise ValueError("Parameter must be a number.")


def _coerce_boolean(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "on"}:
            return True
        if normalized in {"false", "0", "no", "off"}:
            return False
    raise ValueError("Parameter must be a boolean.")


def _coerce_string(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Parameter must be a non-empty string.")
    return value


__all__ = [
    "HarnessManifest",
    "HarnessMemoryEntryFormat",
    "HarnessMemoryEntryKind",
    "HarnessMemoryFileSpec",
    "HarnessParameterSpec",
    "HarnessParameterType",
]
