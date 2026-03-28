from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from harnessiq.agents import AgentModelRequest, AgentModelResponse
from harnessiq.cli.common import build_runtime_config
from harnessiq.cli.main import main


class _StaticModel:
    def generate_turn(self, request: AgentModelRequest) -> AgentModelResponse:
        del request
        return AgentModelResponse(assistant_message="done", should_continue=False)


def create_static_model() -> _StaticModel:
    return _StaticModel()


def create_instagram_search_backend() -> object:
    return object()


def _run(argv: list[str]) -> int:
    return main(argv)


def test_build_runtime_config_applies_policy_without_sink_overrides() -> None:
    runtime_config = build_runtime_config(
        approval_policy="on-request",
        allowed_tools=("filesystem.* , text.normalize_whitespace",),
    )

    assert runtime_config.approval_policy == "on-request"
    assert runtime_config.allowed_tools == ("filesystem.*", "text.normalize_whitespace")


def test_build_runtime_config_populates_dynamic_tool_selection() -> None:
    runtime_config = build_runtime_config(
        dynamic_tools_enabled=True,
        dynamic_tool_candidates=("filesystem.*, context.select.checkpoint", "text.normalize_whitespace"),
        dynamic_tool_top_k=3,
        dynamic_tool_embedding_model="openai:text-embedding-3-large",
    )

    assert runtime_config.tool_selection.enabled is True
    assert runtime_config.tool_selection.candidate_tool_keys == (
        "filesystem.*",
        "context.select.checkpoint",
        "text.normalize_whitespace",
    )
    assert runtime_config.tool_selection.top_k == 3
    assert runtime_config.tool_selection.embedding_model == "openai:text-embedding-3-large"


def test_platform_run_passes_policy_to_runtime_config(tmp_path, capsys) -> None:
    _run(["prepare", "instagram", "--agent", "creator-a", "--memory-root", str(tmp_path)])
    capsys.readouterr()

    mock_agent = MagicMock()
    mock_agent.get_emails.return_value = ()
    mock_agent.run.return_value = SimpleNamespace(
        cycles_completed=1,
        pause_reason=None,
        resets=0,
        status="completed",
    )

    with patch(
        "harnessiq.cli.adapters.instagram.InstagramKeywordDiscoveryAgent.from_memory",
        return_value=mock_agent,
    ) as patched_from_memory:
        result = _run(
            [
                "run",
                "instagram",
                "--agent",
                "creator-a",
                "--memory-root",
                str(tmp_path),
                "--model-factory",
                "tests.test_cli_policy_options:create_static_model",
                "--search-backend-factory",
                "tests.test_cli_policy_options:create_instagram_search_backend",
                "--approval",
                "on-request",
                "--allowed-tools",
                "filesystem.*,context.select.checkpoint",
            ]
        )

    assert result == 0
    runtime_config = patched_from_memory.call_args.kwargs["runtime_config"]
    assert runtime_config.approval_policy == "on-request"
    assert runtime_config.allowed_tools == ("filesystem.*", "context.select.checkpoint")
    payload = json.loads(capsys.readouterr().out)
    assert payload["result"]["status"] == "completed"


def test_instagram_run_passes_policy_to_runtime_config(tmp_path, capsys) -> None:
    _run(["instagram", "prepare", "--agent", "creator-b", "--memory-root", str(tmp_path)])
    capsys.readouterr()

    mock_agent = MagicMock()
    mock_agent.get_emails.return_value = ()
    mock_agent.run.return_value = SimpleNamespace(
        cycles_completed=1,
        pause_reason=None,
        resets=0,
        status="completed",
    )

    with (
        patch(
            "harnessiq.cli.runners.instagram.load_factory",
            return_value=lambda: object(),
        ),
        patch(
            "harnessiq.agents.instagram.InstagramKeywordDiscoveryAgent.from_memory",
            return_value=mock_agent,
        ) as patched_from_memory,
    ):
        result = _run(
            [
                "instagram",
                "run",
                "--agent",
                "creator-b",
                "--memory-root",
                str(tmp_path),
                "--model-factory",
                "tests.test_cli_policy_options:create_static_model",
                "--approval",
                "on-request",
                "--allowed-tools",
                "filesystem.*",
                "--allowed-tools",
                "context.select.checkpoint,text.normalize_whitespace",
            ]
        )

    assert result == 0
    runtime_config = patched_from_memory.call_args.kwargs["runtime_config"]
    assert runtime_config.approval_policy == "on-request"
    assert runtime_config.allowed_tools == (
        "filesystem.*",
        "context.select.checkpoint",
        "text.normalize_whitespace",
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["result"]["status"] == "completed"


def test_instagram_run_passes_dynamic_tool_selection_to_runtime_config(tmp_path, capsys) -> None:
    _run(["instagram", "prepare", "--agent", "creator-c", "--memory-root", str(tmp_path)])
    capsys.readouterr()

    mock_agent = MagicMock()
    mock_agent.get_emails.return_value = ()
    mock_agent.run.return_value = SimpleNamespace(
        cycles_completed=1,
        pause_reason=None,
        resets=0,
        status="completed",
    )

    with (
        patch(
            "harnessiq.cli.runners.instagram.load_factory",
            return_value=lambda: object(),
        ),
        patch(
            "harnessiq.agents.instagram.InstagramKeywordDiscoveryAgent.from_memory",
            return_value=mock_agent,
        ) as patched_from_memory,
    ):
        result = _run(
            [
                "instagram",
                "run",
                "--agent",
                "creator-c",
                "--memory-root",
                str(tmp_path),
                "--model-factory",
                "tests.test_cli_policy_options:create_static_model",
                "--dynamic-tools",
                "--dynamic-tool-candidates",
                "filesystem.*,context.select.checkpoint",
                "--dynamic-tool-candidates",
                "text.normalize_whitespace",
                "--dynamic-tool-top-k",
                "2",
                "--dynamic-tool-embedding-model",
                "openai:text-embedding-3-large",
            ]
        )

    assert result == 0
    runtime_config = patched_from_memory.call_args.kwargs["runtime_config"]
    assert runtime_config.tool_selection.enabled is True
    assert runtime_config.tool_selection.candidate_tool_keys == (
        "filesystem.*",
        "context.select.checkpoint",
        "text.normalize_whitespace",
    )
    assert runtime_config.tool_selection.top_k == 2
    assert runtime_config.tool_selection.embedding_model == "openai:text-embedding-3-large"
    payload = json.loads(capsys.readouterr().out)
    assert payload["result"]["status"] == "completed"


def test_leads_run_passes_policy_to_runtime_config(tmp_path, capsys) -> None:
    _run(["leads", "prepare", "--agent", "campaign-a", "--memory-root", str(tmp_path)])
    capsys.readouterr()
    _run(
        [
            "leads",
            "configure",
            "--agent",
            "campaign-a",
            "--memory-root",
            str(tmp_path),
            "--company-background-text",
            "We sell outbound infrastructure.",
            "--icp-text",
            "VP Sales at Series A SaaS companies",
            "--platform",
            "apollo",
        ]
    )
    capsys.readouterr()

    with patch("harnessiq.cli.runners.leads.LeadsAgent") as mock_agent:
        mock_agent.return_value.run.return_value = SimpleNamespace(
            cycles_completed=1,
            pause_reason=None,
            resets=0,
            status="completed",
        )

        result = _run(
            [
                "leads",
                "run",
                "--agent",
                "campaign-a",
                "--memory-root",
                str(tmp_path),
                "--model-factory",
                "tests.test_cli_policy_options:create_static_model",
                "--approval",
                "on-request",
                "--allowed-tools",
                "apollo.request,filesystem.*",
            ]
        )

    assert result == 0
    runtime_config = mock_agent.call_args.kwargs["runtime_config"]
    assert runtime_config.approval_policy == "on-request"
    assert runtime_config.allowed_tools == ("apollo.request", "filesystem.*")
    payload = json.loads(capsys.readouterr().out)
    assert payload["result"]["status"] == "completed"
