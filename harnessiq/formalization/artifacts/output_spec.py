from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Literal

SupportedOutputFormat = Literal["markdown", "json", "csv", "jsonl", "text"]
CompletionRequirement = Literal["all", "specific", "none"]

_NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:_[a-z0-9]+)*$")
_SUPPORTED_OUTPUT_FORMATS = frozenset({"markdown", "json", "csv", "jsonl", "text"})


def _validate_artifact_name(name: str, *, spec_type: str) -> None:
    stripped = name.strip()
    if not stripped:
        raise ValueError(f"{spec_type} name must not be blank.")
    if len(stripped) > 64:
        raise ValueError(f"{spec_type} name '{stripped}' exceeds 64 characters.")
    if not _NAME_PATTERN.fullmatch(stripped):
        raise ValueError(
            f"{spec_type} name '{stripped}' must be snake_case with only lowercase letters, "
            "numbers, and underscores."
        )


def _validate_text_field(value: str, *, field_name: str, spec_type: str) -> None:
    if not value.strip():
        raise ValueError(f"{spec_type} {field_name} must not be blank.")


@dataclass(frozen=True, slots=True)
class OutputArtifactSpec:
    """Declaration of one output artifact the agent should produce."""

    name: str
    description: str
    file_format: SupportedOutputFormat = "markdown"
    path: str | Path | None = None
    write_tool_key: str | None = None
    contributes_write_tool: bool = True

    def __post_init__(self) -> None:
        _validate_artifact_name(self.name, spec_type="OutputArtifactSpec")
        _validate_text_field(self.description, field_name="description", spec_type="OutputArtifactSpec")
        if self.file_format not in _SUPPORTED_OUTPUT_FORMATS:
            raise ValueError(
                f"OutputArtifactSpec '{self.name}': unsupported format '{self.file_format}'."
            )
        if self.path is not None:
            _validate_text_field(str(self.path), field_name="path", spec_type="OutputArtifactSpec")
        if self.write_tool_key is not None:
            _validate_text_field(
                self.write_tool_key,
                field_name="write_tool_key",
                spec_type="OutputArtifactSpec",
            )


def validate_output_artifact_specs(
    specs: Sequence[OutputArtifactSpec],
) -> tuple[OutputArtifactSpec, ...]:
    """Return a validated spec tuple with unique artifact names."""
    validated = tuple(specs)
    seen: set[str] = set()
    for spec in validated:
        if spec.name in seen:
            raise ValueError(f"Duplicate OutputArtifactSpec name '{spec.name}'.")
        seen.add(spec.name)
    return validated


__all__ = [
    "CompletionRequirement",
    "OutputArtifactSpec",
    "SupportedOutputFormat",
    "validate_output_artifact_specs",
]
