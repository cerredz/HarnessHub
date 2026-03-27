from __future__ import annotations

from harnessiq.interfaces import DynamicToolSelector
from harnessiq.shared.tool_selection import ToolProfile, ToolSelectionConfig
from harnessiq.toolset import (
    DefaultDynamicToolSelector,
    ToolProfileOverride,
    ToolsetRegistry,
    build_tool_selection_query,
    define_tool,
    resolve_registry_tool_profiles,
    resolve_tool_profiles,
)


class _KeywordEmbeddingBackend:
    def embed_texts(self, texts):
        return tuple(_embed_keywords(text) for text in texts)


def _embed_keywords(text: str) -> tuple[float, ...]:
    lowered = text.lower()
    return (
        float(sum(lowered.count(token) for token in ("read", "inspect", "file", "text"))),
        float(sum(lowered.count(token) for token in ("write", "save", "persist", "record"))),
        float(sum(lowered.count(token) for token in ("pause", "human", "approval"))),
        float(sum(lowered.count(token) for token in ("compact", "remove", "summarize", "prune"))),
    )


def test_resolve_registry_tool_profiles_preserves_order_and_supports_custom_tools() -> None:
    registry = ToolsetRegistry()
    custom_tool = define_tool(
        key="custom.shout",
        description="Convert text to uppercase.",
        parameters={"text": {"type": "string", "description": "The text to uppercase."}},
        required=["text"],
        handler=lambda arguments: arguments["text"].upper(),
    )
    registry.register_tool(custom_tool)

    profiles = resolve_registry_tool_profiles(
        registry,
        ("reason.brainstorm", "custom.shout", "context.remove_tool_results"),
    )

    assert [profile.key for profile in profiles] == [
        "reason.brainstorm",
        "custom.shout",
        "context.remove_tool_results",
    ]
    assert profiles[1].family == "custom"
    assert "Accepted parameters: text." in profiles[1].semantic_description
    assert profiles[2].always_on is True


def test_resolve_tool_profiles_applies_retrieval_only_overrides() -> None:
    custom_tool = define_tool(
        key="custom.persist_note",
        description="Persist a note to durable storage.",
        parameters={"note": {"type": "string"}},
        required=["note"],
        handler=lambda arguments: arguments["note"],
    )

    profiles = resolve_tool_profiles(
        (custom_tool,),
        profile_overrides={
            "custom.persist_note": ToolProfileOverride(
                tags=("custom", "persist", "notes"),
                when_to_use="Use when a verified note must be stored durably.",
                limitations="Not for transient scratch work.",
                always_on=True,
                retrievable=False,
            )
        },
    )

    assert profiles[0].tags == ("custom", "persist", "notes")
    assert profiles[0].when_to_use == "Use when a verified note must be stored durably."
    assert profiles[0].limitations == "Not for transient scratch work."
    assert profiles[0].always_on is True
    assert profiles[0].retrievable is False


def test_default_dynamic_tool_selector_ranks_within_candidate_ceiling_and_keeps_mandatory_tools() -> None:
    selector = DefaultDynamicToolSelector(
        config=ToolSelectionConfig(
            enabled=True,
            top_k=1,
            mandatory_tools=("control.pause_for_human",),
        ),
        embedding_backend=_KeywordEmbeddingBackend(),
    )
    assert isinstance(selector, DynamicToolSelector)
    profiles = (
        ToolProfile(
            key="filesystem.read_text_file",
            name="read_text_file",
            family="filesystem",
            description="Read a UTF-8 text file.",
            semantic_description="Read file contents from disk and inspect text.",
            tags=("filesystem", "read", "file"),
            when_to_use="Use when the agent needs to inspect a text file.",
        ),
        ToolProfile(
            key="records.save_output",
            name="save_output",
            family="records",
            description="Persist a validated output record.",
            semantic_description="Write or save durable records after validation.",
            tags=("records", "write", "save"),
            when_to_use="Use when the agent needs to save validated output.",
        ),
        ToolProfile(
            key="control.pause_for_human",
            name="pause_for_human",
            family="control",
            description="Pause the run and wait for human input.",
            semantic_description="Pause execution and request human approval.",
            tags=("control", "pause", "human"),
            when_to_use="Use when the agent needs approval before continuing.",
        ),
    )

    selector.index(profiles)
    result = selector.select(
        context_window=[{"kind": "user", "content": "Inspect the file contents before continuing."}],
        candidate_profiles=profiles,
    )

    assert result.selected_keys == ("filesystem.read_text_file", "control.pause_for_human")
    assert result.mandatory_keys == ("control.pause_for_human",)
    assert set(result.selected_keys).issubset({profile.key for profile in profiles})
    assert result.rejected_keys == ("records.save_output",)


def test_default_dynamic_tool_selector_uses_fallback_when_threshold_filters_everything() -> None:
    selector = DefaultDynamicToolSelector(
        config=ToolSelectionConfig(
            enabled=True,
            top_k=2,
            min_similarity=0.9,
            expand_on_miss=True,
        ),
        embedding_backend=_KeywordEmbeddingBackend(),
    )
    profiles = (
        ToolProfile(
            key="filesystem.read_text_file",
            name="read_text_file",
            family="filesystem",
            description="Read a UTF-8 text file.",
            semantic_description="Read file contents from disk.",
            tags=("filesystem", "read", "file"),
            when_to_use="Use when the agent needs to inspect a file.",
        ),
        ToolProfile(
            key="records.save_output",
            name="save_output",
            family="records",
            description="Persist a validated output record.",
            semantic_description="Write or save durable records.",
            tags=("records", "write", "save"),
            when_to_use="Use when the agent needs to persist results.",
        ),
    )

    result = selector.select(
        context_window=[],
        candidate_profiles=profiles,
        metadata={"query": "schedule a meeting with finance"},
    )

    assert result.fallback_used is True
    assert result.selected_keys == ("filesystem.read_text_file", "records.save_output")


def test_default_dynamic_tool_selector_respects_candidate_tool_key_config() -> None:
    selector = DefaultDynamicToolSelector(
        config=ToolSelectionConfig(
            enabled=True,
            top_k=2,
            candidate_tool_keys=("records.save_output",),
        ),
        embedding_backend=_KeywordEmbeddingBackend(),
    )
    profiles = (
        ToolProfile(
            key="filesystem.read_text_file",
            name="read_text_file",
            family="filesystem",
            description="Read a UTF-8 text file.",
            semantic_description="Read file contents from disk.",
            tags=("filesystem", "read", "file"),
            when_to_use="Use when the agent needs to inspect a file.",
        ),
        ToolProfile(
            key="records.save_output",
            name="save_output",
            family="records",
            description="Persist a validated output record.",
            semantic_description="Write or save durable records.",
            tags=("records", "write", "save"),
            when_to_use="Use when the agent needs to persist results.",
        ),
    )

    result = selector.select(
        context_window=[{"kind": "user", "content": "Read the file and inspect its contents."}],
        candidate_profiles=profiles,
    )

    assert result.selected_keys == ("records.save_output",)
    assert result.rejected_keys == ()


def test_build_tool_selection_query_prefers_explicit_query_and_renders_context_when_missing() -> None:
    explicit = build_tool_selection_query(
        [{"kind": "user", "content": "ignored"}],
        metadata={"query": "persist validated output"},
    )
    fallback = build_tool_selection_query(
        [
            {"kind": "assistant", "content": "Need to inspect the file."},
            {"kind": "tool_result", "tool_key": "filesystem.read_text_file", "output": {"path": "notes.txt"}},
        ]
    )

    assert explicit == "persist validated output"
    assert "assistant: Need to inspect the file." in fallback
    assert "tool_result:" in fallback
