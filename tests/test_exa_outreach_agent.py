"""Tests for ExaOutreachAgent harness behavior and internal tools."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from harnessiq.agents import ExaOutreachAgent, ExaOutreachMemoryStore
from harnessiq.agents.exa_outreach.agent import ExaOutreachAgentConfig
from harnessiq.shared.agents import AgentModelResponse
from harnessiq.shared.exceptions import ConfigurationError, NotFoundError, ResourceNotFoundError, StateError
from harnessiq.shared.exa_outreach import EmailTemplate, FileSystemStorageBackend
from harnessiq.shared.tools import (
    EXA_OUTREACH_CHECK_CONTACTED,
    EXA_OUTREACH_GET_TEMPLATE,
    EXA_OUTREACH_LIST_TEMPLATES,
    EXA_OUTREACH_LOG_EMAIL_SENT,
    EXA_OUTREACH_LOG_LEAD,
    EXA_REQUEST,
    RegisteredTool,
    ToolCall,
    ToolDefinition,
)


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


def _make_exa_client() -> MagicMock:
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
    return mock_exa_client


def _make_resend_client() -> MagicMock:
    mock_resend_client = MagicMock()
    mock_resend_client.credentials.timeout_seconds = 30.0
    mock_resend_client.prepare_request.return_value = MagicMock(
        operation=MagicMock(name="send_email"),
        method="POST",
        url="https://api.resend.com/send-email",
        headers={},
        json_body={},
        path="/send-email",
    )
    mock_resend_client.request_executor = MagicMock(return_value={"id": "email_123"})
    return mock_resend_client


def _make_agent(tmp_path: Path, templates=None, **kwargs) -> ExaOutreachAgent:
    templates = [_make_template()] if templates is None else templates
    return ExaOutreachAgent(
        model=_make_model(),
        email_data=templates,
        search_query="VPs of Engineering at Series B startups",
        memory_path=tmp_path / "outreach",
        exa_client=_make_exa_client(),
        **kwargs,
    )


class TestExaOutreachAgentConstruction:
    def test_basic_construction(self, tmp_path):
        agent = _make_agent(tmp_path)
        assert agent.name == "exa_outreach"

    def test_empty_email_data_raises_when_search_only_is_false(self, tmp_path):
        with pytest.raises(ConfigurationError, match="at least one email template") as raised:
            ExaOutreachAgent(
                model=_make_model(),
                email_data=[],
                memory_path=tmp_path / "outreach",
                exa_client=_make_exa_client(),
            )
        assert isinstance(raised.value, ValueError)

    def test_search_only_allows_empty_email_data(self, tmp_path):
        agent = ExaOutreachAgent(
            model=_make_model(),
            email_data=[],
            search_only=True,
            memory_path=tmp_path / "outreach",
            exa_client=_make_exa_client(),
        )
        assert agent.config.search_only is True
        assert agent.config.email_data == ()

    def test_dict_email_data_coerced(self, tmp_path):
        data = [{"id": "t1", "title": "T", "subject": "S", "actual_email": "Body", "description": "D"}]
        agent = ExaOutreachAgent(
            model=_make_model(),
            email_data=data,
            memory_path=tmp_path / "outreach",
            exa_client=_make_exa_client(),
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

    def test_config_dataclass_allows_empty_templates_in_search_only_mode(self, tmp_path):
        config = ExaOutreachAgentConfig(
            email_data=(),
            memory_path=tmp_path,
            storage_backend=MagicMock(),
            search_only=True,
        )
        assert config.search_only is True


class TestAvailableTools:
    def test_custom_tools_are_added_to_the_agent_surface(self, tmp_path):
        custom_tool = RegisteredTool(
            definition=ToolDefinition(
                key="custom.outreach_helper",
                name="outreach_helper",
                description="Custom helper.",
                input_schema={"type": "object", "properties": {}, "required": [], "additionalProperties": False},
            ),
            handler=lambda arguments: {"ok": True, "arguments": arguments},
        )
        agent = _make_agent(tmp_path, tools=(custom_tool,))

        keys = {tool.key for tool in agent.available_tools()}

        assert "custom.outreach_helper" in keys

    def test_exa_request_tool_present(self, tmp_path):
        agent = _make_agent(tmp_path)
        keys = {tool.key for tool in agent.available_tools()}
        assert EXA_REQUEST in keys

    def test_normal_mode_registers_email_related_internal_tools(self, tmp_path):
        agent = _make_agent(tmp_path, resend_client=_make_resend_client())
        keys = {tool.key for tool in agent.available_tools()}
        assert EXA_OUTREACH_LIST_TEMPLATES in keys
        assert EXA_OUTREACH_GET_TEMPLATE in keys
        assert EXA_OUTREACH_CHECK_CONTACTED in keys
        assert EXA_OUTREACH_LOG_LEAD in keys
        assert EXA_OUTREACH_LOG_EMAIL_SENT in keys
        assert "resend.request" in keys

    def test_resend_tools_absent_when_no_credentials_or_client(self, tmp_path):
        agent = _make_agent(tmp_path, resend_credentials=None, resend_client=None)
        keys = {tool.key for tool in agent.available_tools()}
        assert "resend.request" not in keys

    def test_search_only_removes_email_tool_surface(self, tmp_path):
        agent = ExaOutreachAgent(
            model=_make_model(),
            email_data=[],
            search_only=True,
            memory_path=tmp_path / "outreach",
            exa_client=_make_exa_client(),
            resend_client=_make_resend_client(),
        )
        keys = {tool.key for tool in agent.available_tools()}
        assert EXA_REQUEST in keys
        assert EXA_OUTREACH_CHECK_CONTACTED in keys
        assert EXA_OUTREACH_LOG_LEAD in keys
        assert EXA_OUTREACH_LIST_TEMPLATES not in keys
        assert EXA_OUTREACH_GET_TEMPLATE not in keys
        assert EXA_OUTREACH_LOG_EMAIL_SENT not in keys
        assert "resend.request" not in keys


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
            with pytest.raises(ResourceNotFoundError, match="master_prompt.md") as raised:
                agent.build_system_prompt()
        assert isinstance(raised.value, FileNotFoundError)

    def test_additional_prompt_appended(self, tmp_path):
        agent = _make_agent(tmp_path)
        agent.prepare()
        agent.memory_store.write_additional_prompt("Keep emails under 80 words.")
        prompt = agent.build_system_prompt()
        assert "Keep emails under 80 words." in prompt
        assert "[ADDITIONAL INSTRUCTIONS]" in prompt

    def test_search_only_prompt_explicitly_forbids_email_work(self, tmp_path):
        agent = ExaOutreachAgent(
            model=_make_model(),
            email_data=[],
            search_only=True,
            memory_path=tmp_path / "outreach",
            exa_client=_make_exa_client(),
        )
        agent.prepare()
        prompt = agent.build_system_prompt()
        assert "Search-only mode is enabled." in prompt
        assert "Do not attempt template selection, email drafting, or email sending." in prompt

    def test_legacy_default_identity_is_not_treated_as_custom_override(self, tmp_path):
        legacy_identity = (
            "A disciplined outreach specialist who finds relevant prospects via Exa neural "
            "search, selects the most appropriate email template for each lead, personalizes "
            "the message with specific details from their profile, and sends concise, "
            "value-first cold emails."
        )
        agent = ExaOutreachAgent(
            model=_make_model(),
            email_data=[],
            search_only=True,
            memory_path=tmp_path / "outreach",
            exa_client=_make_exa_client(),
        )
        agent.prepare()
        agent.memory_store.write_agent_identity(legacy_identity)

        prompt = agent.build_system_prompt()

        assert "(You are ExaOutreachAgent.)" not in prompt


class TestLoadParameterSections:
    def test_normal_mode_returns_three_sections(self, tmp_path):
        agent = _make_agent(tmp_path)
        agent.prepare()
        sections = agent.load_parameter_sections()
        assert len(sections) == 3

    def test_email_templates_section_is_first_in_normal_mode(self, tmp_path):
        agent = _make_agent(tmp_path)
        agent.prepare()
        sections = agent.load_parameter_sections()
        assert sections[0].title == "Email Templates"
        templates_data = json.loads(sections[0].content)
        assert len(templates_data) == 1
        assert templates_data[0]["id"] == "t1"

    def test_search_only_omits_email_templates_section(self, tmp_path):
        agent = ExaOutreachAgent(
            model=_make_model(),
            email_data=[],
            search_only=True,
            memory_path=tmp_path / "outreach",
            exa_client=_make_exa_client(),
        )
        agent.prepare()
        sections = agent.load_parameter_sections()
        assert [section.title for section in sections] == ["Search Query", "Current Run"]
        assert '"search_only": true' in sections[0].content


class TestInternalToolHandlers:
    def test_list_templates_returns_all_templates(self, tmp_path):
        templates = [_make_template("t1"), _make_template("t2")]
        agent = _make_agent(tmp_path, templates=templates)
        result = agent.tool_executor.execute(EXA_OUTREACH_LIST_TEMPLATES, {})
        assert result.output["count"] == 2
        ids = [template["id"] for template in result.output["templates"]]
        assert "t1" in ids and "t2" in ids

    def test_get_template_returns_full_template(self, tmp_path):
        agent = _make_agent(tmp_path)
        result = agent.tool_executor.execute(EXA_OUTREACH_GET_TEMPLATE, {"template_id": "t1"})
        assert result.output["id"] == "t1"
        assert "actual_email" in result.output

    def test_get_template_raises_shared_not_found_error_for_unknown_template(self, tmp_path):
        agent = _make_agent(tmp_path)

        with pytest.raises(NotFoundError, match="Template 'missing' not found") as raised:
            agent.tool_executor.execute(EXA_OUTREACH_GET_TEMPLATE, {"template_id": "missing"})

        assert isinstance(raised.value, LookupError)

    def test_check_contacted_returns_false_for_new_url(self, tmp_path):
        agent = _make_agent(tmp_path)
        agent.prepare()
        result = agent.tool_executor.execute(
            EXA_OUTREACH_CHECK_CONTACTED,
            {"url": "https://example.com/new"},
        )
        assert result.output["already_contacted"] is False

    def test_check_contacted_returns_true_after_lead_logged(self, tmp_path):
        agent = ExaOutreachAgent(
            model=_make_model(),
            email_data=[],
            search_only=True,
            memory_path=tmp_path / "outreach",
            exa_client=_make_exa_client(),
        )
        agent.prepare()
        agent.tool_executor.execute(
            EXA_OUTREACH_LOG_LEAD,
            {"url": "https://example.com/alice", "name": "Alice"},
        )
        result = agent.tool_executor.execute(
            EXA_OUTREACH_CHECK_CONTACTED,
            {"url": "https://example.com/alice"},
        )
        assert result.output["already_contacted"] is True

    def test_log_lead_writes_event_to_run_file(self, tmp_path):
        agent = ExaOutreachAgent(
            model=_make_model(),
            email_data=[],
            search_only=True,
            memory_path=tmp_path / "outreach",
            exa_client=_make_exa_client(),
        )
        agent.prepare()
        result = agent.tool_executor.execute(
            EXA_OUTREACH_LOG_LEAD,
            {"url": "https://example.com/bob", "name": "Bob", "email_address": "bob@example.com"},
        )
        assert result.output["url"] == "https://example.com/bob"
        run_file = tmp_path / "outreach" / "runs" / "run_1.json"
        data = json.loads(run_file.read_text())
        lead_events = [event for event in data["events"] if event["type"] == "lead"]
        assert len(lead_events) == 1
        assert lead_events[0]["data"]["url"] == "https://example.com/bob"

    def test_log_lead_raises_shared_state_error_before_prepare(self, tmp_path):
        agent = ExaOutreachAgent(
            model=_make_model(),
            email_data=[],
            search_only=True,
            memory_path=tmp_path / "outreach",
            exa_client=_make_exa_client(),
        )

        with pytest.raises(StateError, match="before prepare") as raised:
            agent.tool_executor.execute(
                EXA_OUTREACH_LOG_LEAD,
                {"url": "https://example.com/bob", "name": "Bob"},
            )

        assert isinstance(raised.value, RuntimeError)

    def test_log_email_sent_writes_event_to_run_file(self, tmp_path):
        agent = _make_agent(tmp_path, resend_client=_make_resend_client())
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
        email_events = [event for event in data["events"] if event["type"] == "email_sent"]
        assert len(email_events) == 1
        assert email_events[0]["data"]["template_id"] == "t1"

    def test_log_email_sent_raises_shared_state_error_before_prepare(self, tmp_path):
        agent = _make_agent(tmp_path, resend_client=_make_resend_client())

        with pytest.raises(StateError, match="before prepare") as raised:
            agent.tool_executor.execute(
                EXA_OUTREACH_LOG_EMAIL_SENT,
                {
                    "to_email": "alice@example.com",
                    "to_name": "Alice",
                    "subject": "Quick intro",
                    "template_id": "t1",
                },
            )

        assert isinstance(raised.value, RuntimeError)


class TestPrepareAndRunOutputs:
    def test_prepare_creates_memory_and_starts_run(self, tmp_path):
        agent = _make_agent(tmp_path)
        agent.prepare()
        assert agent.memory_store.memory_path.exists()
        assert agent.memory_store.runs_dir.exists()
        run_file = tmp_path / "outreach" / "runs" / "run_1.json"
        assert run_file.exists()
        payload = json.loads(run_file.read_text())
        assert payload["metadata"]["search_only"] is False

    def test_search_only_prepare_records_mode_in_run_metadata(self, tmp_path):
        agent = ExaOutreachAgent(
            model=_make_model(),
            email_data=[],
            search_only=True,
            memory_path=tmp_path / "outreach",
            exa_client=_make_exa_client(),
        )
        agent.prepare()
        payload = json.loads((tmp_path / "outreach" / "runs" / "run_1.json").read_text())
        assert payload["metadata"]["search_only"] is True

    def test_build_ledger_metadata_reports_search_only(self, tmp_path):
        agent = ExaOutreachAgent(
            model=_make_model(),
            email_data=[],
            search_only=True,
            memory_path=tmp_path / "outreach",
            exa_client=_make_exa_client(),
        )
        agent.prepare()
        metadata = agent.build_ledger_metadata()
        assert metadata["search_only"] is True
        assert metadata["template_count"] == 0

    def test_build_ledger_tags_switch_for_search_only_mode(self, tmp_path):
        agent = ExaOutreachAgent(
            model=_make_model(),
            email_data=[],
            search_only=True,
            memory_path=tmp_path / "outreach",
            exa_client=_make_exa_client(),
        )
        assert agent.build_ledger_tags() == ["outreach", "sales", "lead_discovery"]

    def test_search_only_run_completes_with_lead_logged_and_no_emails(self, tmp_path):
        model = MagicMock()
        model.generate_turn.return_value = AgentModelResponse(
            assistant_message="Found one new lead.",
            tool_calls=(
                ToolCall(
                    tool_key=EXA_OUTREACH_CHECK_CONTACTED,
                    arguments={"url": "https://example.com/prospects/alice"},
                ),
                ToolCall(
                    tool_key=EXA_OUTREACH_LOG_LEAD,
                    arguments={
                        "url": "https://example.com/prospects/alice",
                        "name": "Alice Prospect",
                        "email_address": "alice@example.com",
                    },
                ),
            ),
            should_continue=False,
        )
        agent = ExaOutreachAgent(
            model=model,
            email_data=[],
            search_only=True,
            memory_path=tmp_path / "outreach",
            exa_client=_make_exa_client(),
        )

        result = agent.run(max_cycles=1)
        run_log = agent.memory_store.read_run("run_1")

        assert result.status == "completed"
        assert result.cycles_completed == 1
        assert len(run_log.leads_found) == 1
        assert run_log.leads_found[0].url == "https://example.com/prospects/alice"
        assert run_log.emails_sent == []


class TestSDKExport:
    def test_agent_importable_from_harnessiq_agents(self):
        from harnessiq.agents import ExaOutreachAgent as agent_type

        assert agent_type is ExaOutreachAgent

    def test_memory_store_importable_from_harnessiq_agents(self):
        from harnessiq.agents import ExaOutreachMemoryStore as store_type

        assert store_type is ExaOutreachMemoryStore
