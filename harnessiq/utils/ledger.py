"""Framework-level audit ledger models, sinks, connection config, and query helpers."""

from __future__ import annotations

import csv
import html
import json
import os
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from io import StringIO
from pathlib import Path
from typing import Any, Literal, Mapping, Protocol, Sequence
from uuid import uuid4

from harnessiq.providers.output_sinks import (
    ConfluenceClient,
    LinearClient,
    NotionClient,
    SupabaseClient,
    WebhookDeliveryClient,
)

DEFAULT_HARNESSIQ_DIRNAME = ".harnessiq"
DEFAULT_LEDGER_FILENAME = "runs.jsonl"
DEFAULT_CONNECTIONS_FILENAME = "connections.json"

LedgerStatus = Literal["completed", "paused", "max_cycles_reached", "error"]


@dataclass(frozen=True, slots=True)
class LedgerEntry:
    """Universal audit record emitted after agent runs finish."""

    run_id: str
    agent_name: str
    started_at: datetime
    finished_at: datetime
    status: LedgerStatus
    reset_count: int
    outputs: dict[str, Any]
    tags: list[str]
    metadata: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "agent_name": self.agent_name,
            "finished_at": _isoformat_z(self.finished_at),
            "metadata": _json_safe(self.metadata),
            "outputs": _json_safe(self.outputs),
            "reset_count": self.reset_count,
            "run_id": self.run_id,
            "started_at": _isoformat_z(self.started_at),
            "status": self.status,
            "tags": list(self.tags),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "LedgerEntry":
        return cls(
            run_id=str(payload["run_id"]),
            agent_name=str(payload["agent_name"]),
            started_at=_parse_datetime(str(payload["started_at"])),
            finished_at=_parse_datetime(str(payload["finished_at"])),
            status=str(payload["status"]),  # type: ignore[arg-type]
            reset_count=int(payload.get("reset_count", 0)),
            outputs=dict(payload.get("outputs", {})),
            tags=[str(tag) for tag in payload.get("tags", [])],
            metadata=dict(payload.get("metadata", {})),
        )


class OutputSink(Protocol):
    """Write-only post-run sink contract."""

    def on_run_complete(self, entry: LedgerEntry) -> None:
        """Persist or export a completed ledger entry."""


@dataclass(slots=True)
class JSONLLedgerSink:
    """Append-only JSONL ledger sink."""

    path: Path | str | None = None
    rotate: bool = False
    max_size_mb: int | None = None

    def __post_init__(self) -> None:
        resolved = Path(self.path).expanduser() if self.path is not None else default_ledger_path()
        self.path = resolved

    def on_run_complete(self, entry: LedgerEntry) -> None:
        path = Path(self.path)
        path.parent.mkdir(parents=True, exist_ok=True)
        if self.rotate and self.max_size_mb is not None and path.exists():
            max_bytes = self.max_size_mb * 1024 * 1024
            if path.stat().st_size >= max_bytes:
                timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                rotated = path.with_name(f"{path.stem}-{timestamp}{path.suffix}")
                path.rename(rotated)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry.as_dict(), sort_keys=True))
            handle.write("\n")


@dataclass(slots=True)
class ObsidianSink:
    """Write one Markdown note per run into an Obsidian-style vault."""

    vault_path: Path | str
    note_folder: str = "Agent Runs"
    filename_template: str = "{date}-{agent_name}-{run_id}.md"

    def __post_init__(self) -> None:
        self.vault_path = Path(self.vault_path).expanduser()

    def on_run_complete(self, entry: LedgerEntry) -> None:
        note_dir = self.vault_path / self.note_folder
        note_dir.mkdir(parents=True, exist_ok=True)
        filename = self.filename_template.format(
            date=entry.finished_at.strftime("%Y-%m-%d"),
            agent_name=_safe_slug(entry.agent_name),
            run_id=entry.run_id,
        )
        note_path = note_dir / filename
        note_path.write_text(_render_obsidian_note(entry), encoding="utf-8")


@dataclass(slots=True)
class SlackSink:
    """Post a completion summary to a Slack incoming webhook."""

    webhook_url: str
    client: WebhookDeliveryClient | None = None

    def on_run_complete(self, entry: LedgerEntry) -> None:
        client = self.client or WebhookDeliveryClient()
        client.post_json(url=self.webhook_url, payload={"text": _render_notification_text(entry)})


@dataclass(slots=True)
class DiscordSink:
    """Post a completion summary to a Discord webhook."""

    webhook_url: str
    client: WebhookDeliveryClient | None = None

    def on_run_complete(self, entry: LedgerEntry) -> None:
        client = self.client or WebhookDeliveryClient()
        client.post_json(url=self.webhook_url, payload={"content": _render_notification_text(entry)})


@dataclass(slots=True)
class NotionSink:
    """Append a run as a page in a Notion database."""

    api_token: str
    database_id: str
    property_mapping: dict[str, dict[str, Any]] | None = None
    client: NotionClient | None = None

    def on_run_complete(self, entry: LedgerEntry) -> None:
        client = self.client or NotionClient(api_token=self.api_token)
        client.create_page(
            database_id=self.database_id,
            properties=_build_notion_properties(entry, self.property_mapping),
            children=_build_notion_children(entry),
        )


@dataclass(slots=True)
class ConfluenceSink:
    """Append a run as a Confluence page."""

    base_url: str
    api_token: str
    space_key: str
    parent_page_id: str | None = None
    title_template: str = "{agent_name} Run {date} {run_id}"
    client: ConfluenceClient | None = None

    def on_run_complete(self, entry: LedgerEntry) -> None:
        client = self.client or ConfluenceClient(base_url=self.base_url, api_token=self.api_token)
        client.create_page(
            space_key=self.space_key,
            title=self.title_template.format(
                agent_name=entry.agent_name,
                date=entry.finished_at.strftime("%Y-%m-%d"),
                run_id=entry.run_id,
            ),
            body_storage=_render_confluence_body(entry),
            parent_page_id=self.parent_page_id,
        )


@dataclass(slots=True)
class SupabaseSink:
    """Insert a run row into a Supabase table."""

    base_url: str
    api_key: str
    table: str = "agent_runs"
    schema: str = "public"
    client: SupabaseClient | None = None

    def on_run_complete(self, entry: LedgerEntry) -> None:
        client = self.client or SupabaseClient(base_url=self.base_url, api_key=self.api_key)
        client.insert_row(table=self.table, schema=self.schema, row=entry.as_dict())


@dataclass(slots=True)
class LinearSink:
    """Create one or more Linear issues from a run."""

    api_key: str
    team_id: str
    explode_field: str | None = None
    title_template: str = "[{agent_name}] {status} {run_id}"
    client: LinearClient | None = None

    def on_run_complete(self, entry: LedgerEntry) -> None:
        client = self.client or LinearClient(api_key=self.api_key)
        records = _explode_entry(entry, self.explode_field)
        if not records:
            records = [{"record": None}]
        for item in records:
            record = item.get("record")
            title = _render_linear_title(entry, record, self.title_template)
            description = _render_linear_description(entry, record)
            client.create_issue(team_id=self.team_id, title=title, description=description)


@dataclass(frozen=True, slots=True)
class SinkConnection:
    """Persisted global sink connection entry."""

    name: str
    sink_type: str
    config: dict[str, Any]
    enabled: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "config", dict(self.config))
        object.__setattr__(self, "name", self.name.strip())
        object.__setattr__(self, "sink_type", self.sink_type.strip())
        if not self.name:
            raise ValueError("Connection name must not be blank.")
        if not self.sink_type:
            raise ValueError("Connection sink_type must not be blank.")

    def as_dict(self) -> dict[str, Any]:
        return {
            "config": _json_safe(self.config),
            "enabled": self.enabled,
            "name": self.name,
            "sink_type": self.sink_type,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SinkConnection":
        return cls(
            name=str(payload["name"]),
            sink_type=str(payload["sink_type"]),
            config=dict(payload.get("config", {})),
            enabled=bool(payload.get("enabled", True)),
        )


@dataclass(frozen=True, slots=True)
class ConnectionsConfig:
    """Collection of persisted sink connections."""

    connections: tuple[SinkConnection, ...] = ()

    def __post_init__(self) -> None:
        normalized = tuple(self.connections)
        unique_names: set[str] = set()
        for connection in normalized:
            if connection.name in unique_names:
                raise ValueError(f"Duplicate sink connection '{connection.name}'.")
            unique_names.add(connection.name)
        object.__setattr__(self, "connections", normalized)

    def as_dict(self) -> dict[str, Any]:
        return {"connections": [connection.as_dict() for connection in self.connections]}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ConnectionsConfig":
        raw_connections = payload.get("connections", [])
        if not isinstance(raw_connections, list):
            raise ValueError("Connections config must define 'connections' as a list.")
        return cls(connections=tuple(SinkConnection.from_dict(item) for item in raw_connections))

    def upsert(self, connection: SinkConnection) -> "ConnectionsConfig":
        indexed = {item.name: item for item in self.connections}
        indexed[connection.name] = connection
        return ConnectionsConfig(connections=tuple(indexed[name] for name in sorted(indexed)))

    def remove(self, name: str) -> "ConnectionsConfig":
        normalized = name.strip()
        indexed = {item.name: item for item in self.connections}
        indexed.pop(normalized, None)
        return ConnectionsConfig(connections=tuple(indexed[key] for key in sorted(indexed)))

    def enabled_connections(self) -> tuple[SinkConnection, ...]:
        return tuple(connection for connection in self.connections if connection.enabled)


@dataclass(slots=True)
class ConnectionsConfigStore:
    """Persist global sink connections under the HarnessIQ home directory."""

    home_dir: Path | str | None = None

    def __post_init__(self) -> None:
        self.home_dir = harnessiq_home_dir(self.home_dir)

    @property
    def config_path(self) -> Path:
        return Path(self.home_dir) / DEFAULT_CONNECTIONS_FILENAME

    def load(self) -> ConnectionsConfig:
        path = self.config_path
        if not path.exists():
            return ConnectionsConfig()
        raw = path.read_text(encoding="utf-8").strip()
        if not raw:
            return ConnectionsConfig()
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise ValueError("Connections config file must contain a JSON object.")
        return ConnectionsConfig.from_dict(payload)

    def save(self, config: ConnectionsConfig) -> Path:
        path = self.config_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(config.as_dict(), indent=2, sort_keys=True), encoding="utf-8")
        return path

    def upsert(self, connection: SinkConnection) -> Path:
        return self.save(self.load().upsert(connection))

    def remove(self, name: str) -> Path:
        return self.save(self.load().remove(name))


def harnessiq_home_dir(home_dir: Path | str | None = None) -> Path:
    if home_dir is not None:
        return Path(home_dir).expanduser().resolve()
    override = os.environ.get("HARNESSIQ_HOME", "").strip()
    if override:
        return Path(override).expanduser().resolve()
    preferred = (Path.home() / DEFAULT_HARNESSIQ_DIRNAME).expanduser().resolve()
    try:
        preferred.mkdir(parents=True, exist_ok=True)
        return preferred
    except OSError:
        fallback = (Path.cwd() / DEFAULT_HARNESSIQ_DIRNAME).resolve()
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


def default_ledger_path(home_dir: Path | str | None = None) -> Path:
    return harnessiq_home_dir(home_dir) / DEFAULT_LEDGER_FILENAME


def new_run_id() -> str:
    return str(uuid4())


def load_ledger_entries(path: Path | str | None = None) -> list[LedgerEntry]:
    ledger_path = Path(path).expanduser() if path is not None else default_ledger_path()
    if not ledger_path.exists():
        return []
    entries: list[LedgerEntry] = []
    for raw_line in ledger_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        payload = json.loads(line)
        if isinstance(payload, dict):
            entries.append(LedgerEntry.from_dict(payload))
    return sorted(entries, key=lambda entry: entry.finished_at)


def filter_ledger_entries(
    entries: Sequence[LedgerEntry],
    *,
    agent_name: str | None = None,
    since: str | None = None,
) -> list[LedgerEntry]:
    filtered = list(entries)
    if agent_name is not None:
        filtered = [entry for entry in filtered if entry.agent_name == agent_name]
    if since is not None:
        threshold = datetime.now(timezone.utc) - parse_relative_duration(since)
        filtered = [entry for entry in filtered if entry.finished_at >= threshold]
    return filtered


def parse_relative_duration(spec: str) -> timedelta:
    normalized = spec.strip().lower()
    if not normalized:
        raise ValueError("Relative duration must not be blank.")
    unit = normalized[-1]
    value_text = normalized[:-1]
    if unit not in {"m", "h", "d"} or not value_text:
        raise ValueError("Relative durations must use the form <number><m|h|d>, for example 30m, 6h, or 7d.")
    value = int(value_text)
    if unit == "m":
        return timedelta(minutes=value)
    if unit == "h":
        return timedelta(hours=value)
    return timedelta(days=value)


def export_ledger_entries(
    entries: Sequence[LedgerEntry],
    *,
    output_format: str,
    flatten_outputs: bool = False,
) -> str:
    normalized = output_format.strip().lower()
    if normalized == "json":
        return json.dumps([entry.as_dict() for entry in entries], indent=2, sort_keys=True)
    if normalized == "jsonl":
        return "\n".join(json.dumps(entry.as_dict(), sort_keys=True) for entry in entries)
    if normalized == "csv":
        return _export_entries_csv(entries, flatten_outputs=flatten_outputs)
    if normalized == "markdown":
        return _export_entries_markdown(entries, flatten_outputs=flatten_outputs)
    raise ValueError(f"Unsupported export format '{output_format}'.")


def build_ledger_report(entries: Sequence[LedgerEntry]) -> dict[str, Any]:
    summary: dict[str, dict[str, Any]] = {}
    total_resets = 0
    total_seconds = 0.0
    for entry in entries:
        bucket = summary.setdefault(
            entry.agent_name,
            {
                "agent_name": entry.agent_name,
                "runs": 0,
                "statuses": {},
                "output_metrics": {},
                "total_resets": 0,
                "total_duration_seconds": 0.0,
            },
        )
        bucket["runs"] += 1
        bucket["total_resets"] += entry.reset_count
        total_resets += entry.reset_count
        duration_seconds = max(0.0, (entry.finished_at - entry.started_at).total_seconds())
        bucket["total_duration_seconds"] += duration_seconds
        total_seconds += duration_seconds

        status_counts = bucket["statuses"]
        status_counts[entry.status] = int(status_counts.get(entry.status, 0)) + 1

        output_metrics = bucket["output_metrics"]
        for key, value in _count_output_metrics(entry.outputs).items():
            output_metrics[key] = int(output_metrics.get(key, 0)) + value

    return {
        "agents": [summary[name] for name in sorted(summary)],
        "total_resets": total_resets,
        "total_runs": len(entries),
        "average_duration_seconds": (total_seconds / len(entries)) if entries else 0.0,
    }


def render_ledger_report(report: Mapping[str, Any], *, output_format: str = "markdown") -> str:
    normalized = output_format.strip().lower()
    if normalized == "json":
        return json.dumps(report, indent=2, sort_keys=True)
    if normalized != "markdown":
        raise ValueError(f"Unsupported report format '{output_format}'.")
    lines = ["# HarnessIQ Run Report", ""]
    for agent in report.get("agents", []):
        agent_name = str(agent["agent_name"])
        lines.append(f"## {agent_name}")
        lines.append(f"- Runs: {agent['runs']}")
        lines.append(f"- Statuses: {json.dumps(agent['statuses'], sort_keys=True)}")
        metrics = agent.get("output_metrics", {})
        if metrics:
            lines.append(f"- Output metrics: {json.dumps(metrics, sort_keys=True)}")
        lines.append(f"- Total resets: {agent['total_resets']}")
        lines.append(f"- Total duration seconds: {round(float(agent['total_duration_seconds']), 2)}")
        lines.append("")
    lines.append(f"Total runs: {report.get('total_runs', 0)}")
    lines.append(f"Total resets: {report.get('total_resets', 0)}")
    lines.append(f"Average duration seconds: {round(float(report.get('average_duration_seconds', 0.0)), 2)}")
    return "\n".join(lines).rstrip()


def follow_ledger(path: Path | str | None = None, *, poll_interval: float = 0.5) -> None:
    ledger_path = Path(path).expanduser() if path is not None else default_ledger_path()
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    ledger_path.touch(exist_ok=True)
    with ledger_path.open("r", encoding="utf-8") as handle:
        handle.seek(0, os.SEEK_END)
        while True:
            line = handle.readline()
            if line:
                print(line.rstrip())
                continue
            time.sleep(poll_interval)


def build_output_sinks(
    *,
    connections: Sequence[SinkConnection] = (),
    sink_specs: Sequence[str] = (),
) -> tuple[OutputSink, ...]:
    sinks: list[OutputSink] = []
    for connection in connections:
        if not connection.enabled:
            continue
        sinks.append(build_sink_from_connection(connection))
    for spec in sink_specs:
        sinks.append(build_sink_from_spec(spec))
    return tuple(sinks)


def build_sink_from_connection(connection: SinkConnection) -> OutputSink:
    return _build_sink(connection.sink_type, connection.config)


def build_sink_from_spec(spec: str) -> OutputSink:
    sink_type, config = parse_sink_spec(spec)
    return _build_sink(sink_type, config)


def parse_sink_spec(spec: str) -> tuple[str, dict[str, Any]]:
    normalized = spec.strip()
    if not normalized:
        raise ValueError("Sink spec must not be blank.")
    sink_type, separator, remainder = normalized.partition(":")
    if not separator:
        raise ValueError(
            "Sink specs must use the form kind:value or kind:key=value,key=value."
        )
    sink_type = sink_type.strip().lower()
    remainder = remainder.strip()
    if not remainder:
        return sink_type, {}
    if "=" not in remainder:
        if sink_type == "jsonl":
            return sink_type, {"path": remainder}
        if sink_type == "obsidian":
            return sink_type, {"vault_path": remainder}
        if sink_type in {"slack", "discord"}:
            return sink_type, {"webhook_url": remainder}
        return sink_type, {"value": remainder}
    config: dict[str, Any] = {}
    for part in remainder.split(","):
        key, separator, value = part.partition("=")
        if not separator:
            raise ValueError(f"Invalid sink assignment '{part}' in spec '{spec}'.")
        config[key.strip()] = _parse_scalar(value.strip())
    return sink_type, config


def _build_sink(sink_type: str, config: Mapping[str, Any]) -> OutputSink:
    normalized = sink_type.strip().lower()
    data = dict(config)
    if normalized == "jsonl":
        return JSONLLedgerSink(path=data.get("path"))
    if normalized == "obsidian":
        return ObsidianSink(
            vault_path=str(data["vault_path"]),
            note_folder=str(data.get("note_folder", "Agent Runs")),
            filename_template=str(data.get("filename_template", "{date}-{agent_name}-{run_id}.md")),
        )
    if normalized == "slack":
        return SlackSink(webhook_url=str(data["webhook_url"]))
    if normalized == "discord":
        return DiscordSink(webhook_url=str(data["webhook_url"]))
    if normalized == "notion":
        return NotionSink(
            api_token=str(data["api_token"]),
            database_id=str(data["database_id"]),
            property_mapping=dict(data.get("property_mapping", {})) if data.get("property_mapping") else None,
        )
    if normalized == "confluence":
        return ConfluenceSink(
            base_url=str(data["base_url"]),
            api_token=str(data["api_token"]),
            space_key=str(data["space_key"]),
            parent_page_id=str(data["parent_page_id"]) if data.get("parent_page_id") is not None else None,
        )
    if normalized == "supabase":
        return SupabaseSink(
            base_url=str(data["base_url"]),
            api_key=str(data["api_key"]),
            table=str(data.get("table", "agent_runs")),
            schema=str(data.get("schema", "public")),
        )
    if normalized == "linear":
        return LinearSink(
            api_key=str(data["api_key"]),
            team_id=str(data["team_id"]),
            explode_field=str(data["explode_field"]) if data.get("explode_field") is not None else None,
        )
    raise ValueError(f"Unsupported sink type '{sink_type}'.")


def _build_notion_properties(
    entry: LedgerEntry,
    property_mapping: dict[str, dict[str, Any]] | None,
) -> dict[str, Any]:
    mapping = property_mapping or {
        "Run": {"path": "run_id", "type": "title"},
        "Agent": {"path": "agent_name", "type": "rich_text"},
        "Status": {"path": "status", "type": "select"},
        "Started": {"path": "started_at", "type": "date"},
        "Finished": {"path": "finished_at", "type": "date"},
    }
    properties: dict[str, Any] = {}
    for property_name, spec in mapping.items():
        source_path = str(spec.get("path", ""))
        kind = str(spec.get("type", "rich_text"))
        raw_value = _resolve_entry_path(entry, source_path)
        transformed = _apply_transform(raw_value, spec.get("transform"))
        if kind == "title":
            properties[property_name] = {"title": [{"text": {"content": str(transformed or "")}}]}
        elif kind == "date":
            date_text = transformed
            if isinstance(date_text, datetime):
                date_text = _isoformat_z(date_text)
            properties[property_name] = {"date": {"start": str(date_text)}} if date_text else {"date": None}
        elif kind == "select":
            properties[property_name] = {"select": {"name": str(transformed)}} if transformed else {"select": None}
        elif kind == "number":
            properties[property_name] = {"number": float(transformed) if transformed is not None else None}
        elif kind == "checkbox":
            properties[property_name] = {"checkbox": bool(transformed)}
        elif kind == "url":
            properties[property_name] = {"url": str(transformed) if transformed else None}
        elif kind == "multi_select":
            values = transformed if isinstance(transformed, list) else [transformed]
            properties[property_name] = {
                "multi_select": [{"name": str(value)} for value in values if value not in (None, "")]
            }
        else:
            properties[property_name] = {"rich_text": [{"text": {"content": _truncate(str(transformed), 1900)}}]}
    return properties


def _build_notion_children(entry: LedgerEntry) -> list[dict[str, Any]]:
    payload = json.dumps(entry.as_dict(), indent=2, sort_keys=True)
    lines = payload.splitlines() or ["{}"]
    return [
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {"rich_text": [{"type": "text", "text": {"content": _truncate(line, 1800)}}]},
        }
        for line in lines[:40]
    ]


def _render_obsidian_note(entry: LedgerEntry) -> str:
    frontmatter = [
        "---",
        f"run_id: {entry.run_id}",
        f"agent: {entry.agent_name}",
        f"status: {entry.status}",
        f"started_at: {_isoformat_z(entry.started_at)}",
        f"finished_at: {_isoformat_z(entry.finished_at)}",
        f"reset_count: {entry.reset_count}",
        f"tags: [{', '.join(entry.tags)}]",
        "---",
        "",
        f"# {entry.agent_name} Run",
        "",
        f"- Status: `{entry.status}`",
        f"- Duration: {_format_duration(entry.finished_at - entry.started_at)}",
        f"- Resets: {entry.reset_count}",
        "",
        "## Outputs",
        "```json",
        json.dumps(entry.outputs, indent=2, sort_keys=True),
        "```",
        "",
        "## Metadata",
        "```json",
        json.dumps(entry.metadata, indent=2, sort_keys=True),
        "```",
        "",
    ]
    return "\n".join(frontmatter)


def _render_confluence_body(entry: LedgerEntry) -> str:
    return (
        f"<h1>{html.escape(entry.agent_name)} Run</h1>"
        f"<p><strong>Status:</strong> {html.escape(entry.status)}</p>"
        f"<p><strong>Run ID:</strong> {html.escape(entry.run_id)}</p>"
        f"<p><strong>Started:</strong> {html.escape(_isoformat_z(entry.started_at))}</p>"
        f"<p><strong>Finished:</strong> {html.escape(_isoformat_z(entry.finished_at))}</p>"
        f"<p><strong>Resets:</strong> {entry.reset_count}</p>"
        f"<h2>Outputs</h2><ac:structured-macro ac:name=\"code\"><ac:plain-text-body><![CDATA[{json.dumps(entry.outputs, indent=2, sort_keys=True)}]]></ac:plain-text-body></ac:structured-macro>"
        f"<h2>Metadata</h2><ac:structured-macro ac:name=\"code\"><ac:plain-text-body><![CDATA[{json.dumps(entry.metadata, indent=2, sort_keys=True)}]]></ac:plain-text-body></ac:structured-macro>"
    )


def _render_notification_text(entry: LedgerEntry) -> str:
    metrics = _count_output_metrics(entry.outputs)
    metrics_text = ", ".join(f"{key}={value}" for key, value in sorted(metrics.items()))
    if not metrics_text:
        metrics_text = "no counted output metrics"
    return (
        f"HarnessIQ run completed\n"
        f"agent={entry.agent_name}\n"
        f"status={entry.status}\n"
        f"run_id={entry.run_id}\n"
        f"duration={_format_duration(entry.finished_at - entry.started_at)}\n"
        f"resets={entry.reset_count}\n"
        f"metrics={metrics_text}"
    )


def _explode_entry(entry: LedgerEntry, explode_field: str | None) -> list[dict[str, Any]]:
    if explode_field is None:
        return []
    value = _resolve_entry_path(entry, explode_field)
    if not isinstance(value, list):
        return []
    return [{"record": item} for item in value]


def _render_linear_title(entry: LedgerEntry, record: Any, template: str) -> str:
    title = template.format(
        agent_name=entry.agent_name,
        status=entry.status,
        run_id=entry.run_id,
    )
    if isinstance(record, Mapping):
        company = record.get("company") or record.get("to_name") or record.get("name")
        role = record.get("title") or record.get("role") or record.get("subject")
        if company or role:
            title = f"{title} - {' / '.join(str(part) for part in (company, role) if part)}"
    return _truncate(title, 250)


def _render_linear_description(entry: LedgerEntry, record: Any) -> str:
    body = {
        "agent_name": entry.agent_name,
        "finished_at": _isoformat_z(entry.finished_at),
        "outputs": entry.outputs,
        "record": record,
        "run_id": entry.run_id,
        "status": entry.status,
    }
    return "```json\n" + json.dumps(body, indent=2, sort_keys=True) + "\n```"


def _resolve_entry_path(entry: LedgerEntry, path: str) -> Any:
    if path == "run_id":
        return entry.run_id
    if path == "agent_name":
        return entry.agent_name
    if path == "started_at":
        return entry.started_at
    if path == "finished_at":
        return entry.finished_at
    if path == "status":
        return entry.status
    if path == "reset_count":
        return entry.reset_count
    if path == "tags":
        return list(entry.tags)
    root: Any
    if path.startswith("outputs."):
        root = entry.outputs
        remainder = path.removeprefix("outputs.")
    elif path.startswith("metadata."):
        root = entry.metadata
        remainder = path.removeprefix("metadata.")
    else:
        root = entry.as_dict()
        remainder = path
    current = root
    for part in remainder.split("."):
        if isinstance(current, Mapping):
            current = current.get(part)
            continue
        return None
    return current


def _apply_transform(value: Any, transform: Any) -> Any:
    if transform == "len":
        if isinstance(value, (list, tuple, dict, set)):
            return len(value)
        return 0 if value is None else 1
    return value


def _count_output_metrics(outputs: Mapping[str, Any]) -> dict[str, int]:
    metrics: dict[str, int] = {}
    for key, value in outputs.items():
        if isinstance(value, list):
            metrics[key] = len(value)
        elif isinstance(value, dict) and "count" in value and isinstance(value["count"], int):
            metrics[key] = int(value["count"])
    return metrics


def _export_entries_csv(entries: Sequence[LedgerEntry], *, flatten_outputs: bool) -> str:
    rows = [_entry_to_row(entry, flatten_outputs=flatten_outputs) for entry in entries]
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return buffer.getvalue().rstrip()


def _export_entries_markdown(entries: Sequence[LedgerEntry], *, flatten_outputs: bool) -> str:
    lines = ["# Ledger Export", ""]
    for entry in entries:
        lines.append(f"## {entry.agent_name} - {entry.run_id}")
        lines.append(f"- Status: `{entry.status}`")
        lines.append(f"- Finished: `{_isoformat_z(entry.finished_at)}`")
        lines.append(f"- Resets: {entry.reset_count}")
        payload = _entry_to_row(entry, flatten_outputs=flatten_outputs)
        lines.append("```json")
        lines.append(json.dumps(payload, indent=2, sort_keys=True))
        lines.append("```")
        lines.append("")
    return "\n".join(lines).rstrip()


def _entry_to_row(entry: LedgerEntry, *, flatten_outputs: bool) -> dict[str, Any]:
    row: dict[str, Any] = {
        "agent_name": entry.agent_name,
        "finished_at": _isoformat_z(entry.finished_at),
        "reset_count": entry.reset_count,
        "run_id": entry.run_id,
        "started_at": _isoformat_z(entry.started_at),
        "status": entry.status,
        "tags": ",".join(entry.tags),
    }
    if flatten_outputs:
        row.update({f"outputs.{key}": value for key, value in _flatten_mapping(entry.outputs).items()})
        row.update({f"metadata.{key}": value for key, value in _flatten_mapping(entry.metadata).items()})
    else:
        row["outputs"] = json.dumps(entry.outputs, sort_keys=True)
        row["metadata"] = json.dumps(entry.metadata, sort_keys=True)
    return row


def _flatten_mapping(payload: Mapping[str, Any], prefix: str = "") -> dict[str, Any]:
    flattened: dict[str, Any] = {}
    for key, value in payload.items():
        next_key = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(value, Mapping):
            flattened.update(_flatten_mapping(value, prefix=next_key))
            continue
        if isinstance(value, list):
            flattened[next_key] = json.dumps(value, sort_keys=True)
            continue
        flattened[next_key] = value
    return flattened


def _parse_scalar(value: str) -> Any:
    if not value:
        return ""
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def _json_safe(value: Any) -> Any:
    if isinstance(value, datetime):
        return _isoformat_z(value)
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    as_dict = getattr(value, "as_dict", None)
    if callable(as_dict):
        return _json_safe(as_dict())
    return str(value)


def _parse_datetime(text: str) -> datetime:
    normalized = text.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    return datetime.fromisoformat(normalized).astimezone(timezone.utc)


def _isoformat_z(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _format_duration(duration: timedelta) -> str:
    total_seconds = max(0, int(duration.total_seconds()))
    minutes, seconds = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h {minutes}m {seconds}s"
    if minutes:
        return f"{minutes}m {seconds}s"
    return f"{seconds}s"


def _safe_slug(value: str) -> str:
    cleaned = "".join(character if character.isalnum() or character in {"-", "_"} else "-" for character in value)
    collapsed = "-".join(part for part in cleaned.split("-") if part)
    return collapsed or "agent"


def _truncate(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    return value[: max(0, limit - 3)] + "..."


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
