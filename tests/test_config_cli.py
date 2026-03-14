"""Tests for the credential config CLI commands."""

from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from harnessiq.cli.main import main
from harnessiq.config import DotEnvFileNotFoundError


class ConfigCLITests(unittest.TestCase):
    def test_set_and_show_manage_agent_credential_bindings(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            set_stdout = io.StringIO()
            with redirect_stdout(set_stdout):
                exit_code = main(
                    [
                        "config",
                        "set",
                        "--repo-root",
                        temp_dir,
                        "--agent",
                        "email_agent",
                        "--description",
                        "Resend-backed email credentials",
                        "--credential",
                        "api_key=RESEND_API_KEY",
                        "--credential",
                        "timeout_seconds=RESEND_TIMEOUT_SECONDS",
                    ]
                )

            self.assertEqual(exit_code, 0)
            set_payload = json.loads(set_stdout.getvalue())
            self.assertEqual(set_payload["status"], "configured")
            self.assertEqual(set_payload["binding"]["field_map"]["api_key"], "RESEND_API_KEY")

            show_stdout = io.StringIO()
            with redirect_stdout(show_stdout):
                exit_code = main(
                    [
                        "config",
                        "show",
                        "--repo-root",
                        temp_dir,
                        "--agent",
                        "email_agent",
                    ]
                )

            self.assertEqual(exit_code, 0)
            show_payload = json.loads(show_stdout.getvalue())
            self.assertEqual(show_payload["binding"]["description"], "Resend-backed email credentials")
            self.assertEqual(show_payload["binding"]["field_map"]["timeout_seconds"], "RESEND_TIMEOUT_SECONDS")

    def test_show_can_resolve_redacted_values(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            Path(temp_dir, ".env").write_text("RESEND_API_KEY=re_test_abcdef1234\n", encoding="utf-8")
            with redirect_stdout(io.StringIO()):
                main(
                    [
                        "config",
                        "set",
                        "--repo-root",
                        temp_dir,
                        "--agent",
                        "email_agent",
                        "--credential",
                        "api_key=RESEND_API_KEY",
                    ]
                )

            show_stdout = io.StringIO()
            with redirect_stdout(show_stdout):
                exit_code = main(
                    [
                        "config",
                        "show",
                        "--repo-root",
                        temp_dir,
                        "--agent",
                        "email_agent",
                        "--resolve",
                    ]
                )

            self.assertEqual(exit_code, 0)
            payload = json.loads(show_stdout.getvalue())
            self.assertIn("api_key", payload["resolved"])
            self.assertNotEqual(payload["resolved"]["api_key"], "re_test_abcdef1234")
            self.assertTrue(payload["resolved"]["api_key"].endswith("1234"))

    def test_show_with_resolve_raises_when_env_file_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with redirect_stdout(io.StringIO()):
                main(
                    [
                        "config",
                        "set",
                        "--repo-root",
                        temp_dir,
                        "--agent",
                        "email_agent",
                        "--credential",
                        "api_key=RESEND_API_KEY",
                    ]
                )

            with self.assertRaises(DotEnvFileNotFoundError):
                with redirect_stdout(io.StringIO()):
                    main(
                        [
                            "config",
                            "show",
                            "--repo-root",
                            temp_dir,
                            "--agent",
                            "email_agent",
                            "--resolve",
                        ]
                    )


if __name__ == "__main__":
    unittest.main()
