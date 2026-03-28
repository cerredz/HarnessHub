"""Tests for the dedicated email CLI commands."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from harnessiq.cli.main import build_parser, main
from harnessiq.shared.email_campaign import EmailCampaignMemoryStore, EmailCampaignRecipient


def _run(argv: list[str]) -> int:
    return main(argv)


class EmailCliTests(unittest.TestCase):
    def test_email_subcommand_registered(self) -> None:
        parser = build_parser()
        with self.assertRaises(SystemExit) as exc_info:
            parser.parse_args(["email", "--help"])
        self.assertEqual(exc_info.exception.code, 0)

    def test_get_recipients_subcommand_registered(self) -> None:
        parser = build_parser()
        args, _ = parser.parse_known_args(["email", "get-recipients", "--agent", "test"])
        self.assertEqual(args.email_command, "get-recipients")

    def test_prepare_creates_memory_folder(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("sys.stdout.write") as mock_write:
                result = _run(["email", "prepare", "--agent", "campaign-a", "--memory-root", temp_dir])
            self.assertEqual(result, 0)
            self.assertTrue((Path(temp_dir) / "campaign-a").is_dir())
            payload = json.loads("".join(call.args[0] for call in mock_write.call_args_list))
            self.assertEqual(payload["status"], "prepared")

    def test_configure_sets_source_campaign_and_runtime_parameters(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            _run(["email", "prepare", "--agent", "campaign-a", "--memory-root", temp_dir])
            with patch("sys.stdout.write") as mock_write:
                result = _run(
                    [
                        "email",
                        "configure",
                        "--agent",
                        "campaign-a",
                        "--memory-root",
                        temp_dir,
                        "--mongodb-uri-env",
                        "MONGODB_URI",
                        "--mongodb-database",
                        "warehouse",
                        "--mongodb-collection",
                        "instagram_leads",
                        "--from-address",
                        "HarnessIQ <hello@example.com>",
                        "--subject",
                        "Hello {{name}}",
                        "--text-body-text",
                        "Hi {{email}}",
                        "--runtime-param",
                        "batch_size=25",
                    ]
                )
            self.assertEqual(result, 0)
            payload = json.loads("".join(call.args[0] for call in mock_write.call_args_list))
            self.assertEqual(payload["source_config"]["collection"], "instagram_leads")
            self.assertEqual(payload["campaign_config"]["subject"], "Hello {{name}}")
            self.assertEqual(payload["runtime_parameters"]["batch_size"], 25)

    def test_get_recipients_reads_resolved_preview(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = EmailCampaignMemoryStore(memory_path=Path(temp_dir) / "campaign-a")
            store.prepare()
            with (
                patch(
                    "harnessiq.cli.builders.email.load_email_campaign_recipients",
                    return_value=[
                        EmailCampaignRecipient(email_address="creator@example.com", name="Creator A"),
                    ],
                ),
                patch("sys.stdout.write") as mock_write,
            ):
                result = _run(["email", "get-recipients", "--agent", "campaign-a", "--memory-root", temp_dir])
            self.assertEqual(result, 0)
            payload = json.loads("".join(call.args[0] for call in mock_write.call_args_list))
            self.assertEqual(payload["count"], 1)
            self.assertEqual(payload["recipients"][0]["email_address"], "creator@example.com")

    def test_run_uses_bound_resend_credentials_and_agent_from_memory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_agent = MagicMock()
            mock_result = MagicMock()
            mock_result.cycles_completed = 1
            mock_result.pause_reason = None
            mock_result.resets = 0
            mock_result.status = "completed"
            mock_agent.run.return_value = mock_result
            mock_agent.build_ledger_outputs.return_value = {
                "delivery_records": [{"email_address": "creator@example.com"}],
                "recipient_batch": [{"email_address": "creator@example.com"}],
            }

            with (
                patch(
                    "harnessiq.cli.runners.email.HarnessCliLifecycleBuilder.resolve_bound_credentials",
                    return_value={"resend": MagicMock(api_key="re_test_123")},
                ),
                patch(
                    "harnessiq.agents.email.EmailCampaignAgent.from_memory",
                    return_value=mock_agent,
                ) as patched_from_memory,
                patch("sys.stdout.write") as mock_write,
            ):
                result = _run(
                    [
                        "email",
                        "run",
                        "--agent",
                        "campaign-a",
                        "--memory-root",
                        temp_dir,
                        "--model-factory",
                        "tests.test_platform_cli:create_static_model",
                    ]
                )

            self.assertEqual(result, 0)
            payload = json.loads("".join(call.args[0] for call in mock_write.call_args_list))
            self.assertEqual(payload["delivery_count"], 1)
            self.assertEqual(payload["recipient_batch_count"], 1)
            self.assertEqual(
                patched_from_memory.call_args.kwargs["instance_name"],
                "campaign-a",
            )


if __name__ == "__main__":
    unittest.main()
