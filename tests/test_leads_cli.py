"""Tests for the leads CLI commands."""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

import pytest

from harnessiq.agents import AgentModelRequest, AgentModelResponse
from harnessiq.agents.leads.agent import LEADS_LOG_SEARCH, LEADS_SAVE_LEADS
from harnessiq.cli.leads.commands import (
    SUPPORTED_LEADS_RUNTIME_PARAMETERS,
    normalize_leads_runtime_parameters,
)
from harnessiq.cli.main import build_parser, main
from harnessiq.shared.leads import LeadRecord, LeadSaveResult
from harnessiq.shared.tools import RegisteredTool, ToolCall, ToolDefinition


def _run(argv: list[str]) -> int:
    return main(argv)


class _SavingModel:
    def __init__(self) -> None:
        self.requests: list[AgentModelRequest] = []

    def generate_turn(self, request: AgentModelRequest) -> AgentModelResponse:
        self.requests.append(request)
        return AgentModelResponse(
            assistant_message="Logged one search and saved one lead.",
            tool_calls=(
                ToolCall(
                    tool_key=LEADS_LOG_SEARCH,
                    arguments={
                        "platform": "apollo",
                        "query": "VP Sales at Series A SaaS companies",
                        "result_count": 1,
                        "new_leads": 1,
                    },
                ),
                ToolCall(
                    tool_key=LEADS_SAVE_LEADS,
                    arguments={
                        "leads": [
                            {
                                "full_name": "Alice Smith",
                                "company_name": "Acme",
                                "title": "VP Sales",
                                "provider": "apollo",
                                "provider_person_id": "person_1",
                            }
                        ]
                    },
                ),
            ),
            should_continue=False,
        )


class _RecordingStorageBackend:
    def __init__(self) -> None:
        self.started_runs: list[tuple[str, dict[str, Any]]] = []
        self.finished_runs: list[tuple[str, str]] = []
        self.saved_entries: list[tuple[str, str, tuple[LeadRecord, ...], dict[str, Any] | None]] = []
        self._saved_by_key: dict[str, LeadRecord] = {}
        self._current_run_id: str | None = None

    def start_run(self, run_id: str, metadata: dict[str, Any]) -> None:
        self._current_run_id = run_id
        self.started_runs.append((run_id, metadata))

    def finish_run(self, run_id: str, completed_at: str) -> None:
        self.finished_runs.append((run_id, completed_at))

    def save_leads(
        self,
        run_id: str,
        icp_key: str,
        leads,
        metadata: dict[str, Any] | None = None,
    ) -> tuple[LeadSaveResult, ...]:
        lead_tuple = tuple(leads)
        self.saved_entries.append((run_id, icp_key, lead_tuple, metadata))
        results: list[LeadSaveResult] = []
        for lead in lead_tuple:
            dedupe_key = lead.dedupe_key()
            if dedupe_key in self._saved_by_key:
                results.append(LeadSaveResult(lead=lead, saved=False, reason="duplicate"))
                continue
            self._saved_by_key[dedupe_key] = lead
            results.append(LeadSaveResult(lead=lead, saved=True, reason="saved"))
        return tuple(results)

    def has_seen_lead(self, dedupe_key: str) -> bool:
        return dedupe_key in self._saved_by_key

    def list_leads(self, *, icp_key: str | None = None) -> list[LeadRecord]:
        return list(self._saved_by_key.values())

    def current_run_id(self) -> str | None:
        return self._current_run_id


_LAST_STORAGE_BACKEND: _RecordingStorageBackend | None = None


def create_saving_model() -> _SavingModel:
    return _SavingModel()


def create_provider_tools() -> tuple[RegisteredTool, ...]:
    return (
        RegisteredTool(
            definition=ToolDefinition(
                key="apollo.request",
                name="apollo_request",
                description="Fake Apollo request tool for CLI tests.",
                input_schema={
                    "type": "object",
                    "properties": {},
                    "required": [],
                    "additionalProperties": True,
                },
            ),
            handler=lambda arguments: {"ok": True, "arguments": arguments},
        ),
    )


def create_storage_backend() -> _RecordingStorageBackend:
    global _LAST_STORAGE_BACKEND
    _LAST_STORAGE_BACKEND = _RecordingStorageBackend()
    return _LAST_STORAGE_BACKEND


class TestParserRegistration:
    def test_leads_subcommand_registered(self):
        parser = build_parser()
        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args(["leads", "--help"])
        assert exc_info.value.code == 0

    def test_leads_run_subcommand_registered(self):
        parser = build_parser()
        args, _ = parser.parse_known_args(
            [
                "leads",
                "run",
                "--agent",
                "test",
                "--model-factory",
                "mod:fn",
            ]
        )
        assert args.leads_command == "run"


class TestConfigureAndShow:
    def test_configure_and_show_manage_leads_state(self, tmp_path, capsys):
        result = _run(
            [
                "leads",
                "prepare",
                "--agent",
                "campaign-a",
                "--memory-root",
                str(tmp_path),
            ]
        )
        assert result == 0
        capsys.readouterr()

        result = _run(
            [
                "leads",
                "configure",
                "--agent",
                "campaign-a",
                "--memory-root",
                str(tmp_path),
                "--company-background-text",
                "We sell outbound infrastructure to B2B SaaS revenue teams.",
                "--icp-text",
                "VP Sales at Series A SaaS companies",
                "--icp-text",
                "Head of Revenue at 50-200 employee SaaS companies",
                "--platform",
                "apollo",
                "--platform",
                "leadiq",
                "--runtime-param",
                "search_summary_every=25",
                "--runtime-param",
                "max_tokens=4096",
            ]
        )
        assert result == 0
        configured = json.loads(capsys.readouterr().out)
        assert configured["status"] == "configured"
        assert configured["run_config"]["search_summary_every"] == 25
        assert configured["runtime_parameters"]["max_tokens"] == 4096
        assert [entry["key"] for entry in configured["run_config"]["icps"]] == [
            "vp-sales-at-series-a-saas-companies",
            "head-of-revenue-at-50-200-employee-saas-companies",
        ]
        assert configured["run_config"]["platforms"] == ["apollo", "leadiq"]

        result = _run(
            [
                "leads",
                "show",
                "--agent",
                "campaign-a",
                "--memory-root",
                str(tmp_path),
            ]
        )
        assert result == 0
        shown = json.loads(capsys.readouterr().out)
        assert shown["run_config"]["company_background"].startswith("We sell outbound")
        assert shown["runtime_parameters"]["max_tokens"] == 4096
        assert {entry["icp"]["label"] for entry in shown["icp_states"]} == {
            "VP Sales at Series A SaaS companies",
            "Head of Revenue at 50-200 employee SaaS companies",
        }


class TestNormalizeRuntimeParameters:
    def test_supported_constant_lists_expected_keys(self):
        assert "max_tokens" in SUPPORTED_LEADS_RUNTIME_PARAMETERS
        assert "search_summary_every" in SUPPORTED_LEADS_RUNTIME_PARAMETERS
        assert "prune_search_interval" in SUPPORTED_LEADS_RUNTIME_PARAMETERS

    def test_normalize_leads_runtime_parameters(self):
        result = normalize_leads_runtime_parameters(
            {
                "max_tokens": "60000",
                "reset_threshold": "0.8",
                "prune_search_interval": "10",
                "prune_token_limit": "",
                "search_summary_every": "50",
                "search_tail_size": "5",
                "max_leads_per_icp": None,
            }
        )
        assert result == {
            "max_tokens": 60000,
            "reset_threshold": 0.8,
            "prune_search_interval": 10,
            "prune_token_limit": None,
            "search_summary_every": 50,
            "search_tail_size": 5,
            "max_leads_per_icp": None,
        }

    def test_normalize_rejects_unsupported_keys(self):
        with pytest.raises(ValueError, match="Unsupported"):
            normalize_leads_runtime_parameters({"bad_key": "1"})


class TestRunCommand:
    def test_run_uses_provider_tools_and_storage_backend_factories(self, tmp_path, capsys):
        global _LAST_STORAGE_BACKEND
        _LAST_STORAGE_BACKEND = None

        _run(
            [
                "leads",
                "configure",
                "--agent",
                "campaign-b",
                "--memory-root",
                str(tmp_path),
                "--company-background-text",
                "We sell outbound infrastructure to B2B SaaS revenue teams.",
                "--icp-text",
                "VP Sales at Series A SaaS companies",
                "--platform",
                "apollo",
            ]
        )
        capsys.readouterr()

        result = _run(
            [
                "leads",
                "run",
                "--agent",
                "campaign-b",
                "--memory-root",
                str(tmp_path),
                "--model-factory",
                "tests.test_leads_cli:create_saving_model",
                "--provider-tools-factory",
                "tests.test_leads_cli:create_provider_tools",
                "--storage-backend-factory",
                "tests.test_leads_cli:create_storage_backend",
                "--max-cycles",
                "2",
            ]
        )
        assert result == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["result"]["status"] == "completed"
        assert _LAST_STORAGE_BACKEND is not None
        assert len(_LAST_STORAGE_BACKEND.started_runs) == 1
        assert len(_LAST_STORAGE_BACKEND.saved_entries) == 1
        assert len(_LAST_STORAGE_BACKEND.list_leads()) == 1

    def test_run_applies_runtime_overrides_to_agent_constructor(self, tmp_path, capsys):
        _run(
            [
                "leads",
                "configure",
                "--agent",
                "campaign-c",
                "--memory-root",
                str(tmp_path),
                "--company-background-text",
                "We sell outbound infrastructure to B2B SaaS revenue teams.",
                "--icp-text",
                "VP Sales at Series A SaaS companies",
                "--platform",
                "apollo",
                "--runtime-param",
                "search_summary_every=25",
            ]
        )
        capsys.readouterr()

        with patch("harnessiq.cli.runners.leads.LeadsAgent") as mock_agent:
            mock_result = SimpleNamespace(
                cycles_completed=1,
                pause_reason=None,
                resets=0,
                status="completed",
            )
            mock_agent.return_value.run.return_value = mock_result

            result = _run(
                [
                    "leads",
                    "run",
                    "--agent",
                    "campaign-c",
                    "--memory-root",
                    str(tmp_path),
                    "--model-factory",
                    "tests.test_leads_cli:create_saving_model",
                    "--provider-tools-factory",
                    "tests.test_leads_cli:create_provider_tools",
                    "--storage-backend-factory",
                    "tests.test_leads_cli:create_storage_backend",
                    "--runtime-param",
                    "search_summary_every=7",
                    "--runtime-param",
                    "search_tail_size=3",
                    "--runtime-param",
                    "max_tokens=1024",
                ]
            )
            assert result == 0
            kwargs = mock_agent.call_args.kwargs
            assert kwargs["search_summary_every"] == 7
            assert kwargs["search_tail_size"] == 3
            assert kwargs["max_tokens"] == 1024
            assert kwargs["tools"][0].key == "apollo.request"
            assert isinstance(kwargs["storage_backend"], _RecordingStorageBackend)
        capsys.readouterr()
