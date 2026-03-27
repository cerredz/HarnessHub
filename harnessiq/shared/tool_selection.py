"""Shared runtime models for dynamic tool selection."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from harnessiq.shared.validated import NonEmptyString, PositiveInt

DEFAULT_TOOL_SELECTION_EMBEDDING_MODEL = "openai:text-embedding-3-small"

ToolSelectionRerankerMode = Literal["none", "auto", "always"]


def _normalize_string_tuple(values: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        candidate = str(value).strip()
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        normalized.append(candidate)
    return tuple(normalized)


@dataclass(frozen=True, slots=True)
class ToolProfile:
    """Retrieval metadata for one tool without changing the tool catalog itself."""

    key: str
    name: str
    family: str
    description: str
    requires_credentials: bool = False
    semantic_description: str = ""
    tags: tuple[str, ...] = ()
    when_to_use: str = ""
    limitations: str = ""
    always_on: bool = False
    retrievable: bool = True

    def __post_init__(self) -> None:
        normalized_key = str(NonEmptyString(self.key, field_name="tool profile key"))
        normalized_name = str(NonEmptyString(self.name, field_name="tool profile name"))
        normalized_family = str(NonEmptyString(self.family, field_name="tool profile family")).lower()
        normalized_description = str(
            NonEmptyString(self.description, field_name=f"tool profile description for {normalized_key}")
        )
        object.__setattr__(self, "key", normalized_key)
        object.__setattr__(self, "name", normalized_name)
        object.__setattr__(self, "family", normalized_family)
        object.__setattr__(self, "description", normalized_description)
        object.__setattr__(self, "tags", _normalize_string_tuple(tuple(self.tags)))
        object.__setattr__(self, "semantic_description", str(self.semantic_description).strip())
        object.__setattr__(self, "when_to_use", str(self.when_to_use).strip())
        object.__setattr__(self, "limitations", str(self.limitations).strip())


@dataclass(frozen=True, slots=True)
class ToolSelectionConfig:
    """Optional per-agent configuration for dynamic tool selection."""

    enabled: bool = False
    embedding_model: str | None = None
    top_k: int = 5
    candidate_tool_keys: tuple[str, ...] = ()
    mandatory_tools: tuple[str, ...] = ()
    min_similarity: float = 0.0
    reranker_mode: ToolSelectionRerankerMode = "none"
    expand_on_miss: bool = True
    debug_logging: bool = False

    def __post_init__(self) -> None:
        if self.top_k <= 0:
            raise ValueError("tool_selection.top_k must be greater than zero.")
        if not -1.0 <= float(self.min_similarity) <= 1.0:
            raise ValueError("tool_selection.min_similarity must be between -1.0 and 1.0.")
        if self.reranker_mode not in {"none", "auto", "always"}:
            raise ValueError("tool_selection.reranker_mode must be one of: none, auto, always.")
        object.__setattr__(self, "top_k", int(PositiveInt(int(self.top_k), field_name="tool_selection.top_k")))
        object.__setattr__(self, "candidate_tool_keys", _normalize_string_tuple(tuple(self.candidate_tool_keys)))
        object.__setattr__(self, "mandatory_tools", _normalize_string_tuple(tuple(self.mandatory_tools)))
        normalized_embedding_model = (
            str(self.embedding_model).strip()
            if isinstance(self.embedding_model, str)
            else None
        )
        object.__setattr__(self, "embedding_model", normalized_embedding_model or None)
        object.__setattr__(self, "min_similarity", float(self.min_similarity))


@dataclass(frozen=True, slots=True)
class ToolSelectionResult:
    """Structured output of one selector invocation."""

    selected_keys: tuple[str, ...]
    retrieval_query: str
    scored_tools: tuple[tuple[str, float], ...] = ()
    always_on_keys: tuple[str, ...] = ()
    mandatory_keys: tuple[str, ...] = ()
    rejected_keys: tuple[str, ...] = ()
    fallback_used: bool = False
    reranker_used: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "selected_keys", _normalize_string_tuple(tuple(self.selected_keys)))
        object.__setattr__(self, "always_on_keys", _normalize_string_tuple(tuple(self.always_on_keys)))
        object.__setattr__(self, "mandatory_keys", _normalize_string_tuple(tuple(self.mandatory_keys)))
        object.__setattr__(self, "rejected_keys", _normalize_string_tuple(tuple(self.rejected_keys)))
        normalized_scores: list[tuple[str, float]] = []
        for key, score in self.scored_tools:
            normalized_scores.append((str(NonEmptyString(key, field_name="scored tool key")), float(score)))
        object.__setattr__(self, "scored_tools", tuple(normalized_scores))
        object.__setattr__(self, "retrieval_query", str(self.retrieval_query).strip())


__all__ = [
    "DEFAULT_TOOL_SELECTION_EMBEDDING_MODEL",
    "ToolProfile",
    "ToolSelectionConfig",
    "ToolSelectionResult",
    "ToolSelectionRerankerMode",
]
