"""Compatibility facade for the decomposed ledger subsystem."""

from __future__ import annotations

from harnessiq.utils.ledger_connections import (
    ConnectionsConfig,
    ConnectionsConfigStore,
    SinkConnection,
    default_ledger_path,
    harnessiq_home_dir,
    parse_sink_spec,
)
from harnessiq.utils.ledger_exports import (
    export_ledger_entries,
    filter_ledger_entries,
    follow_ledger,
    load_ledger_entries,
)
from harnessiq.utils.ledger_models import (
    DEFAULT_CONNECTIONS_FILENAME,
    DEFAULT_HARNESSIQ_DIRNAME,
    DEFAULT_LEDGER_FILENAME,
    LedgerEntry,
    LedgerStatus,
    OutputSink,
    new_run_id,
    parse_relative_duration,
)
from harnessiq.utils.ledger_reports import build_ledger_report, render_ledger_report
from harnessiq.utils.ledger_sinks import (
    ConfluenceSink,
    DiscordSink,
    JSONLLedgerSink,
    LinearSink,
    NotionSink,
    ObsidianSink,
    SlackSink,
    SupabaseSink,
    build_output_sinks,
    build_sink_from_connection,
    build_sink_from_spec,
)

__all__ = [
    "ConfluenceSink",
    "ConnectionsConfig",
    "ConnectionsConfigStore",
    "DEFAULT_CONNECTIONS_FILENAME",
    "DEFAULT_HARNESSIQ_DIRNAME",
    "DEFAULT_LEDGER_FILENAME",
    "DiscordSink",
    "JSONLLedgerSink",
    "LedgerEntry",
    "LedgerStatus",
    "LinearSink",
    "NotionSink",
    "ObsidianSink",
    "OutputSink",
    "SinkConnection",
    "SlackSink",
    "SupabaseSink",
    "build_ledger_report",
    "build_output_sinks",
    "build_sink_from_connection",
    "build_sink_from_spec",
    "default_ledger_path",
    "export_ledger_entries",
    "filter_ledger_entries",
    "follow_ledger",
    "harnessiq_home_dir",
    "load_ledger_entries",
    "new_run_id",
    "parse_relative_duration",
    "parse_sink_spec",
    "render_ledger_report",
]
