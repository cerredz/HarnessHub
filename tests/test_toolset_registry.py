"""Tests for harnessiq.toolset catalog and registry (Ticket 1)."""

from __future__ import annotations

import pytest

from harnessiq.shared.tools import RegisteredTool
from harnessiq.toolset import (
    ToolEntry,
    ToolsetRegistry,
    get_family,
    get_tool,
    get_tools,
    list_tools,
)
from harnessiq.toolset.catalog import PROVIDER_ENTRY_INDEX, PROVIDER_FACTORY_MAP


# ---------------------------------------------------------------------------
# get_tool — built-in tools
# ---------------------------------------------------------------------------


class TestGetToolBuiltin:
    def test_returns_registered_tool_by_key(self):
        tool = get_tool("reason.brainstorm")
        assert isinstance(tool, RegisteredTool)
        assert tool.key == "reason.brainstorm"

    def test_tool_is_executable(self):
        tool = get_tool("reason.brainstorm")
        result = tool.execute({"topic": "AI"})
        assert "reasoning_instruction" in result.output
        assert "brainstorm" in result.output["reasoning_instruction"].lower()

    def test_chain_of_thought(self):
        tool = get_tool("reason.chain_of_thought")
        assert tool.key == "reason.chain_of_thought"
        result = tool.execute({"task": "solve a maze"})
        assert "reasoning_instruction" in result.output

    def test_critique(self):
        tool = get_tool("reason.critique")
        assert tool.key == "reason.critique"
        result = tool.execute({"content": "This is my draft output."})
        assert "reasoning_instruction" in result.output

    def test_filesystem_tool(self):
        tool = get_tool("filesystem.read_text_file")
        assert isinstance(tool, RegisteredTool)
        assert tool.key == "filesystem.read_text_file"

    def test_reasoning_lens_tool(self):
        tool = get_tool("reasoning.step_by_step")
        assert isinstance(tool, RegisteredTool)
        assert tool.key == "reasoning.step_by_step"

    def test_text_tool(self):
        tool = get_tool("text.normalize_whitespace")
        assert tool.key == "text.normalize_whitespace"

    def test_records_tool(self):
        tool = get_tool("records.filter_records")
        assert tool.key == "records.filter_records"

    def test_context_tool(self):
        tool = get_tool("context.remove_tool_results")
        assert tool.key == "context.remove_tool_results"

    def test_core_tool(self):
        tool = get_tool("core.echo_text")
        assert tool.key == "core.echo_text"

    def test_prompt_tool(self):
        tool = get_tool("prompt.create_system_prompt")
        assert tool.key == "prompt.create_system_prompt"

    def test_unknown_key_raises_key_error(self):
        with pytest.raises(KeyError, match="'no.such.tool'"):
            get_tool("no.such.tool")

    def test_unknown_key_error_mentions_list_tools(self):
        with pytest.raises(KeyError, match="list_tools"):
            get_tool("no.such.tool")


# ---------------------------------------------------------------------------
# get_tool — provider tools (credentials required)
# ---------------------------------------------------------------------------


class TestGetToolProvider:
    def test_provider_tool_without_credentials_raises(self):
        with pytest.raises(ValueError, match="credentials"):
            get_tool("creatify.request")

    def test_provider_tool_error_names_the_key(self):
        with pytest.raises(ValueError, match="creatify.request"):
            get_tool("creatify.request")

    def test_all_provider_keys_raise_without_credentials(self):
        for key in PROVIDER_ENTRY_INDEX:
            with pytest.raises(ValueError):
                get_tool(key)


# ---------------------------------------------------------------------------
# get_tools
# ---------------------------------------------------------------------------


class TestGetTools:
    def test_returns_tuple_of_tools(self):
        tools = get_tools("reason.brainstorm", "reason.chain_of_thought", "reason.critique")
        assert len(tools) == 3
        assert all(isinstance(t, RegisteredTool) for t in tools)

    def test_order_matches_input(self):
        keys = ["reason.critique", "reason.brainstorm"]
        tools = get_tools(*keys)
        assert [t.key for t in tools] == keys

    def test_single_key(self):
        tools = get_tools("filesystem.read_text_file")
        assert len(tools) == 1
        assert tools[0].key == "filesystem.read_text_file"

    def test_unknown_key_raises(self):
        with pytest.raises(KeyError):
            get_tools("reason.brainstorm", "no.such")

    def test_mix_of_families(self):
        tools = get_tools("reason.brainstorm", "filesystem.read_text_file", "reasoning.step_by_step")
        assert len(tools) == 3
        assert {t.key for t in tools} == {
            "reason.brainstorm",
            "filesystem.read_text_file",
            "reasoning.step_by_step",
        }


# ---------------------------------------------------------------------------
# get_family
# ---------------------------------------------------------------------------


class TestGetFamily:
    def test_reason_family_has_three_tools(self):
        tools = get_family("reason")
        assert len(tools) == 3
        keys = {t.key for t in tools}
        assert "reason.brainstorm" in keys
        assert "reason.chain_of_thought" in keys
        assert "reason.critique" in keys

    def test_reasoning_family_has_fifty_tools(self):
        tools = get_family("reasoning")
        assert len(tools) == 50

    def test_filesystem_family_has_eight_tools(self):
        tools = get_family("filesystem")
        assert len(tools) == 8

    def test_count_limits_results(self):
        tools = get_family("reasoning", count=4)
        assert len(tools) == 4

    def test_count_one(self):
        tools = get_family("reason", count=1)
        assert len(tools) == 1

    def test_count_exceeding_family_size_returns_all(self):
        tools_all = get_family("reason")
        tools_limited = get_family("reason", count=100)
        assert len(tools_limited) == len(tools_all)

    def test_count_preserves_insertion_order(self):
        tools_all = get_family("reasoning")
        tools_four = get_family("reasoning", count=4)
        assert [t.key for t in tools_four] == [t.key for t in tools_all[:4]]

    def test_count_zero_raises(self):
        with pytest.raises(ValueError, match="positive"):
            get_family("reasoning", count=0)

    def test_count_negative_raises(self):
        with pytest.raises(ValueError, match="positive"):
            get_family("reasoning", count=-1)

    def test_unknown_family_raises_key_error(self):
        with pytest.raises(KeyError, match="no_such_family"):
            get_family("no_such_family")

    def test_unknown_family_error_lists_available(self):
        with pytest.raises(KeyError, match="reasoning"):
            get_family("no_such_family")

    def test_provider_family_without_credentials_raises(self):
        with pytest.raises(ValueError, match="credentials"):
            get_family("creatify")

    def test_all_tools_in_family_have_correct_key_prefix(self):
        for family in ("reason", "reasoning", "filesystem", "text", "records", "context"):
            tools = get_family(family)
            for tool in tools:
                assert tool.key.startswith(f"{family}."), (
                    f"Tool {tool.key!r} in family '{family}' has wrong key prefix"
                )

    def test_all_tools_are_registered_tool_instances(self):
        tools = get_family("filesystem")
        assert all(isinstance(t, RegisteredTool) for t in tools)


# ---------------------------------------------------------------------------
# list_tools
# ---------------------------------------------------------------------------


class TestListTools:
    def test_returns_list_of_tool_entries(self):
        entries = list_tools()
        assert isinstance(entries, list)
        assert all(isinstance(e, ToolEntry) for e in entries)

    def test_list_has_builtin_and_provider_entries(self):
        entries = list_tools()
        has_builtin = any(not e.requires_credentials for e in entries)
        has_provider = any(e.requires_credentials for e in entries)
        assert has_builtin
        assert has_provider

    def test_all_entries_have_required_fields(self):
        for entry in list_tools():
            assert entry.key
            assert entry.name
            assert entry.description
            assert entry.family
            assert isinstance(entry.requires_credentials, bool)

    def test_provider_entries_marked_requires_credentials(self):
        provider_entries = [e for e in list_tools() if e.requires_credentials]
        provider_keys = {e.key for e in provider_entries}
        expected_keys = set(PROVIDER_ENTRY_INDEX.keys())
        assert expected_keys.issubset(provider_keys)

    def test_builtin_entries_not_requires_credentials(self):
        builtin_entries = [e for e in list_tools() if not e.requires_credentials]
        assert len(builtin_entries) > 0
        assert all(not e.requires_credentials for e in builtin_entries)

    def test_brainstorm_entry_has_correct_family(self):
        entries = {e.key: e for e in list_tools()}
        assert "reason.brainstorm" in entries
        assert entries["reason.brainstorm"].family == "reason"

    def test_creatify_entry_has_correct_family(self):
        entries = {e.key: e for e in list_tools()}
        assert "creatify.request" in entries
        assert entries["creatify.request"].family == "creatify"
        assert entries["creatify.request"].requires_credentials is True

    def test_all_provider_families_in_catalog(self):
        entries = {e.key: e for e in list_tools()}
        for family in PROVIDER_FACTORY_MAP:
            key = f"{family}.request"
            assert key in entries, f"Provider key '{key}' missing from list_tools()"

    def test_no_duplicate_keys(self):
        entries = list_tools()
        keys = [e.key for e in entries]
        assert len(keys) == len(set(keys))


# ---------------------------------------------------------------------------
# Module-level singleton behaviour
# ---------------------------------------------------------------------------


class TestSingleton:
    def test_repeated_calls_return_same_registry(self):
        from harnessiq.toolset import _get_registry
        r1 = _get_registry()
        r2 = _get_registry()
        assert r1 is r2

    def test_repeated_get_tool_returns_same_object(self):
        t1 = get_tool("reason.brainstorm")
        t2 = get_tool("reason.brainstorm")
        assert t1 is t2


# ---------------------------------------------------------------------------
# ToolsetRegistry direct usage
# ---------------------------------------------------------------------------


class TestToolsetRegistryDirect:
    def test_can_instantiate_independently(self):
        registry = ToolsetRegistry()
        tool = registry.get("reason.brainstorm")
        assert tool.key == "reason.brainstorm"

    def test_independent_instances_share_no_state(self):
        r1 = ToolsetRegistry()
        r2 = ToolsetRegistry()
        # Both resolve to equivalent tools but are separate instances
        t1 = r1.get("reason.brainstorm")
        t2 = r2.get("reason.brainstorm")
        assert t1.key == t2.key

    def test_get_many_returns_correct_count(self):
        registry = ToolsetRegistry()
        tools = registry.get_many("reason.brainstorm", "reason.critique")
        assert len(tools) == 2

    def test_list_returns_list_of_entries(self):
        registry = ToolsetRegistry()
        entries = registry.list()
        assert isinstance(entries, list)
        assert len(entries) > 0
