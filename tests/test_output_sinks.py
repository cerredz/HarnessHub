"""Tests for ledger sink implementations and helpers."""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

from harnessiq.providers import GoogleSheetsClient as ProviderGoogleSheetsClient
from harnessiq.providers import LinearClient as ProviderLinearClient
from harnessiq.providers import WebhookDeliveryClient as ProviderWebhookDeliveryClient
from harnessiq.providers import extract_model_metadata as provider_extract_model_metadata
from harnessiq.providers.output_sinks import (
    GoogleSheetsClient,
    LinearClient,
    WebhookDeliveryClient,
    extract_model_metadata,
)
from harnessiq.utils import (
    ConfluenceSink,
    DiscordSink,
    GoogleSheetsSink,
    JSONLLedgerSink,
    LedgerEntry,
    LinearSink,
    NotionSink,
    ObsidianSink,
    SlackSink,
    SupabaseSink,
    build_output_sink,
    build_output_sinks,
    list_output_sink_types,
    load_ledger_entries,
    parse_sink_spec,
    register_output_sink,
    unregister_output_sink,
)


def _entry() -> LedgerEntry:
    return LedgerEntry(
        run_id="run-123",
        agent_name="linkedin_job_applier",
        started_at=datetime(2026, 3, 19, 2, 0, tzinfo=timezone.utc),
        finished_at=datetime(2026, 3, 19, 2, 5, tzinfo=timezone.utc),
        status="completed",
        reset_count=1,
        outputs={"jobs_applied": [{"company": "Stripe", "title": "Staff Engineer"}]},
        tags=["linkedin", "jobs"],
        metadata={"provider": "grok", "model_name": "grok-4-1-fast"},
    )


class OutputSinkTests(unittest.TestCase):
    def test_provider_output_sink_facades_preserve_public_imports(self) -> None:
        self.assertIs(GoogleSheetsClient, ProviderGoogleSheetsClient)
        self.assertIs(LinearClient, ProviderLinearClient)
        self.assertIs(WebhookDeliveryClient, ProviderWebhookDeliveryClient)
        self.assertIs(extract_model_metadata, provider_extract_model_metadata)
        self.assertEqual(GoogleSheetsClient.__module__, "harnessiq.providers.output_sinks")
        self.assertEqual(LinearClient.__module__, "harnessiq.providers.output_sinks")
        self.assertEqual(WebhookDeliveryClient.__module__, "harnessiq.providers.output_sinks")
        self.assertEqual(extract_model_metadata.__module__, "harnessiq.providers.output_sinks")

    def test_jsonl_sink_appends_and_entries_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir, "runs.jsonl")
            sink = JSONLLedgerSink(path=path)
            sink.on_run_complete(_entry())

            self.assertTrue(path.exists())
            loaded = load_ledger_entries(path)
            self.assertEqual(len(loaded), 1)
            self.assertEqual(loaded[0].run_id, "run-123")

    def test_obsidian_sink_writes_markdown_note(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            sink = ObsidianSink(vault_path=temp_dir, note_folder="Agent Runs")
            sink.on_run_complete(_entry())

            note_dir = Path(temp_dir, "Agent Runs")
            files = list(note_dir.glob("*.md"))
            self.assertEqual(len(files), 1)
            content = files[0].read_text(encoding="utf-8")
            self.assertIn("linkedin_job_applier", content)
            self.assertIn("jobs_applied", content)

    def test_slack_and_discord_sinks_post_webhook_payloads(self) -> None:
        client = MagicMock()

        SlackSink(webhook_url="https://slack.example", client=client).on_run_complete(_entry())
        DiscordSink(webhook_url="https://discord.example", client=client).on_run_complete(_entry())

        self.assertEqual(client.post_json.call_count, 2)
        first_payload = client.post_json.call_args_list[0].kwargs["payload"]
        second_payload = client.post_json.call_args_list[1].kwargs["payload"]
        self.assertIn("text", first_payload)
        self.assertIn("content", second_payload)

    def test_provider_backed_sinks_delegate_to_clients(self) -> None:
        notion_client = MagicMock()
        confluence_client = MagicMock()
        supabase_client = MagicMock()
        linear_client = MagicMock()
        google_sheets_client = MagicMock()
        google_sheets_client.get_values.return_value = []

        NotionSink(api_token="token", database_id="db", client=notion_client).on_run_complete(_entry())
        ConfluenceSink(base_url="https://conf.example", api_token="token", space_key="ENG", client=confluence_client).on_run_complete(_entry())
        SupabaseSink(base_url="https://supabase.example", api_key="key", client=supabase_client).on_run_complete(_entry())
        LinearSink(api_key="key", team_id="team", client=linear_client).on_run_complete(_entry())
        GoogleSheetsSink(
            client_id="cid",
            client_secret="secret",
            refresh_token="refresh",
            spreadsheet_id="sheet-123",
            client=google_sheets_client,
        ).on_run_complete(_entry())

        self.assertTrue(notion_client.create_page.called)
        self.assertTrue(confluence_client.create_page.called)
        self.assertTrue(supabase_client.insert_row.called)
        self.assertTrue(linear_client.create_issue.called)
        self.assertTrue(google_sheets_client.update_values.called)
        self.assertTrue(google_sheets_client.append_values.called)

    def test_linear_sink_can_explode_output_records(self) -> None:
        client = MagicMock()
        sink = LinearSink(
            api_key="key",
            team_id="team",
            explode_field="outputs.jobs_applied",
            client=client,
        )

        sink.on_run_complete(_entry())

        self.assertEqual(client.create_issue.call_count, 1)
        description = client.create_issue.call_args.kwargs["description"]
        self.assertIn("Stripe", description)

    def test_google_sheets_sink_can_explode_output_records(self) -> None:
        client = MagicMock()
        client.get_values.return_value = [["run_id", "agent_name", "company", "title"]]
        sink = GoogleSheetsSink(
            client_id="cid",
            client_secret="secret",
            refresh_token="refresh",
            spreadsheet_id="sheet-123",
            explode_field="outputs.jobs_applied",
            client=client,
        )

        sink.on_run_complete(_entry())

        self.assertTrue(client.update_values.called)
        updated_header = client.update_values.call_args.kwargs["values"][0]
        self.assertIn("company", updated_header)
        self.assertIn("title", updated_header)
        appended_values = client.append_values.call_args.kwargs["values"]
        self.assertEqual(len(appended_values), 1)
        header_index = {name: index for index, name in enumerate(updated_header)}
        self.assertEqual(appended_values[0][header_index["company"]], "Stripe")
        self.assertEqual(appended_values[0][header_index["title"]], "Staff Engineer")

    def test_parse_sink_spec_and_build_output_sinks_support_runtime_injection(self) -> None:
        sink_type, config = parse_sink_spec("obsidian:vault_path=C:/vault,note_folder=Runs")

        self.assertEqual(sink_type, "obsidian")
        self.assertEqual(config["note_folder"], "Runs")

        sinks = build_output_sinks(sink_specs=("slack:https://hooks.example",))
        self.assertEqual(len(sinks), 1)
        self.assertEqual(type(sinks[0]).__name__, "SlackSink")

    def test_custom_sink_types_can_be_registered_and_built(self) -> None:
        class CustomSink:
            def __init__(self, prefix: str) -> None:
                self.prefix = prefix

            def on_run_complete(self, entry: LedgerEntry) -> None:
                del entry

        sink_type = "custom_test_sink"
        register_output_sink(
            sink_type,
            lambda config: CustomSink(prefix=str(config["prefix"])),
        )
        try:
            self.assertIn(sink_type, list_output_sink_types())
            direct = build_output_sink(sink_type, {"prefix": "alpha"})
            built = build_output_sinks(sink_specs=(f"{sink_type}:prefix=beta",))

            self.assertIsInstance(direct, CustomSink)
            self.assertEqual(direct.prefix, "alpha")
            self.assertEqual(len(built), 1)
            self.assertIsInstance(built[0], CustomSink)
            self.assertEqual(built[0].prefix, "beta")
        finally:
            unregister_output_sink(sink_type)

    def test_register_output_sink_rejects_builtin_collision(self) -> None:
        with self.assertRaisesRegex(ValueError, "reserved for a built-in"):
            register_output_sink("slack", lambda config: SlackSink(webhook_url=str(config["webhook_url"])))

    def test_google_sheets_sink_is_listed_and_buildable(self) -> None:
        self.assertIn("google_sheets", list_output_sink_types())
        sink = build_output_sink(
            "google_sheets",
            {
                "client_id": "cid",
                "client_secret": "secret",
                "refresh_token": "refresh",
                "spreadsheet_id": "sheet-123",
                "include_header": "false",
            },
        )
        self.assertIsInstance(sink, GoogleSheetsSink)
        self.assertFalse(sink.include_header)


if __name__ == "__main__":
    unittest.main()
