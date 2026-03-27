from __future__ import annotations

import io
from contextlib import redirect_stdout

import pytest

from harnessiq.cli.main import build_parser, main


def test_gcloud_top_level_command_is_registered() -> None:
    parser = build_parser()
    args, _ = parser.parse_known_args(["gcloud", "health"])

    assert args.command == "gcloud"
    assert args.gcloud_command == "health"


def test_gcloud_credentials_subcommands_are_registered() -> None:
    parser = build_parser()
    args, _ = parser.parse_known_args(["gcloud", "credentials", "sync"])

    assert args.command == "gcloud"
    assert args.gcloud_command == "credentials"
    assert args.gcloud_credentials_command == "sync"


def test_gcloud_help_path_exits_cleanly() -> None:
    parser = build_parser()
    with pytest.raises(SystemExit) as exc_info:
        parser.parse_args(["gcloud", "--help"])
    assert exc_info.value.code == 0


def test_gcloud_main_prints_help_until_handlers_are_implemented() -> None:
    stdout = io.StringIO()
    with redirect_stdout(stdout):
        exit_code = main(["gcloud"])

    assert exit_code == 0
    assert "Manage Google Cloud deployment configuration and operations" in stdout.getvalue()
