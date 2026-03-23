from __future__ import annotations

import io
import json
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from harnessiq.agents import AgentModelRequest, AgentModelResponse
from harnessiq.cli.main import main


class _StaticModel:
    def generate_turn(self, request: AgentModelRequest) -> AgentModelResponse:
        del request
        return AgentModelResponse(assistant_message="done", should_continue=False)


def create_static_model() -> _StaticModel:
    return _StaticModel()


def _run(argv: list[str]) -> tuple[int, dict[str, object]]:
    stdout = io.StringIO()
    with redirect_stdout(stdout):
        exit_code = main(argv)
    return exit_code, json.loads(stdout.getvalue())


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

    with patch("harnessiq.cli.platform_adapters.KnowtAgent", return_value=mock_agent) as patched_agent:
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
