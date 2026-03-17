"""Tests for ExaOutreachAgent harness and internal tools."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from harnessiq.agents import ExaOutreachAgent, ExaOutreachMemoryStore
from harnessiq.agents.exa_outreach.agent import ExaOutreachAgentConfig
from harnessiq.shared.agents import AgentModelRequest, AgentModelResponse
from harnessiq.shared.exa_outreach import (
    EmailTemplate,
    FileSystemStorageBackend,
    LeadRecord,
)
from harnessiq.shared.tools import (
    EXA_OUTREACH_CHECK_CONTACTED,
    EXA_OUTREACH_GET_TEMPLATE,
    EXA_OUTREACH_LIST_TEMPLATES,
    EXA_OUTREACH_LOG_EMAIL_SENT,
    EXA_OUTREACH_LOG_LEAD,
    EXA_REQUEST,
)


# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------


def _make_template(template_id: str = "t1", **overrides) -> EmailTemplate:
    defaults = dict(
        id=template_id,
        title="Cold Intro",
        subject="Hi there",
        description="Standard intro",
        actual_email="Hi {{name}}, I wanted to reach out...",
    )
    defaults.update(overrides)
    return EmailTemplate(**defaults)


def _make_model(should_continue: bool = False) -> MagicMock:
    model = MagicMock()
    model.generate_turn.return_value = AgentModelResponse(
        assistant_message="Done.",
        should_continue=should_continue,
    )
    return model


def _make_agent(tmp_path: Path, templates=None, **kwargs) -> ExaOutreachAgent:
    templates = templates or [_make_template()]
    # Provide a mock exa client to satisfy the exa tools factory.
    mock_exa_client = MagicMock()
    mock_exa_client.credentials.timeout_seconds = 30.0
    mock_exa_client.prepare_request.return_value = MagicMock(
        operation=MagicMock(name="search_and_contents"),
        method="POST",
        url="https://api.exa.ai/searchAndContents",
        headers={},
        json_body={},
        path="/searchAndContents",
    )
    mock_exa_client.request_executor = MagicMock(return_value={"results": []})

    return ExaOutreachAgent(
        model=_make_model(),
        email_data=templates,
        search_query="VPs of Engineering at Series B startups",
        memory_path=tmp_path / "outreach",
        exa_client=mock_exa_client,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


class TestExaOutreachAgentConstruction:
    def test_basic_construction(self, tmp_path):
        agent = _make_agent(tmp_path)
        assert agent.name == "exa_outreach"

    def test_empty_email_data_raises(self, tmp_path):
        mock_exa_client = MagicMock()
        mock_exa_client.credentials.timeout_seconds = 30.0
        with pytest.raises(ValueError, match="at least one email template"):
            ExaOutreachAgent(
                model=_make_model(),
                email_data=[],
                memory_path=tmp_path / "outreach",
                exa_client=mock_exa_client,
            )

    def test_dict_email_data_coerced(self, tmp_path):
        mock_exa_client = MagicMock()
        mock_exa_client.credentials.timeout_seconds = 30.0
        data = [{"id": "t1", "title": "T", "subject": "S", "actual_email": "Body", "description": "D"}]
        agent = ExaOutreachAgent(
            model=_make_model(),
            email_data=data,
            memory_path=tmp_path / "outreach",
            exa_client=mock_exa_client,
        )
        assert agent.config.email_data[0].id == "t1"

    def test_default_storage_backend_is_filesystem(self, tmp_path):
        agent = _make_agent(tmp_path)
        assert isinstance(agent.config.storage_backend, FileSystemStorageBackend)

    def test_custom_storage_backend_accepted(self, tmp_path):
        custom_backend = MagicMock()
        custom_backend.start_run = MagicMock()
        custom_backend.finish_run = MagicMock()
        custom_backend.log_event = MagicMock()
        custom_backend.has_seen = MagicMock(return_value=False)
        custom_backend.current_run_id = MagicMock(return_value=None)
        agent = _make_agent(tmp_path, storage_backend=custom_backend)
        assert agent.config.storage_backend is custom_backend


# ---------------------------------------------------------------------------
# Available tools
# ---------------------------------------------------------------------------


class TestAvailableTools:
    def test_exa_request_tool_present(self, tmp_path):
        agent = _make_agent(tmp_path)
        keys = {t.key for t in agent.available_tools()}
        assert EXA_REQUEST in keys

    def test_all_internal_tool_keys_present(self, tmp_path):
        agent = _make_agent(tmp_path)
        keys = {t.key for t in agent.available_tools()}
        assert EXA_OUTREACH_LIST_TEMPLATES in keys
        assert EXA_OUTREACH_GET_TEMPLATE in keys
        assert EXA_OUTREACH_CHECK_CONTACTED in keys
        assert EXA_OUTREACH_LOG_LEAD in keys
        assert EXA_OUTREACH_LOG_EMAIL_SENT in keys

    def test_resend_tools_absent_when_no_credentials(self, tmp_path):
        agent = _make_agent(tmp_path, resend_credentials=None, resend_client=None)
        keys = {t.key for t in agent.available_tools()}
        assert "resend.request" not in keys


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------


class TestBuildSystemPrompt:
    def test_loads_master_prompt_file(self, tmp_path):
        agent = _make_agent(tmp_path)
        agent.prepare()
        prompt = agent.build_system_prompt()
        assert "[IDENTITY]" in prompt
        assert "[GOAL]" in prompt
        assert "[BEHAVIORAL RULES]" in prompt

    def test_missing_master_prompt_raises(self, tmp_path):
        agent = _make_agent(tmp_path)
        agent.prepare()
        with patch("harnessiq.agents.exa_outreach.agent._MASTER_PROMPT_PATH") as mock_path:
            mock_path.exists.return_value = False
            with pytest.raises(FileNotFoundError, match="master_prompt.md"):
                agent.build_system_prompt()

    def test_additional_prompt_appended(self, tmp_path):
        agent = _make_agent(tmp_path)
        agent.prepare()
        agent.memory_store.write_additional_prompt("Keep emails under 80 words.")
        prompt = agent.build_system_prompt()
        assert "Keep emails under 80 words." in prompt
        assert "[ADDITIONAL INSTRUCTIONS]" in prompt


# ---------------------------------------------------------------------------
# Parameter sections
# ---------------------------------------------------------------------------


class TestLoadParameterSections:
    def test_returns_three_sections(self, tmp_path):
        agent = _make_agent(tmp_path)
        agent.prepare()
        sections = agent.load_parameter_sections()
        assert len(sections) == 3

    def test_email_templates_section_is_first(self, tmp_path):
        agent = _make_agent(tmp_path)
        agent.prepare()
        sections = agent.load_parameter_sections()
        assert sections[0].title == "Email Templates"
        templates_data = json.loads(sections[0].content)
        assert len(templates_data) == 1
        assert templates_data[0]["id"] == "t1"

    def test_search_query_section_is_second(self, tmp_path):
        agent = _make_agent(tmp_path)
        agent.prepare()
        sections = agent.load_parameter_sections()
        assert sections[1].title == "Search Query"
        assert "VPs of Engineering" in sections[1].content

    def test_current_run_section_is_third(self, tmp_path):
        agent = _make_agent(tmp_path)
        agent.prepare()
        sections = agent.load_parameter_sections()
        assert sections[2].title == "Current Run"
        assert sections[2].content == "run_1"


# ---------------------------------------------------------------------------
# Internal tool handlers
# ---------------------------------------------------------------------------


class TestListTemplatesHandler:
    def test_returns_all_templates(self, tmp_path):
        templates = [_make_template("t1"), _make_template("t2")]
        agent = _make_agent(tmp_path, templates=templates)
        result = agent.tool_executor.execute(EXA_OUTREACH_LIST_TEMPLATES, {})
        assert result.output["count"] == 2
        ids = [t["id"] for t in result.output["templates"]]
        assert "t1" in ids and "t2" in ids

    def test_returns_metadata_not_actual_email(self, tmp_path):
        agent = _make_agent(tmp_path)
        result = agent.tool_executor.execute(EXA_OUTREACH_LIST_TEMPLATES, {})
        template = result.output["templates"][0]
        assert "actual_email" not in template
        assert "description" in template


class TestGetTemplateHandler:
    def test_returns_full_template(self, tmp_path):
        agent = _make_agent(tmp_path)
        result = agent.tool_executor.execute(EXA_OUTREACH_GET_TEMPLATE, {"template_id": "t1"})
        assert result.output["id"] == "t1"
        assert "actual_email" in result.output

    def test_unknown_id_raises(self, tmp_path):
        agent = _make_agent(tmp_path)
        with pytest.raises(ValueError, match="not found"):
            agent.tool_executor.execute(EXA_OUTREACH_GET_TEMPLATE, {"template_id": "unknown"})


class TestCheckContactedHandler:
    def test_returns_false_for_new_url(self, tmp_path):
        agent = _make_agent(tmp_path)
        agent.prepare()
        result = agent.tool_executor.execute(
            EXA_OUTREACH_CHECK_CONTACTED, {"url": "https://example.com/new"}
        )
        assert result.output["already_contacted"] is False

    def test_returns_true_after_lead_logged(self, tmp_path):
        agent = _make_agent(tmp_path)
        agent.prepare()
        # Log a lead first
        agent.tool_executor.execute(
            EXA_OUTREACH_LOG_LEAD,
            {"url": "https://example.com/alice", "name": "Alice"},
        )
        result = agent.tool_executor.execute(
            EXA_OUTREACH_CHECK_CONTACTED, {"url": "https://example.com/alice"}
        )
        assert result.output["already_contacted"] is True


class TestLogLeadHandler:
    def test_log_lead_writes_to_run_file(self, tmp_path):
        agent = _make_agent(tmp_path)
        agent.prepare()
        result = agent.tool_executor.execute(
            EXA_OUTREACH_LOG_LEAD,
            {"url": "https://example.com/bob", "name": "Bob", "email_address": "bob@example.com"},
        )
        assert result.output["url"] == "https://example.com/bob"
        assert result.output["name"] == "Bob"
        # Verify written to disk in generic event format
        run_file = tmp_path / "outreach" / "runs" / "run_1.json"
        data = json.loads(run_file.read_text())
        lead_events = [e for e in data["events"] if e["type"] == "lead"]
        assert len(lead_events) == 1
        assert lead_events[0]["data"]["url"] == "https://example.com/bob"

    def test_log_lead_without_prepare_raises(self, tmp_path):
        agent = _make_agent(tmp_path)
        with pytest.raises(RuntimeError, match="prepare\\(\\)"):
            agent.tool_executor.execute(
                EXA_OUTREACH_LOG_LEAD,
                {"url": "https://example.com/x", "name": "X"},
            )


class TestLogEmailSentHandler:
    def test_log_email_sent_writes_to_run_file(self, tmp_path):
        agent = _make_agent(tmp_path)
        agent.prepare()
        result = agent.tool_executor.execute(
            EXA_OUTREACH_LOG_EMAIL_SENT,
            {
                "to_email": "alice@example.com",
                "to_name": "Alice",
                "subject": "Quick intro",
                "template_id": "t1",
            },
        )
        assert result.output["to_email"] == "alice@example.com"
        run_file = tmp_path / "outreach" / "runs" / "run_1.json"
        data = json.loads(run_file.read_text())
        email_events = [e for e in data["events"] if e["type"] == "email_sent"]
        assert len(email_events) == 1
        assert email_events[0]["data"]["template_id"] == "t1"

    def test_log_email_sent_without_prepare_raises(self, tmp_path):
        agent = _make_agent(tmp_path)
        with pytest.raises(RuntimeError, match="prepare\\(\\)"):
            agent.tool_executor.execute(
                EXA_OUTREACH_LOG_EMAIL_SENT,
                {"to_email": "x@x.com", "to_name": "X", "subject": "S", "template_id": "t1"},
            )


# ---------------------------------------------------------------------------
# prepare() and run integration
# ---------------------------------------------------------------------------


class TestPrepare:
    def test_prepare_creates_memory_and_starts_run(self, tmp_path):
        agent = _make_agent(tmp_path)
        agent.prepare()
        assert agent.memory_store.memory_path.exists()
        assert agent.memory_store.runs_dir.exists()
        assert (tmp_path / "outreach" / "runs" / "run_1.json").exists()

    def test_run_increments_run_id(self, tmp_path):
        # First run
        agent = _make_agent(tmp_path)
        agent.prepare()
        assert (tmp_path / "outreach" / "runs" / "run_1.json").exists()
        # Second run — new agent instance on same memory path
        agent2 = _make_agent(tmp_path)
        agent2.prepare()
        assert (tmp_path / "outreach" / "runs" / "run_2.json").exists()


# ---------------------------------------------------------------------------
# SDK-level import
# ---------------------------------------------------------------------------


class TestSDKExport:
    def test_agent_importable_from_harnessiq_agents(self):
        from harnessiq.agents import ExaOutreachAgent as A
        assert A is ExaOutreachAgent

    def test_memory_store_importable_from_harnessiq_agents(self):
        from harnessiq.agents import ExaOutreachMemoryStore as S
        assert S is ExaOutreachMemoryStore
