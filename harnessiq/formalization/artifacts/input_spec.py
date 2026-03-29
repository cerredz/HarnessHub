from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Literal

OnOversize = Literal["truncate", "skip", "header_only"]
SupportedInputFormat = Literal["text", "markdown", "json", "jsonl", "csv"]

_NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:_[a-z0-9]+)*$")

_FORMAT_SECTION_LABEL: dict[str, str] = {
    "text": "plain text",
    "markdown": "Markdown",
    "json": "JSON",
    "jsonl": "JSONL (newline-delimited JSON)",
    "csv": "CSV",
}


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
class InjectionPolicy:
    """Controls how one input artifact's content is injected per reset."""

    max_chars: int | None = 100_000
    on_oversize: OnOversize = "truncate"
    refresh_on_reset: bool = True
    custom_filter: Callable[[str, int], bool] | None = None
    section_title_template: str = "Input: {name}"
    include_path_in_section: bool = True

    def __post_init__(self) -> None:
        if self.max_chars is not None and self.max_chars < 0:
            raise ValueError("InjectionPolicy max_chars must be greater than or equal to zero.")
        if self.on_oversize not in {"truncate", "skip", "header_only"}:
            raise ValueError(f"Unsupported on_oversize mode '{self.on_oversize}'.")
        if not self.section_title_template.strip():
            raise ValueError("InjectionPolicy section_title_template must not be blank.")
        if self.custom_filter is not None and not callable(self.custom_filter):
            raise ValueError("InjectionPolicy custom_filter must be callable when provided.")


@dataclass(frozen=True, slots=True)
class InputArtifactSpec:
    """Declaration of one input artifact injected into the context window."""

    name: str
    path: str | Path
    description: str
    file_format: SupportedInputFormat = "text"
    required: bool = True
    injection_policy: InjectionPolicy = field(default_factory=InjectionPolicy)

    def __post_init__(self) -> None:
        _validate_artifact_name(self.name, spec_type="InputArtifactSpec")
        _validate_text_field(str(self.path), field_name="path", spec_type="InputArtifactSpec")
        _validate_text_field(self.description, field_name="description", spec_type="InputArtifactSpec")
        if self.file_format not in _FORMAT_SECTION_LABEL:
            raise ValueError(
                f"InputArtifactSpec '{self.name}': unsupported format '{self.file_format}'."
            )


def validate_input_artifact_specs(
    specs: Sequence[InputArtifactSpec],
) -> tuple[InputArtifactSpec, ...]:
    """Return a validated spec tuple with unique artifact names."""
    validated = tuple(specs)
    seen: set[str] = set()
    for spec in validated:
        if spec.name in seen:
            raise ValueError(f"Duplicate InputArtifactSpec name '{spec.name}'.")
        seen.add(spec.name)
    return validated


__all__ = [
    "InjectionPolicy",
    "InputArtifactSpec",
    "OnOversize",
    "SupportedInputFormat",
    "_FORMAT_SECTION_LABEL",
    "validate_input_artifact_specs",
]
