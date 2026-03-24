"""Ledger sink implementations and sink-construction helpers."""

from __future__ import annotations

import html
import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from harnessiq.providers.output_sinks import (
    ConfluenceClient,
    GoogleSheetsClient,
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

OutputSinkFactory = Callable[[Mapping[str, Any]], OutputSink]
_BUILTIN_SINK_FACTORIES: dict[str, OutputSinkFactory] = {}
_CUSTOM_SINK_FACTORIES: dict[str, OutputSinkFactory] = {}
_INSTAGRAM_AGENT_NAME = "instagram_keyword_discovery"
_INSTAGRAM_LEAD_EXPORT_HEADER = ("name", "instagram_url", "email_address", "username")


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


@dataclass(slots=True)
class GoogleSheetsSink:
    """Append one or more ledger rows into a Google Sheet."""

    client_id: str
    client_secret: str
    refresh_token: str
    spreadsheet_id: str
    sheet_name: str = "Sheet1"
    explode_field: str | None = None
    include_header: bool = True
    scope: str | None = None
    token_url: str | None = None
    base_url: str | None = None
    client: GoogleSheetsClient | None = None

    def on_run_complete(self, entry: LedgerEntry) -> None:
        client = self.client or self._build_client()
        records = _explode_entry(entry, self.explode_field)
        if not records:
            records = [{"record": None}]
        row_dicts: list[dict[str, Any]] = []
        for item in records:
            row_dicts.extend(_render_google_sheets_rows(entry, item.get("record")))
        _append_google_sheet_rows(
            client=client,
            spreadsheet_id=self.spreadsheet_id,
            sheet_name=self.sheet_name,
            row_dicts=row_dicts,
            include_header=self.include_header,
        )

    def _build_client(self) -> GoogleSheetsClient:
        kwargs: dict[str, Any] = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self.refresh_token,
        }
        if self.scope is not None:
            kwargs["scope"] = self.scope
        if self.token_url is not None:
            kwargs["token_url"] = self.token_url
        if self.base_url is not None:
            kwargs["base_url"] = self.base_url
        return GoogleSheetsClient(**kwargs)


def register_output_sink(
    sink_type: str,
    factory: OutputSinkFactory,
    *,
    allow_replace: bool = False,
) -> None:
    """Register a custom output sink factory under ``sink_type``."""
    normalized = _normalize_sink_type(sink_type)
    if not callable(factory):
        raise TypeError("factory must be callable.")
    if normalized in _BUILTIN_SINK_FACTORIES and not allow_replace:
        raise ValueError(f"Sink type '{normalized}' is reserved for a built-in Harnessiq sink.")
    if normalized in _CUSTOM_SINK_FACTORIES and not allow_replace:
        raise ValueError(f"Sink type '{normalized}' is already registered.")
    _CUSTOM_SINK_FACTORIES[normalized] = factory


def unregister_output_sink(sink_type: str) -> None:
    """Remove a previously registered custom sink type."""
    normalized = _normalize_sink_type(sink_type)
    if normalized in _BUILTIN_SINK_FACTORIES:
        raise ValueError(f"Cannot unregister built-in sink type '{normalized}'.")
    _CUSTOM_SINK_FACTORIES.pop(normalized, None)


def list_output_sink_types() -> tuple[str, ...]:
    """Return the currently available sink type names."""
    return tuple([*sorted(_BUILTIN_SINK_FACTORIES), *sorted(_CUSTOM_SINK_FACTORIES)])


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
    return build_output_sink(connection.sink_type, connection.config)


def build_sink_from_spec(spec: str) -> OutputSink:
    sink_type, config = parse_sink_spec(spec)
    return build_output_sink(sink_type, config)


def build_output_sink(sink_type: str, config: Mapping[str, Any]) -> OutputSink:
    """Build one output sink instance from a sink type and config mapping."""
    normalized = _normalize_sink_type(sink_type)
    factory = _CUSTOM_SINK_FACTORIES.get(normalized) or _BUILTIN_SINK_FACTORIES.get(normalized)
    if factory is None:
        raise ValueError(
            f"Unsupported sink type '{sink_type}'. "
            f"Available sink types: {', '.join(list_output_sink_types())}."
        )
    return factory(dict(config))


def _build_sink(sink_type: str, config: Mapping[str, Any]) -> OutputSink:
    return build_output_sink(sink_type, config)


def _normalize_sink_type(sink_type: str) -> str:
    normalized = sink_type.strip().lower()
    if not normalized:
        raise ValueError("Sink type must not be blank.")
    return normalized


def _register_builtin_sinks() -> None:
    if _BUILTIN_SINK_FACTORIES:
        return
    _BUILTIN_SINK_FACTORIES.update(
        {
            "jsonl": lambda data: JSONLLedgerSink(path=data.get("path")),
            "obsidian": lambda data: ObsidianSink(
                vault_path=str(data["vault_path"]),
                note_folder=str(data.get("note_folder", "Agent Runs")),
                filename_template=str(data.get("filename_template", "{date}-{agent_name}-{run_id}.md")),
            ),
            "slack": lambda data: SlackSink(webhook_url=str(data["webhook_url"])),
            "discord": lambda data: DiscordSink(webhook_url=str(data["webhook_url"])),
            "notion": lambda data: NotionSink(
                api_token=str(data["api_token"]),
                database_id=str(data["database_id"]),
                property_mapping=dict(data.get("property_mapping", {})) if data.get("property_mapping") else None,
            ),
            "confluence": lambda data: ConfluenceSink(
                base_url=str(data["base_url"]),
                api_token=str(data["api_token"]),
                space_key=str(data["space_key"]),
                parent_page_id=str(data["parent_page_id"]) if data.get("parent_page_id") is not None else None,
            ),
            "supabase": lambda data: SupabaseSink(
                base_url=str(data["base_url"]),
                api_key=str(data["api_key"]),
                table=str(data.get("table", "agent_runs")),
                schema=str(data.get("schema", "public")),
            ),
            "linear": lambda data: LinearSink(
                api_key=str(data["api_key"]),
                team_id=str(data["team_id"]),
                explode_field=str(data["explode_field"]) if data.get("explode_field") is not None else None,
            ),
            "google_sheets": lambda data: GoogleSheetsSink(
                client_id=str(data["client_id"]),
                client_secret=str(data["client_secret"]),
                refresh_token=str(data["refresh_token"]),
                spreadsheet_id=str(data["spreadsheet_id"]),
                sheet_name=str(data.get("sheet_name", "Sheet1")),
                explode_field=str(data["explode_field"]) if data.get("explode_field") is not None else None,
                include_header=_coerce_sink_bool(data.get("include_header"), default=True),
                scope=str(data["scope"]) if data.get("scope") is not None else None,
                token_url=str(data["token_url"]) if data.get("token_url") is not None else None,
                base_url=str(data["base_url"]) if data.get("base_url") is not None else None,
            ),
        }
    )


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


def _render_google_sheets_row(entry: LedgerEntry, record: Any) -> dict[str, Any]:
    row: dict[str, Any] = {
        "run_id": entry.run_id,
        "agent_name": entry.agent_name,
        "status": entry.status,
        "started_at": _isoformat_z(entry.started_at),
        "finished_at": _isoformat_z(entry.finished_at),
        "reset_count": entry.reset_count,
    }
    if isinstance(record, Mapping):
        row.update(_flatten_sheet_mapping(record))
        return row
    if record is not None:
        row["record"] = _render_sheet_cell(record)
        return row
    row["outputs_json"] = json.dumps(entry.outputs, sort_keys=True)
    row["metadata_json"] = json.dumps(entry.metadata, sort_keys=True)
    row["tags_json"] = json.dumps(list(entry.tags), sort_keys=True)
    return row


def _render_google_sheets_rows(entry: LedgerEntry, record: Any) -> list[dict[str, Any]]:
    instagram_rows = _maybe_render_instagram_google_sheets_rows(entry, record)
    if instagram_rows is not None:
        return instagram_rows
    return [_render_google_sheets_row(entry, record)]


def _maybe_render_instagram_google_sheets_rows(
    entry: LedgerEntry,
    record: Any,
) -> list[dict[str, Any]] | None:
    if entry.agent_name != _INSTAGRAM_AGENT_NAME or not isinstance(record, Mapping):
        return None
    source_url = str(record.get("source_url", "")).strip()
    if "instagram.com" not in source_url.lower():
        return None
    try:
        from harnessiq.shared.instagram import build_instagram_lead_export_rows

        return [dict(row) for row in build_instagram_lead_export_rows(record)]
    except (KeyError, TypeError, ValueError):
        return None


def _flatten_sheet_mapping(payload: Mapping[str, Any], prefix: str = "") -> dict[str, Any]:
    flattened: dict[str, Any] = {}
    for key in sorted(payload):
        column_name = f"{prefix}.{key}" if prefix else str(key)
        value = payload[key]
        if isinstance(value, Mapping):
            flattened.update(_flatten_sheet_mapping(value, column_name))
            continue
        flattened[column_name] = _render_sheet_cell(value)
    return flattened


def _render_sheet_cell(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, datetime):
        return _isoformat_z(value)
    return json.dumps(value, sort_keys=True, default=str)


def _append_google_sheet_rows(
    *,
    client: GoogleSheetsClient,
    spreadsheet_id: str,
    sheet_name: str,
    row_dicts: Sequence[Mapping[str, Any]],
    include_header: bool,
) -> None:
    if not row_dicts:
        return
    existing_values = client.get_values(spreadsheet_id=spreadsheet_id, range_name=f"{sheet_name}!1:1")
    existing_header = [str(cell) for cell in existing_values[0]] if existing_values else []
    desired_header = _determine_sheet_header(row_dicts=row_dicts, existing_header=existing_header)
    should_write_header = bool(existing_header) and desired_header != existing_header
    should_write_header = should_write_header or (include_header and bool(desired_header) and not existing_header)
    if should_write_header:
        client.update_values(
            spreadsheet_id=spreadsheet_id,
            range_name=f"{sheet_name}!1:1",
            values=[desired_header],
        )
    header = desired_header if desired_header else existing_header
    values = [[row.get(column, "") for column in header] for row in row_dicts]
    client.append_values(
        spreadsheet_id=spreadsheet_id,
        range_name=f"{sheet_name}!A:A",
        values=values,
    )


def _determine_sheet_header(
    *,
    row_dicts: Sequence[Mapping[str, Any]],
    existing_header: Sequence[str],
) -> list[str]:
    instagram_header = _resolve_instagram_lead_header(row_dicts)
    if instagram_header is not None:
        return instagram_header
    header = list(existing_header)
    for row in row_dicts:
        for key in row:
            if key not in header:
                header.append(str(key))
    return header


def _resolve_instagram_lead_header(row_dicts: Sequence[Mapping[str, Any]]) -> list[str] | None:
    if not row_dicts:
        return None
    allowed = set(_INSTAGRAM_LEAD_EXPORT_HEADER)
    if any(set(row) - allowed for row in row_dicts):
        return None
    if not any("instagram_url" in row for row in row_dicts):
        return None
    return [column for column in _INSTAGRAM_LEAD_EXPORT_HEADER if any(column in row for row in row_dicts)]


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


def _coerce_sink_bool(value: Any, *, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "on"}:
            return True
        if normalized in {"false", "0", "no", "off"}:
            return False
    raise ValueError(f"Expected a boolean-compatible sink value, received {value!r}.")


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
    "GoogleSheetsSink",
    "JSONLLedgerSink",
    "LinearSink",
    "NotionSink",
    "ObsidianSink",
    "SlackSink",
    "SupabaseSink",
    "build_output_sink",
    "build_output_sinks",
    "build_sink_from_connection",
    "build_sink_from_spec",
    "list_output_sink_types",
    "register_output_sink",
    "unregister_output_sink",
]


_register_builtin_sinks()
