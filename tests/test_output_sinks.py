"""Tests for ledger sink implementations and helpers."""

from __future__ import annotations

import json
import tempfile
import unittest
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

from harnessiq.providers import GoogleSheetsClient as ProviderGoogleSheetsClient
from harnessiq.providers import LinearClient as ProviderLinearClient
from harnessiq.providers import MongoDBClient as ProviderMongoDBClient
from harnessiq.providers import WebhookDeliveryClient as ProviderWebhookDeliveryClient
from harnessiq.providers import extract_model_metadata as provider_extract_model_metadata
from harnessiq.interfaces import GoogleSheetsSinkClient, MongoCollectionSinkClient, WebhookSinkClient
from harnessiq.providers.output_sinks import (
    GoogleSheetsClient,
    LinearClient,
    MongoDBClient,
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
    MongoDBSink,
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


class _FakeWebhookClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def post_json(
        self,
        *,
        url: str,
        payload: Mapping[str, object],
        headers: Mapping[str, str] | None = None,
        timeout_seconds: float = 30.0,
    ) -> None:
        self.calls.append(
            {
                "url": url,
                "payload": dict(payload),
                "headers": dict(headers) if headers is not None else None,
                "timeout_seconds": timeout_seconds,
            }
        )


class _FakeNotionClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def create_page(
        self,
        *,
        database_id: str,
        properties: Mapping[str, object],
        children: list[dict[str, object]] | None = None,
    ) -> None:
        self.calls.append(
            {
                "database_id": database_id,
                "properties": dict(properties),
                "children": list(children) if children is not None else None,
            }
        )


class _FakeConfluenceClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def create_page(
        self,
        *,
        space_key: str,
        title: str,
        body_storage: str,
        parent_page_id: str | None = None,
    ) -> None:
        self.calls.append(
            {
                "space_key": space_key,
                "title": title,
                "body_storage": body_storage,
                "parent_page_id": parent_page_id,
            }
        )


class _FakeSupabaseClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def insert_row(self, *, table: str, row: Mapping[str, object], schema: str = "public") -> None:
        self.calls.append({"table": table, "row": dict(row), "schema": schema})


class _FakeLinearClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def create_issue(
        self,
        *,
        team_id: str,
        title: str,
        description: str | None = None,
        priority: int | None = None,
    ) -> None:
        self.calls.append(
            {
                "team_id": team_id,
                "title": title,
                "description": description,
                "priority": priority,
            }
        )


class _FakeGoogleSheetsClient:
    def __init__(self, existing_values: list[list[object]] | None = None) -> None:
        self.existing_values = existing_values or []
        self.updated_rows: list[dict[str, object]] = []
        self.appended_rows: list[dict[str, object]] = []

    def get_values(self, *, spreadsheet_id: str, range_name: str) -> list[list[object]]:
        return [list(row) for row in self.existing_values]

    def update_values(
        self,
        *,
        spreadsheet_id: str,
        range_name: str,
        values: list[list[object]],
        value_input_option: str = "RAW",
    ) -> None:
        self.updated_rows.append(
            {
                "spreadsheet_id": spreadsheet_id,
                "range_name": range_name,
                "values": [list(row) for row in values],
                "value_input_option": value_input_option,
            }
        )

    def append_values(
        self,
        *,
        spreadsheet_id: str,
        range_name: str,
        values: list[list[object]],
        value_input_option: str = "RAW",
        insert_data_option: str = "INSERT_ROWS",
    ) -> None:
        self.appended_rows.append(
            {
                "spreadsheet_id": spreadsheet_id,
                "range_name": range_name,
                "values": [list(row) for row in values],
                "value_input_option": value_input_option,
                "insert_data_option": insert_data_option,
            }
        )


class _FakeMongoCollectionClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def insert_documents(self, *, documents: Sequence[Mapping[str, object]]) -> None:
        self.calls.append({"documents": [dict(document) for document in documents]})


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


def _instagram_entry() -> LedgerEntry:
    return LedgerEntry(
        run_id="run-instagram",
        agent_name="instagram_keyword_discovery",
        started_at=datetime(2026, 3, 19, 3, 0, tzinfo=timezone.utc),
        finished_at=datetime(2026, 3, 19, 3, 5, tzinfo=timezone.utc),
        status="completed",
        reset_count=0,
        outputs={
            "emails": ["creator@example.com", "team@example.com"],
            "leads": [
                {
                    "emails": ["creator@example.com", "team@example.com"],
                    "found_at": "2026-03-19T03:01:00Z",
                    "snippet": "creator@example.com team@example.com",
                    "source_keyword": "fitness creator",
                    "source_url": "https://www.instagram.com/creator-a/",
                    "title": "Creator A",
                }
            ],
            "search_history": [],
        },
        tags=["instagram"],
        metadata={"provider": "grok", "model_name": "grok-4-1-fast"},
    )


class OutputSinkTests(unittest.TestCase):
    def test_provider_output_sink_facades_preserve_public_imports(self) -> None:
        self.assertIs(GoogleSheetsClient, ProviderGoogleSheetsClient)
        self.assertIs(LinearClient, ProviderLinearClient)
        self.assertIs(MongoDBClient, ProviderMongoDBClient)
        self.assertIs(WebhookDeliveryClient, ProviderWebhookDeliveryClient)
        self.assertIs(extract_model_metadata, provider_extract_model_metadata)
        self.assertEqual(GoogleSheetsClient.__module__, "harnessiq.providers.output_sinks")
        self.assertEqual(LinearClient.__module__, "harnessiq.providers.output_sinks")
        self.assertEqual(MongoDBClient.__module__, "harnessiq.providers.output_sinks")
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
        notion_client = _FakeNotionClient()
        confluence_client = _FakeConfluenceClient()
        supabase_client = _FakeSupabaseClient()
        linear_client = _FakeLinearClient()
        mongo_client = _FakeMongoCollectionClient()
        google_sheets_client = _FakeGoogleSheetsClient()

        self.assertIsInstance(mongo_client, MongoCollectionSinkClient)
        self.assertIsInstance(google_sheets_client, GoogleSheetsSinkClient)

        NotionSink(api_token="token", database_id="db", client=notion_client).on_run_complete(_entry())
        ConfluenceSink(base_url="https://conf.example", api_token="token", space_key="ENG", client=confluence_client).on_run_complete(_entry())
        SupabaseSink(base_url="https://supabase.example", api_key="key", client=supabase_client).on_run_complete(_entry())
        MongoDBSink(
            connection_uri="mongodb://localhost:27017",
            database="harnessiq",
            collection="agent_runs",
            client=mongo_client,
        ).on_run_complete(_entry())
        LinearSink(api_key="key", team_id="team", client=linear_client).on_run_complete(_entry())
        GoogleSheetsSink(
            client_id="cid",
            client_secret="secret",
            refresh_token="refresh",
            spreadsheet_id="sheet-123",
            client=google_sheets_client,
        ).on_run_complete(_entry())

        self.assertEqual(len(notion_client.calls), 1)
        self.assertEqual(len(confluence_client.calls), 1)
        self.assertEqual(len(supabase_client.calls), 1)
        self.assertEqual(len(mongo_client.calls), 1)
        self.assertEqual(len(linear_client.calls), 1)
        self.assertEqual(len(google_sheets_client.updated_rows), 1)
        self.assertEqual(len(google_sheets_client.appended_rows), 1)

    def test_slack_and_discord_sinks_accept_protocol_compatible_webhook_clients(self) -> None:
        client = _FakeWebhookClient()
        self.assertIsInstance(client, WebhookSinkClient)

        SlackSink(webhook_url="https://slack.example", client=client).on_run_complete(_entry())
        DiscordSink(webhook_url="https://discord.example", client=client).on_run_complete(_entry())

        self.assertEqual(len(client.calls), 2)
        self.assertIn("text", client.calls[0]["payload"])
        self.assertIn("content", client.calls[1]["payload"])

    def test_mongodb_client_inserts_documents_and_closes_managed_client(self) -> None:
        collection = MagicMock()
        database = MagicMock()
        database.__getitem__.return_value = collection
        managed_client = MagicMock()
        managed_client.__getitem__.return_value = database

        client = MongoDBClient(
            connection_uri="mongodb://localhost:27017",
            database="harnessiq",
            collection="agent_runs",
            mongo_client_factory=lambda *args, **kwargs: managed_client,
        )

        client.insert_documents(documents=[{"run_id": "run-1"}, {"run_id": "run-2"}])

        self.assertTrue(collection.insert_many.called)
        self.assertTrue(managed_client.close.called)

    def test_mongodb_client_uses_insert_one_for_single_document(self) -> None:
        collection = MagicMock()
        client = MongoDBClient(
            connection_uri="mongodb://localhost:27017",
            database="harnessiq",
            collection="agent_runs",
            collection_handle=collection,
        )

        client.insert_documents(documents=[{"run_id": "run-1"}])

        self.assertTrue(collection.insert_one.called)
        self.assertFalse(collection.insert_many.called)

    def test_mongodb_sink_persists_full_entry_without_explode_field(self) -> None:
        client = MagicMock()
        sink = MongoDBSink(
            connection_uri="mongodb://localhost:27017",
            database="harnessiq",
            collection="agent_runs",
            client=client,
        )

        sink.on_run_complete(_entry())

        documents = client.insert_documents.call_args.kwargs["documents"]
        self.assertEqual(len(documents), 1)
        self.assertEqual(documents[0]["run_id"], "run-123")
        self.assertEqual(documents[0]["agent_name"], "linkedin_job_applier")
        self.assertNotIn("record", documents[0])

    def test_mongodb_sink_can_explode_output_records(self) -> None:
        client = MagicMock()
        sink = MongoDBSink(
            connection_uri="mongodb://localhost:27017",
            database="harnessiq",
            collection="agent_runs",
            explode_field="outputs.jobs_applied",
            client=client,
        )

        sink.on_run_complete(_entry())

        documents = client.insert_documents.call_args.kwargs["documents"]
        self.assertEqual(len(documents), 1)
        self.assertEqual(documents[0]["explode_field"], "outputs.jobs_applied")
        self.assertEqual(documents[0]["record"]["company"], "Stripe")

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

    def test_google_sheets_sink_renders_instagram_leads_as_simple_rows(self) -> None:
        client = MagicMock()
        client.get_values.return_value = [["run_id", "agent_name", "status", "source_url", "emails"]]
        sink = GoogleSheetsSink(
            client_id="cid",
            client_secret="secret",
            refresh_token="refresh",
            spreadsheet_id="sheet-123",
            explode_field="outputs.leads",
            client=client,
        )

        sink.on_run_complete(_instagram_entry())

        updated_header = client.update_values.call_args.kwargs["values"][0]
        self.assertEqual(updated_header, ["name", "instagram_url", "email_address", "username"])
        appended_values = client.append_values.call_args.kwargs["values"]
        self.assertEqual(len(appended_values), 2)
        self.assertNotIn("run_id", updated_header)
        header_index = {name: index for index, name in enumerate(updated_header)}
        self.assertEqual(appended_values[0][header_index["name"]], "Creator A")
        self.assertEqual(
            appended_values[0][header_index["instagram_url"]],
            "https://www.instagram.com/creator-a/",
        )
        self.assertEqual(appended_values[0][header_index["email_address"]], "creator@example.com")
        self.assertEqual(appended_values[0][header_index["username"]], "creator-a")
        self.assertEqual(appended_values[1][header_index["email_address"]], "team@example.com")

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

    def test_mongodb_sink_is_listed_and_buildable(self) -> None:
        self.assertIn("mongodb", list_output_sink_types())
        sink = build_output_sink(
            "mongodb",
            {
                "connection_uri": "mongodb://localhost:27017",
                "database": "harnessiq",
                "collection": "agent_runs",
                "explode_field": "outputs.jobs_applied",
            },
        )
        self.assertIsInstance(sink, MongoDBSink)
        self.assertEqual(sink.collection, "agent_runs")
        self.assertEqual(sink.explode_field, "outputs.jobs_applied")


if __name__ == "__main__":
    unittest.main()
