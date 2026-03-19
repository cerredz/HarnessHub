"""Tests for the leads tool factory."""

from __future__ import annotations

import pytest

from harnessiq.shared.leads import LeadsAgentConfig, LeadsMemoryStore
from harnessiq.shared.tools import (
    LEADS_CHECK_SEEN,
    LEADS_COMPACT_SEARCH_HISTORY,
    LEADS_LOG_SEARCH,
    LEADS_SAVE_LEADS,
    RegisteredTool,
    ToolDefinition,
)
from harnessiq.tools.leads import create_leads_tools


def _dummy_provider_tool() -> RegisteredTool:
    return RegisteredTool(
        definition=ToolDefinition(
            key="apollo.request",
            name="apollo_request",
            description="Fake Apollo tool for leads tool tests.",
            input_schema={
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": True,
            },
        ),
        handler=lambda arguments: {"ok": True, "arguments": arguments},
    )


def test_create_leads_tools_appends_internal_tools_after_provider_tools(tmp_path):
    config = LeadsAgentConfig.from_inputs(
        company_background="We sell outbound infrastructure to B2B SaaS teams.",
        icps=("VP Sales",),
        platforms=("apollo",),
        memory_path=tmp_path / "memory",
    )
    memory_store = LeadsMemoryStore(config.memory_path)
    memory_store.prepare()
    memory_store.write_run_config(config.run_config)
    memory_store.initialize_icp_states(config.run_config.icps)

    tools = create_leads_tools(
        config=config,
        memory_store=memory_store,
        current_icp=lambda: config.run_config.icps[0],
        current_run_id=lambda: "run_1",
        refresh_parameters=lambda: None,
        provider_tools=(_dummy_provider_tool(),),
    )

    assert [tool.key for tool in tools] == [
        "apollo.request",
        LEADS_LOG_SEARCH,
        LEADS_COMPACT_SEARCH_HISTORY,
        LEADS_CHECK_SEEN,
        LEADS_SAVE_LEADS,
    ]


def test_create_leads_tools_rejects_unknown_platform_without_override(tmp_path):
    config = LeadsAgentConfig.from_inputs(
        company_background="We sell outbound infrastructure to B2B SaaS teams.",
        icps=("VP Sales",),
        platforms=("unknown_platform",),
        memory_path=tmp_path / "memory",
    )
    memory_store = LeadsMemoryStore(config.memory_path)
    memory_store.prepare()
    memory_store.write_run_config(config.run_config)
    memory_store.initialize_icp_states(config.run_config.icps)

    with pytest.raises(ValueError, match="Unsupported leads platform 'unknown_platform'"):
        create_leads_tools(
            config=config,
            memory_store=memory_store,
            current_icp=lambda: config.run_config.icps[0],
            current_run_id=lambda: "run_1",
            refresh_parameters=lambda: None,
        )
