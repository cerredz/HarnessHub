from __future__ import annotations

import subprocess
from unittest.mock import patch

import pytest

from harnessiq.providers.gcloud import GcloudClient, GcloudError


def test_build_command_appends_project_flag_when_missing() -> None:
    client = GcloudClient(project_id="proj-123", region="us-central1")

    command = client.build_command(["run", "jobs", "list"])

    assert command == ["gcloud", "run", "jobs", "list", "--project=proj-123"]


def test_build_command_preserves_explicit_project_flag() -> None:
    client = GcloudClient(project_id="proj-123", region="us-central1")

    command = client.build_command(["run", "jobs", "list", "--project=override"])

    assert command == ["gcloud", "run", "jobs", "list", "--project=override"]


def test_run_returns_trimmed_stdout() -> None:
    client = GcloudClient(project_id="proj-123", region="us-central1")
    completed = subprocess.CompletedProcess(
        args=["gcloud"],
        returncode=0,
        stdout="value\n",
        stderr="",
    )

    with patch("harnessiq.providers.gcloud.client.subprocess.run", return_value=completed) as patched:
        result = client.run(["config", "get-value", "project"])

    assert result == "value"
    patched.assert_called_once()


def test_run_passes_stdin_text_to_subprocess() -> None:
    client = GcloudClient(project_id="proj-123", region="us-central1")
    completed = subprocess.CompletedProcess(
        args=["gcloud"],
        returncode=0,
        stdout="ok",
        stderr="",
    )

    with patch("harnessiq.providers.gcloud.client.subprocess.run", return_value=completed) as patched:
        client.run(["secrets", "versions", "add", "demo", "--data-file=-"], input_text="super-secret")

    assert patched.call_args.kwargs["input"] == "super-secret"
    assert patched.call_args.kwargs["text"] is True


def test_run_raises_gcloud_error_on_failure() -> None:
    client = GcloudClient(project_id="proj-123", region="us-central1")
    completed = subprocess.CompletedProcess(
        args=["gcloud"],
        returncode=1,
        stdout="",
        stderr="permission denied",
    )

    with patch("harnessiq.providers.gcloud.client.subprocess.run", return_value=completed):
        with pytest.raises(GcloudError, match="permission denied") as raised:
            client.run(["run", "jobs", "list"])

    assert raised.value.exit_code == 1
    assert "--project=proj-123" in raised.value.command


def test_run_json_decodes_json_payload() -> None:
    client = GcloudClient(project_id="proj-123", region="us-central1")
    completed = subprocess.CompletedProcess(
        args=["gcloud"],
        returncode=0,
        stdout='{"name": "demo"}',
        stderr="",
    )

    with patch("harnessiq.providers.gcloud.client.subprocess.run", return_value=completed):
        result = client.run_json(["run", "jobs", "describe", "demo"])

    assert result == {"name": "demo"}


def test_dry_run_returns_rendered_command_without_running_subprocess() -> None:
    client = GcloudClient(project_id="proj-123", region="us-central1", dry_run=True)

    with patch("harnessiq.providers.gcloud.client.subprocess.run") as patched:
        result = client.run(["run", "jobs", "list"])

    assert result == "gcloud run jobs list --project=proj-123"
    patched.assert_not_called()


def test_run_json_returns_preview_payload_in_dry_run_mode() -> None:
    client = GcloudClient(project_id="proj-123", region="us-central1", dry_run=True)

    with patch("harnessiq.providers.gcloud.client.subprocess.run") as patched:
        result = client.run_json(["run", "jobs", "list"])

    assert result == {
        "dry_run": True,
        "command": ["gcloud", "run", "jobs", "list", "--project=proj-123"],
    }
    patched.assert_not_called()
