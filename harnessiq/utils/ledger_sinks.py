"""Ledger sink implementations and sink-construction helpers."""

from __future__ import annotations

import html
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from harnessiq.providers.output_sinks import (
    ConfluenceClient,
    LinearClient,
    NotionClient,
    SupabaseClient,
    WebhookDeliveryClient,
)
from harnessiq.utils.ledger_connections import SinkConnection, default_ledger_path, parse_sink_spec
from harnessiq.utils.ledger_models import (
    LedgerEntry,
    OutputSink,
    _format_duration,
    _isoformat_z,
    _safe_slug,
    _truncate,
)


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


__all__ = [
    "ConfluenceSink",
    "DiscordSink",
    "JSONLLedgerSink",
    "LinearSink",
    "NotionSink",
    "ObsidianSink",
    "SlackSink",
    "SupabaseSink",
    "build_output_sinks",
    "build_sink_from_connection",
    "build_sink_from_spec",
]
