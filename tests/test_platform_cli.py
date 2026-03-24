from __future__ import annotations

import io
import json
import os
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from harnessiq.agents import AgentModelRequest, AgentModelResponse
from harnessiq.cli.main import main

_LAST_PROVIDER_ENV: dict[str, str] = {}
_SPECIAL_SEARCH_BACKEND = object()


class _StaticModel:
    def generate_turn(self, request: AgentModelRequest) -> AgentModelResponse:
        del request
        return AgentModelResponse(assistant_message="done", should_continue=False)


def create_static_model() -> _StaticModel:
    return _StaticModel()


def create_static_model_recording_provider_env() -> _StaticModel:
    global _LAST_PROVIDER_ENV
    _LAST_PROVIDER_ENV = {
        "XAI_API_KEY": os.environ.get("XAI_API_KEY", ""),
    }
    return _StaticModel()


def create_empty_browser_tools() -> tuple[object, ...]:
    return ()


def create_instagram_search_backend() -> object:
    return object()


def create_special_instagram_search_backend() -> object:
    return _SPECIAL_SEARCH_BACKEND


def _run(argv: list[str]) -> tuple[int, dict[str, object]]:
    stdout = io.StringIO()
    with redirect_stdout(stdout):
        exit_code = main(argv)
    return exit_code, json.loads(stdout.getvalue())


def _clear_repo_resume_index() -> None:
    index_path = Path("memory") / "harness_profiles.json"
    if index_path.exists():
        index_path.unlink()


def test_prepare_show_and_inspect_generic_linkedin(tmp_path: Path) -> None:
    exit_code, prepared = _run(
        [
            "prepare",
            "linkedin",
            "--agent",
            "candidate-a",
            "--memory-root",
            str(tmp_path),
            "--max-tokens",
            "2048",
            "--notify-on-pause",
            "false",
            "--custom-param",
            "team=platform",
        ]
    )
    assert exit_code == 0
    assert prepared["status"] == "prepared"
    assert prepared["profile"]["runtime_parameters"]["max_tokens"] == 2048
    assert prepared["profile"]["runtime_parameters"]["notify_on_pause"] is False
    assert prepared["profile"]["custom_parameters"]["team"] == "platform"

    exit_code, shown = _run(
        [
            "show",
            "linkedin",
            "--agent",
            "candidate-a",
            "--memory-root",
            str(tmp_path),
        ]
    )
    assert exit_code == 0
    assert shown["profile"]["runtime_parameters"]["max_tokens"] == 2048
    assert shown["state"]["custom_parameters"]["team"] == "platform"

    exit_code, inspected = _run(["inspect", "linkedin"])
    assert exit_code == 0
    runtime_index = {entry["key"]: entry for entry in inspected["runtime_parameters"]}
    assert runtime_index["max_tokens"]["default"] == 80000
    assert inspected["default_memory_root"] == "memory/linkedin"
    assert inspected["provider_credential_fields"]["playwright"] == []


def test_prepare_show_and_inspect_generic_research_sweep(tmp_path: Path) -> None:
    exit_code, prepared = _run(
        [
            "prepare",
            "research-sweep",
            "--agent",
            "sweep-a",
            "--memory-root",
            str(tmp_path),
            "--max-tokens",
            "4096",
            "--reset-threshold",
            "0.8",
            "--query",
            "CRISPR therapeutic applications",
            "--allowed-serper-operations",
            "search,scholar",
        ]
    )
    assert exit_code == 0
    assert prepared["status"] == "prepared"
    assert prepared["profile"]["runtime_parameters"]["max_tokens"] == 4096
    assert prepared["profile"]["runtime_parameters"]["reset_threshold"] == 0.8
    assert prepared["profile"]["custom_parameters"]["query"] == "CRISPR therapeutic applications"

    exit_code, shown = _run(
        [
            "show",
            "research_sweep",
            "--agent",
            "sweep-a",
            "--memory-root",
            str(tmp_path),
        ]
    )
    assert exit_code == 0
    assert shown["state"]["query"] == "CRISPR therapeutic applications"
    assert shown["state"]["custom_parameters"]["allowed_serper_operations"] == "search,scholar"

    exit_code, inspected = _run(["inspect", "research-sweep"])
    assert exit_code == 0
    runtime_index = {entry["key"]: entry for entry in inspected["runtime_parameters"]}
    assert runtime_index["max_tokens"]["default"] == 80000
    assert inspected["default_memory_root"] == "memory/research_sweep"
    assert inspected["provider_credential_fields"]["serper"][0]["name"] == "api_key"


def test_generic_show_seeds_profile_from_existing_native_linkedin_state(tmp_path: Path) -> None:
    _run(
        [
            "linkedin",
            "configure",
            "--agent",
            "candidate-b",
            "--memory-root",
            str(tmp_path),
            "--job-preferences-text",
            "Staff roles.",
            "--user-profile-text",
            "Backend engineer.",
            "--runtime-param",
            "max_tokens=4096",
            "--custom-param",
            "team=infra",
        ]
    )

    exit_code, shown = _run(
        [
            "show",
            "linkedin",
            "--agent",
            "candidate-b",
            "--memory-root",
            str(tmp_path),
        ]
    )
    assert exit_code == 0
    assert shown["profile"]["runtime_parameters"]["max_tokens"] == 4096
    assert shown["profile"]["custom_parameters"]["team"] == "infra"


def test_credentials_bind_show_and_test_for_knowt(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text(
        "CREATIFY_API_ID=cid_123\nCREATIFY_API_KEY=key_456\n",
        encoding="utf-8",
    )

    exit_code, bound = _run(
        [
            "credentials",
            "bind",
            "knowt",
            "--agent",
            "channel-a",
            "--memory-root",
            str(tmp_path),
            "--env",
            "creatify.api_id=CREATIFY_API_ID",
            "--env",
            "creatify.api_key=CREATIFY_API_KEY",
        ]
    )
    assert exit_code == 0
    assert bound["status"] == "bound"
    assert bound["families"]["creatify"]["api_id"] == "CREATIFY_API_ID"

    exit_code, shown = _run(
        [
            "credentials",
            "show",
            "knowt",
            "--agent",
            "channel-a",
            "--memory-root",
            str(tmp_path),
        ]
    )
    assert exit_code == 0
    assert shown["bound"] is True
    assert shown["families"]["creatify"]["api_key"] == "CREATIFY_API_KEY"

    exit_code, tested = _run(
        [
            "credentials",
            "test",
            "knowt",
            "--agent",
            "channel-a",
            "--memory-root",
            str(tmp_path),
        ]
    )
    assert exit_code == 0
    assert tested["status"] == "resolved"
    assert tested["families"]["creatify"]["api_id"] == "cid_123"
    assert tested["families"]["creatify"]["api_key_masked"].startswith("key")


def test_run_generic_knowt_uses_bound_creatify_credentials(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text(
        "CREATIFY_API_ID=cid_123\nCREATIFY_API_KEY=key_456\n",
        encoding="utf-8",
    )
    _run(["prepare", "knowt", "--agent", "channel-b", "--memory-root", str(tmp_path)])
    _run(
        [
            "credentials",
            "bind",
            "knowt",
            "--agent",
            "channel-b",
            "--memory-root",
            str(tmp_path),
            "--env",
            "creatify.api_id=CREATIFY_API_ID",
            "--env",
            "creatify.api_key=CREATIFY_API_KEY",
        ]
    )

    mock_agent = MagicMock()
    mock_agent.run.return_value = SimpleNamespace(
        cycles_completed=1,
        pause_reason=None,
        resets=0,
        status="completed",
    )

    with patch("harnessiq.cli.adapters.knowt.KnowtAgent", return_value=mock_agent) as patched_agent:
        exit_code, payload = _run(
            [
                "run",
                "knowt",
                "--agent",
                "channel-b",
                "--memory-root",
                str(tmp_path),
                "--model-factory",
                "tests.test_platform_cli:create_static_model",
                "--max-tokens",
                "12000",
            ]
        )

    assert exit_code == 0
    assert payload["result"]["status"] == "completed"
    kwargs = patched_agent.call_args.kwargs
    assert kwargs["creatify_credentials"].api_id == "cid_123"
    assert kwargs["max_tokens"] == 12000


def test_run_generic_research_sweep_uses_bound_serper_credentials(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("SERPER_API_KEY=serper_123\n", encoding="utf-8")
    _run(
        [
            "prepare",
            "research-sweep",
            "--agent",
            "sweep-b",
            "--memory-root",
            str(tmp_path),
            "--query",
            "few-shot learning for protein folding",
        ]
    )
    _run(
        [
            "credentials",
            "bind",
            "research_sweep",
            "--agent",
            "sweep-b",
            "--memory-root",
            str(tmp_path),
            "--env",
            "serper.api_key=SERPER_API_KEY",
        ]
    )

    mock_agent = MagicMock()
    mock_agent.last_run_id = "run-456"
    mock_agent.run.return_value = SimpleNamespace(
        cycles_completed=1,
        pause_reason=None,
        resets=0,
        status="completed",
    )

    with patch(
        "harnessiq.cli.adapters.research_sweep.ResearchSweepAgent.from_memory",
        return_value=mock_agent,
    ) as patched_from_memory:
        exit_code, payload = _run(
            [
                "run",
                "research-sweep",
                "--agent",
                "sweep-b",
                "--memory-root",
                str(tmp_path),
                "--model-factory",
                "tests.test_platform_cli:create_static_model",
            ]
        )

    assert exit_code == 0
    assert payload["result"]["status"] == "completed"
    kwargs = patched_from_memory.call_args.kwargs
    assert kwargs["serper_credentials"].api_key == "serper_123"
    assert kwargs["custom_overrides"]["query"] == "few-shot learning for protein folding"


def test_run_generic_prospecting_seeds_model_factory_environment_from_local_env(tmp_path: Path) -> None:
    (tmp_path / "local.env").write_text("XAI_API_KEY=local-xai-key\n", encoding="utf-8")
    _run(["prepare", "prospecting", "--agent", "nj-dentists", "--memory-root", str(tmp_path)])

    mock_agent = MagicMock()
    mock_agent.last_run_id = "run-123"
    mock_agent.run.return_value = SimpleNamespace(
        cycles_completed=1,
        pause_reason=None,
        resets=0,
        status="completed",
    )

    with (
        patch.dict("os.environ", {}, clear=True),
        patch(
            "harnessiq.cli.adapters.prospecting.GoogleMapsProspectingAgent.from_memory",
            return_value=mock_agent,
        ),
    ):
        exit_code, payload = _run(
            [
                "run",
                "prospecting",
                "--agent",
                "nj-dentists",
                "--memory-root",
                str(tmp_path),
                "--model-factory",
                "tests.test_platform_cli:create_static_model_recording_provider_env",
                "--browser-tools-factory",
                "tests.test_platform_cli:create_empty_browser_tools",
            ]
        )

    assert exit_code == 0
    assert payload["result"]["status"] == "completed"
    assert _LAST_PROVIDER_ENV["XAI_API_KEY"] == "local-xai-key"


def test_run_generic_instagram_accepts_custom_params_and_icp_override(tmp_path: Path) -> None:
    _run(["prepare", "instagram", "--agent", "creator-a", "--memory-root", str(tmp_path)])

    mock_agent = MagicMock()
    mock_agent.get_emails.return_value = ("creator@example.com",)
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
        exit_code, payload = _run(
            [
                "run",
                "instagram",
                "--agent",
                "creator-a",
                "--memory-root",
                str(tmp_path),
                "--model-factory",
                "tests.test_platform_cli:create_static_model",
                "--search-backend-factory",
                "tests.test_platform_cli:create_instagram_search_backend",
                "--custom-param",
                'target_segment="micro-creators"',
                "--icp",
                "fitness creators",
            ]
        )

    assert exit_code == 0
    assert payload["result"]["status"] == "completed"
    assert patched_from_memory.call_args.kwargs["custom_overrides"] == {
        "icp_profiles": ["fitness creators"],
        "target_segment": "micro-creators",
    }


def test_run_resume_reuses_persisted_adapter_arguments(tmp_path: Path) -> None:
    _clear_repo_resume_index()
    _run(["prepare", "instagram", "--agent", "creator-resume", "--memory-root", str(tmp_path)])

    first_agent = MagicMock()
    first_agent.get_emails.return_value = ("creator@example.com",)
    first_agent.run.return_value = SimpleNamespace(
        cycles_completed=1,
        pause_reason=None,
        resets=0,
        status="completed",
    )

    with patch(
        "harnessiq.cli.adapters.instagram.InstagramKeywordDiscoveryAgent.from_memory",
        return_value=first_agent,
    ) as first_from_memory:
        exit_code, first_payload = _run(
            [
                "run",
                "instagram",
                "--agent",
                "creator-resume",
                "--memory-root",
                str(tmp_path),
                "--model-factory",
                "tests.test_platform_cli:create_static_model",
                "--search-backend-factory",
                "tests.test_platform_cli:create_special_instagram_search_backend",
                "--custom-param",
                'target_segment="micro-creators"',
                "--icp",
                "fitness creators",
            ]
        )

    assert exit_code == 0
    assert first_payload["profile"]["last_run"]["model_factory"] == "tests.test_platform_cli:create_static_model"
    assert (
        first_payload["profile"]["last_run"]["adapter_arguments"]["search_backend_factory"]
        == "tests.test_platform_cli:create_special_instagram_search_backend"
    )
    assert first_from_memory.call_args.kwargs["search_backend"] is _SPECIAL_SEARCH_BACKEND

    resumed_agent = MagicMock()
    resumed_agent.get_emails.return_value = ("creator@example.com",)
    resumed_agent.run.return_value = SimpleNamespace(
        cycles_completed=1,
        pause_reason=None,
        resets=0,
        status="completed",
    )

    with patch(
        "harnessiq.cli.adapters.instagram.InstagramKeywordDiscoveryAgent.from_memory",
        return_value=resumed_agent,
    ) as resumed_from_memory:
        exit_code, resumed_payload = _run(
            [
                "run",
                "instagram",
                "--resume",
                "--agent",
                "creator-resume",
                "--memory-root",
                str(tmp_path),
            ]
        )

    assert exit_code == 0
    assert resumed_payload["result"]["status"] == "completed"
    assert resumed_from_memory.call_args.kwargs["search_backend"] is _SPECIAL_SEARCH_BACKEND
    assert resumed_from_memory.call_args.kwargs["custom_overrides"] == {
        "icp_profiles": ["fitness creators"],
        "target_segment": "micro-creators",
    }


def test_top_level_resume_reuses_prior_run_by_agent_name(tmp_path: Path) -> None:
    _clear_repo_resume_index()
    _run(["prepare", "knowt", "--agent", "channel-resume", "--memory-root", str(tmp_path)])

    first_agent = MagicMock()
    first_agent.run.return_value = SimpleNamespace(
        cycles_completed=1,
        pause_reason=None,
        resets=0,
        status="completed",
    )

    with patch("harnessiq.cli.adapters.knowt.KnowtAgent", return_value=first_agent):
        _run(
            [
                "run",
                "knowt",
                "--agent",
                "channel-resume",
                "--memory-root",
                str(tmp_path),
                "--model-factory",
                "tests.test_platform_cli:create_static_model",
                "--max-tokens",
                "12000",
            ]
        )

    resumed_agent = MagicMock()
    resumed_agent.run.return_value = SimpleNamespace(
        cycles_completed=1,
        pause_reason=None,
        resets=0,
        status="completed",
    )

    def _select_knowt(prompt: str, options: list[str]) -> int:
        return next(index for index, label in enumerate(options) if "Knowt" in label)

    with (
        patch("harnessiq.cli.platform_commands.select_index", side_effect=_select_knowt) as patched_select,
        patch("harnessiq.cli.adapters.knowt.KnowtAgent", return_value=resumed_agent) as patched_agent,
    ):
        exit_code, payload = _run(["resume", "channel-resume", "--harness", "knowt"])

    assert exit_code == 0
    assert payload["result"]["status"] == "completed"
    assert patched_agent.call_args.kwargs["max_tokens"] == 12000
    assert payload["resume"]["model_factory"] == "tests.test_platform_cli:create_static_model"
    assert patched_select.call_count in {0, 1}


def test_top_level_resume_prompts_when_agent_name_is_ambiguous(tmp_path: Path) -> None:
    _clear_repo_resume_index()
    knowt_root = tmp_path / "knowt"
    instagram_root = tmp_path / "instagram"
    _run(["prepare", "knowt", "--agent", "shared-agent", "--memory-root", str(knowt_root)])
    _run(["prepare", "instagram", "--agent", "shared-agent", "--memory-root", str(instagram_root)])

    knowt_agent = MagicMock()
    knowt_agent.run.return_value = SimpleNamespace(
        cycles_completed=1,
        pause_reason=None,
        resets=0,
        status="completed",
    )
    instagram_agent = MagicMock()
    instagram_agent.get_emails.return_value = ("creator@example.com",)
    instagram_agent.run.return_value = SimpleNamespace(
        cycles_completed=1,
        pause_reason=None,
        resets=0,
        status="completed",
    )

    with patch("harnessiq.cli.adapters.knowt.KnowtAgent", return_value=knowt_agent):
        _run(
            [
                "run",
                "knowt",
                "--agent",
                "shared-agent",
                "--memory-root",
                str(knowt_root),
                "--model-factory",
                "tests.test_platform_cli:create_static_model",
            ]
        )

    with patch(
        "harnessiq.cli.adapters.instagram.InstagramKeywordDiscoveryAgent.from_memory",
        return_value=instagram_agent,
    ):
        _run(
            [
                "run",
                "instagram",
                "--agent",
                "shared-agent",
                "--memory-root",
                str(instagram_root),
                "--model-factory",
                "tests.test_platform_cli:create_static_model",
                "--search-backend-factory",
                "tests.test_platform_cli:create_special_instagram_search_backend",
            ]
        )

    resumed_agent = MagicMock()
    resumed_agent.get_emails.return_value = ("creator@example.com",)
    resumed_agent.run.return_value = SimpleNamespace(
        cycles_completed=1,
        pause_reason=None,
        resets=0,
        status="completed",
    )

    def _select_instagram(prompt: str, options: list[str]) -> int:
        assert "shared-agent" in prompt
        return next(index for index, label in enumerate(options) if "Instagram" in label)

    with (
        patch("harnessiq.cli.platform_commands.select_index", side_effect=_select_instagram) as patched_select,
        patch(
            "harnessiq.cli.adapters.instagram.InstagramKeywordDiscoveryAgent.from_memory",
            return_value=resumed_agent,
        ) as patched_instagram,
    ):
        exit_code, payload = _run(["resume", "shared-agent"])

    assert exit_code == 0
    assert payload["harness"] == "instagram"
    assert payload["result"]["status"] == "completed"
    assert patched_select.call_count == 1
    assert patched_instagram.call_args.kwargs["search_backend"] is _SPECIAL_SEARCH_BACKEND
