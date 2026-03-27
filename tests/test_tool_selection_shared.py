from __future__ import annotations

import pytest

from harnessiq.shared.agents import AgentRuntimeConfig, merge_agent_runtime_config
from harnessiq.shared.tool_selection import (
    ToolProfile,
    ToolSelectionConfig,
    ToolSelectionResult,
)


def test_tool_profile_normalizes_strings_and_tags() -> None:
    profile = ToolProfile(
        key=" filesystem.read_text_file ",
        name=" read_text_file ",
        family=" Filesystem ",
        description=" Read a UTF-8 text file. ",
        tags=("read", " text ", "read"),
    )

    assert profile.key == "filesystem.read_text_file"
    assert profile.name == "read_text_file"
    assert profile.family == "filesystem"
    assert profile.description == "Read a UTF-8 text file."
    assert profile.tags == ("read", "text")


def test_tool_selection_config_normalizes_tool_keys_and_embedding_model() -> None:
    config = ToolSelectionConfig(
        enabled=True,
        embedding_model=" openai:text-embedding-3-small ",
        candidate_tool_keys=("filesystem.read_text_file", "filesystem.read_text_file", "text.normalize"),
        mandatory_tools=("control.pause_for_human", " control.pause_for_human "),
    )

    assert config.enabled is True
    assert config.embedding_model == "openai:text-embedding-3-small"
    assert config.candidate_tool_keys == ("filesystem.read_text_file", "text.normalize")
    assert config.mandatory_tools == ("control.pause_for_human",)


def test_tool_selection_config_rejects_non_positive_top_k() -> None:
    with pytest.raises(ValueError, match="greater than zero"):
        ToolSelectionConfig(top_k=0)


def test_tool_selection_result_normalizes_keys_and_scores() -> None:
    result = ToolSelectionResult(
        selected_keys=("filesystem.read_text_file", "filesystem.read_text_file"),
        retrieval_query=" inspect files ",
        scored_tools=(("filesystem.read_text_file", 0.9),),
    )

    assert result.selected_keys == ("filesystem.read_text_file",)
    assert result.retrieval_query == "inspect files"
    assert result.scored_tools == (("filesystem.read_text_file", 0.9),)


def test_agent_runtime_config_carries_tool_selection_without_changing_defaults() -> None:
    runtime = AgentRuntimeConfig()

    assert runtime.tool_selection.enabled is False
    assert runtime.allowed_tools == ()


def test_merge_agent_runtime_config_preserves_tool_selection() -> None:
    runtime = AgentRuntimeConfig(
        tool_selection=ToolSelectionConfig(
            enabled=True,
            embedding_model="openai:text-embedding-3-small",
            top_k=7,
        )
    )

    merged = merge_agent_runtime_config(
        runtime,
        max_tokens=90_000,
        reset_threshold=0.8,
    )

    assert merged.tool_selection.enabled is True
    assert merged.tool_selection.embedding_model == "openai:text-embedding-3-small"
    assert merged.tool_selection.top_k == 7
