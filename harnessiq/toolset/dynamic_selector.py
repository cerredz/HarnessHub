"""Dynamic tool-profile resolution and default selector implementations."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Mapping, Sequence

from harnessiq.interfaces.tool_selection import EmbeddingBackend
from harnessiq.shared.agents import AgentContextWindow
from harnessiq.shared.tool_selection import (
    ToolProfile,
    ToolSelectionConfig,
    ToolSelectionResult,
)
from harnessiq.shared.tools import (
    CONTEXT_COMPACTION_TOOL_KEYS,
    HEAVY_COMPACTION,
    LOG_COMPACTION,
    REMOVE_TOOL_RESULTS,
    REMOVE_TOOLS,
    RegisteredTool,
    ToolDefinition,
)
from harnessiq.toolset.catalog import PROVIDER_ENTRY_INDEX, ToolEntry
from harnessiq.toolset.registry import ToolsetRegistry

_DEFAULT_ALWAYS_ON_KEYS = frozenset(
    {
        REMOVE_TOOL_RESULTS,
        REMOVE_TOOLS,
        HEAVY_COMPACTION,
        LOG_COMPACTION,
        *CONTEXT_COMPACTION_TOOL_KEYS,
    }
)


@dataclass(frozen=True, slots=True)
class ToolProfileOverride:
    """Optional retrieval-only overrides layered on top of existing tool metadata."""

    semantic_description: str | None = None
    tags: tuple[str, ...] = ()
    when_to_use: str | None = None
    limitations: str | None = None
    always_on: bool | None = None
    retrievable: bool | None = None

    def __post_init__(self) -> None:
        normalized_tags: list[str] = []
        seen_tags: set[str] = set()
        for value in self.tags:
            candidate = str(value).strip()
            if not candidate or candidate in seen_tags:
                continue
            seen_tags.add(candidate)
            normalized_tags.append(candidate)
        object.__setattr__(self, "tags", tuple(normalized_tags))
        object.__setattr__(
            self,
            "semantic_description",
            str(self.semantic_description).strip() if self.semantic_description is not None else None,
        )
        object.__setattr__(
            self,
            "when_to_use",
            str(self.when_to_use).strip() if self.when_to_use is not None else None,
        )
        object.__setattr__(
            self,
            "limitations",
            str(self.limitations).strip() if self.limitations is not None else None,
        )


def resolve_tool_profiles(
    tools: Sequence[RegisteredTool],
    *,
    catalog_entries: Mapping[str, ToolEntry] | Sequence[ToolEntry] | None = None,
    profile_overrides: Mapping[str, ToolProfileOverride] | None = None,
    always_on_keys: Sequence[str] = (),
) -> tuple[ToolProfile, ...]:
    """Derive retrieval profiles for a concrete ordered tool set."""
    entry_index = _build_catalog_entry_index(catalog_entries)
    override_index = dict(profile_overrides or {})
    forced_always_on = {str(key).strip() for key in always_on_keys if str(key).strip()}
    profiles: list[ToolProfile] = []
    for tool in tools:
        catalog_entry = entry_index.get(tool.key)
        override = override_index.get(tool.key)
        profiles.append(
            _build_tool_profile(
                tool,
                catalog_entry=catalog_entry,
                override=override,
                forced_always_on=forced_always_on,
            )
        )
    return tuple(profiles)


def resolve_tool_definition_profiles(
    definitions: Sequence[ToolDefinition],
    *,
    catalog_entries: Mapping[str, ToolEntry] | Sequence[ToolEntry] | None = None,
    profile_overrides: Mapping[str, ToolProfileOverride] | None = None,
    always_on_keys: Sequence[str] = (),
) -> tuple[ToolProfile, ...]:
    """Derive retrieval profiles from tool definitions without executable handlers."""
    synthetic_tools = tuple(
        RegisteredTool(definition=definition, handler=_unreachable_handler)
        for definition in definitions
    )
    return resolve_tool_profiles(
        synthetic_tools,
        catalog_entries=catalog_entries,
        profile_overrides=profile_overrides,
        always_on_keys=always_on_keys,
    )


def resolve_registry_tool_profiles(
    registry: ToolsetRegistry,
    tool_keys: Sequence[str],
    *,
    credentials: object = None,
    profile_overrides: Mapping[str, ToolProfileOverride] | None = None,
    always_on_keys: Sequence[str] = (),
) -> tuple[ToolProfile, ...]:
    """Resolve profiles for ordered keys from a ``ToolsetRegistry`` instance."""
    tools = tuple(registry.get(key, credentials=credentials) for key in tool_keys)
    return resolve_tool_profiles(
        tools,
        profile_overrides=profile_overrides,
        always_on_keys=always_on_keys,
    )


class DefaultDynamicToolSelector:
    """Deterministic cosine-similarity selector backed by an embedding backend."""

    def __init__(
        self,
        *,
        config: ToolSelectionConfig,
        embedding_backend: EmbeddingBackend,
    ) -> None:
        self._config = config
        self._embedding_backend = embedding_backend
        self._profile_by_key: dict[str, ToolProfile] = {}
        self._embedding_by_key: dict[str, tuple[float, ...]] = {}
        self._indexed_signature_by_key: dict[str, str] = {}

    @property
    def config(self) -> ToolSelectionConfig:
        return self._config

    def index(self, profiles: Sequence[ToolProfile]) -> None:
        deduplicated_profiles = _deduplicate_profiles(profiles)
        pending_profiles: list[ToolProfile] = []
        pending_payloads: list[str] = []
        for profile in deduplicated_profiles:
            self._profile_by_key[profile.key] = profile
            if not profile.retrievable:
                continue
            signature = _profile_embedding_payload(profile)
            if self._indexed_signature_by_key.get(profile.key) == signature:
                continue
            pending_profiles.append(profile)
            pending_payloads.append(signature)
        if not pending_profiles:
            return
        embeddings = self._embedding_backend.embed_texts(tuple(pending_payloads))
        if len(embeddings) != len(pending_profiles):
            raise ValueError("Embedding backend returned a vector count that did not match the indexed profiles.")
        for profile, signature, embedding in zip(pending_profiles, pending_payloads, embeddings):
            self._embedding_by_key[profile.key] = tuple(float(value) for value in embedding)
            self._indexed_signature_by_key[profile.key] = signature

    def select(
        self,
        *,
        context_window: AgentContextWindow,
        candidate_profiles: Sequence[ToolProfile],
        metadata: Mapping[str, object] | None = None,
    ) -> ToolSelectionResult:
        deduplicated_candidates = _deduplicate_profiles(candidate_profiles)
        if self._config.candidate_tool_keys:
            allowed_keys = set(self._config.candidate_tool_keys)
            deduplicated_candidates = tuple(
                profile for profile in deduplicated_candidates if profile.key in allowed_keys
            )

        self.index(deduplicated_candidates)
        query = build_tool_selection_query(context_window, metadata=metadata)
        if not deduplicated_candidates:
            return ToolSelectionResult(selected_keys=(), retrieval_query=query)

        query_embedding = self._embedding_backend.embed_texts((query,))
        if len(query_embedding) != 1:
            raise ValueError("Embedding backend must return exactly one vector for the selection query.")
        query_vector = tuple(float(value) for value in query_embedding[0])

        candidate_key_order = tuple(profile.key for profile in deduplicated_candidates)
        candidate_order_index = {key: index for index, key in enumerate(candidate_key_order)}
        always_on_keys = tuple(profile.key for profile in deduplicated_candidates if profile.always_on)
        mandatory_lookup = set(self._config.mandatory_tools)
        mandatory_keys = tuple(
            profile.key
            for profile in deduplicated_candidates
            if profile.key in mandatory_lookup
        )

        scored_entries: list[tuple[str, float]] = []
        for profile in deduplicated_candidates:
            if not profile.retrievable:
                continue
            vector = self._embedding_by_key.get(profile.key)
            if vector is None:
                continue
            scored_entries.append((profile.key, _cosine_similarity(query_vector, vector)))

        scored_entries.sort(key=lambda item: (-item[1], candidate_order_index[item[0]]))

        above_threshold = [
            item
            for item in scored_entries
            if item[1] >= self._config.min_similarity
        ]
        retrieved_keys = [key for key, _ in above_threshold[: self._config.top_k]]
        fallback_used = False
        if self._config.expand_on_miss and len(retrieved_keys) < min(self._config.top_k, len(scored_entries)):
            fallback_used = True
            for key, _ in scored_entries:
                if key in retrieved_keys:
                    continue
                retrieved_keys.append(key)
                if len(retrieved_keys) >= self._config.top_k:
                    break

        selected_keys = _merge_unique_keys(retrieved_keys, always_on_keys, mandatory_keys)
        selected_key_lookup = set(selected_keys)
        rejected_keys = tuple(key for key in candidate_key_order if key not in selected_key_lookup)

        result = ToolSelectionResult(
            selected_keys=selected_keys,
            retrieval_query=query,
            scored_tools=tuple(scored_entries),
            always_on_keys=always_on_keys,
            mandatory_keys=mandatory_keys,
            rejected_keys=rejected_keys,
            fallback_used=fallback_used,
            reranker_used=False,
        )
        candidate_key_set = set(candidate_key_order)
        if not set(result.selected_keys).issubset(candidate_key_set):
            raise AssertionError("Selector returned keys outside the candidate ceiling.")
        return result


def build_tool_selection_query(
    context_window: AgentContextWindow,
    *,
    metadata: Mapping[str, object] | None = None,
) -> str:
    """Render a deterministic retrieval query from the current context window."""
    explicit_query = _extract_explicit_query(metadata)
    if explicit_query is not None:
        return explicit_query

    segments: list[str] = []
    for entry in context_window:
        kind = str(entry.get("kind", "")).strip().lower()
        if not kind:
            continue
        content = _render_context_entry(entry)
        if not content:
            continue
        segments.append(f"{kind}: {content}")
    if metadata:
        rendered_metadata = _render_metadata(metadata)
        if rendered_metadata:
            segments.append(f"metadata: {rendered_metadata}")
    return "\n".join(segments).strip()


def _build_tool_profile(
    tool: RegisteredTool,
    *,
    catalog_entry: ToolEntry | None,
    override: ToolProfileOverride | None,
    forced_always_on: set[str],
) -> ToolProfile:
    definition = tool.definition
    family = catalog_entry.family if catalog_entry is not None else _family_of(definition.key)
    requires_credentials = (
        catalog_entry.requires_credentials
        if catalog_entry is not None
        else False
    )
    semantic_description = (
        override.semantic_description
        if override is not None and override.semantic_description is not None
        else _derive_semantic_description(definition, requires_credentials=requires_credentials)
    )
    when_to_use = (
        override.when_to_use
        if override is not None and override.when_to_use is not None
        else _derive_when_to_use(definition)
    )
    limitations = (
        override.limitations
        if override is not None and override.limitations is not None
        else _derive_limitations(definition, requires_credentials=requires_credentials)
    )
    tags = override.tags if override is not None and override.tags else _derive_tags(definition, family=family)
    always_on = definition.key in forced_always_on or definition.key in _DEFAULT_ALWAYS_ON_KEYS
    if override is not None and override.always_on is not None:
        always_on = override.always_on
    retrievable = True
    if override is not None and override.retrievable is not None:
        retrievable = override.retrievable
    return ToolProfile(
        key=definition.key,
        name=definition.name,
        family=family,
        description=definition.description,
        requires_credentials=requires_credentials,
        semantic_description=semantic_description,
        tags=tags,
        when_to_use=when_to_use,
        limitations=limitations,
        always_on=always_on,
        retrievable=retrievable,
    )


def _build_catalog_entry_index(
    catalog_entries: Mapping[str, ToolEntry] | Sequence[ToolEntry] | None,
) -> dict[str, ToolEntry]:
    entry_index = dict(PROVIDER_ENTRY_INDEX)
    if catalog_entries is None:
        return entry_index
    if isinstance(catalog_entries, Mapping):
        entry_index.update({str(key): value for key, value in catalog_entries.items()})
        return entry_index
    for entry in catalog_entries:
        entry_index[entry.key] = entry
    return entry_index


def _derive_semantic_description(
    definition: ToolDefinition,
    *,
    requires_credentials: bool,
) -> str:
    properties = definition.inspect().get("parameters", [])
    parameter_names = [
        str(parameter.get("name")).strip()
        for parameter in properties
        if str(parameter.get("name", "")).strip()
    ]
    segments = [definition.description]
    if parameter_names:
        segments.append(f"Accepted parameters: {', '.join(parameter_names)}.")
    if requires_credentials:
        segments.append("This tool requires configured external provider credentials.")
    return " ".join(segment for segment in segments if segment).strip()


def _derive_when_to_use(definition: ToolDefinition) -> str:
    action = definition.description.rstrip(".")
    return (
        f"Use when the agent needs to {action[0].lower() + action[1:] if action else 'complete this task'}."
    )


def _derive_limitations(
    definition: ToolDefinition,
    *,
    requires_credentials: bool,
) -> str:
    segments = ["Only arguments defined in the tool schema are accepted."]
    if requires_credentials:
        segments.append("This tool cannot run until the required provider credentials are configured.")
    return " ".join(segments)


def _derive_tags(definition: ToolDefinition, *, family: str) -> tuple[str, ...]:
    tags: list[str] = [family]
    for part in definition.key.replace(".", "_").split("_"):
        if part and part not in tags:
            tags.append(part)
    parameters = definition.inspect().get("parameters", [])
    for parameter in parameters:
        name = str(parameter.get("name", "")).strip().replace(" ", "_")
        if name and name not in tags:
            tags.append(name)
    return tuple(tags)


def _profile_embedding_payload(profile: ToolProfile) -> str:
    segments = [profile.name, profile.description, profile.semantic_description]
    if profile.tags:
        segments.append("tags: " + ", ".join(profile.tags))
    if profile.when_to_use:
        segments.append("when_to_use: " + profile.when_to_use)
    return "\n".join(segment for segment in segments if segment).strip()


def _deduplicate_profiles(profiles: Sequence[ToolProfile]) -> tuple[ToolProfile, ...]:
    deduplicated: list[ToolProfile] = []
    seen: set[str] = set()
    for profile in profiles:
        if profile.key in seen:
            continue
        seen.add(profile.key)
        deduplicated.append(profile)
    return tuple(deduplicated)


def _extract_explicit_query(metadata: Mapping[str, object] | None) -> str | None:
    if metadata is None:
        return None
    for key in ("query", "context_signal"):
        value = metadata.get(key)
        if isinstance(value, str):
            candidate = value.strip()
            if candidate:
                return candidate
    return None


def _render_context_entry(entry: Mapping[str, object]) -> str:
    content = str(entry.get("content", "")).strip()
    if content:
        return content
    if "output" in entry:
        output = entry.get("output")
        if isinstance(output, str):
            return output.strip()
        if output is not None:
            return json.dumps(output, sort_keys=True, default=str)
    if "arguments" in entry:
        arguments = entry.get("arguments")
        if isinstance(arguments, Mapping):
            return json.dumps(arguments, sort_keys=True, default=str)
    label = str(entry.get("label", "")).strip()
    tool_key = str(entry.get("tool_key", "")).strip()
    return " ".join(part for part in (label, tool_key) if part).strip()


def _render_metadata(metadata: Mapping[str, object]) -> str:
    serialized: dict[str, object] = {}
    for key in sorted(metadata):
        if key in {"query", "context_signal"}:
            continue
        value = metadata[key]
        if value is None:
            continue
        serialized[str(key)] = value
    if not serialized:
        return ""
    return json.dumps(serialized, sort_keys=True, default=str)


def _family_of(tool_key: str) -> str:
    return str(tool_key).split(".", 1)[0].strip().lower()


def _merge_unique_keys(*groups: Sequence[str]) -> tuple[str, ...]:
    merged: list[str] = []
    seen: set[str] = set()
    for group in groups:
        for key in group:
            candidate = str(key).strip()
            if not candidate or candidate in seen:
                continue
            seen.add(candidate)
            merged.append(candidate)
    return tuple(merged)


def _cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right):
        raise ValueError("Embedding vectors must share the same dimensionality.")
    numerator = sum(float(a) * float(b) for a, b in zip(left, right))
    left_norm = math.sqrt(sum(float(value) * float(value) for value in left))
    right_norm = math.sqrt(sum(float(value) * float(value) for value in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return numerator / (left_norm * right_norm)


def _unreachable_handler(arguments: dict[str, object]) -> object:
    del arguments
    raise RuntimeError("Synthetic selector profile tools are not executable.")


__all__ = [
    "DefaultDynamicToolSelector",
    "ToolProfileOverride",
    "build_tool_selection_query",
    "resolve_tool_definition_profiles",
    "resolve_registry_tool_profiles",
    "resolve_tool_profiles",
]
