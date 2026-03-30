"""
===============================================================================
File: harnessiq/tools/artifact.py

What this file does:
- Defines the `ArtifactToolRuntime` type and the supporting logic it needs in
  the `harnessiq/tools` module.
- Artifact writing and inspection tools.

Use cases:
- Import `ArtifactToolRuntime` when composing higher-level HarnessIQ runtime
  behavior from this package.

How to use it:
- Use the public class and any exported helpers here as the supported entry
  points for this module.

Intent:
- Keep this package responsibility encapsulated behind one focused module
  instead of duplicating the same logic elsewhere.
===============================================================================
"""

from __future__ import annotations

import csv
import hashlib
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from harnessiq.shared.tools import (
    ARTIFACT_APPEND_RUN_LOG,
    ARTIFACT_FINALIZE_REPORT,
    ARTIFACT_LIST_ARTIFACTS,
    ARTIFACT_READ_ARTIFACT,
    ARTIFACT_RENDER_TABLE,
    ARTIFACT_SNAPSHOT_OUTPUT,
    ARTIFACT_WRITE_CSV,
    ARTIFACT_WRITE_JSON,
    ARTIFACT_WRITE_MARKDOWN,
    RegisteredTool,
    ToolArguments,
    ToolDefinition,
)

from .runtime_support import append_jsonl, read_json, resolve_runtime_root, utc_now, write_json


@dataclass(slots=True)
class ArtifactToolRuntime:
    root: Path

    def __init__(self, root: str | Path | None = None) -> None:
        self.root = resolve_runtime_root(root)
        self.artifact_dir.mkdir(parents=True, exist_ok=True)

    @property
    def artifact_dir(self) -> Path:
        return self.root / "artifacts"

    @property
    def index_path(self) -> Path:
        return self.artifact_dir / "index.json"

    def read_index(self) -> list[dict[str, Any]]:
        return read_json(self.index_path, [])

    def write_index(self, items: list[dict[str, Any]]) -> None:
        write_json(self.index_path, items)


def create_artifact_tools(*, runtime: ArtifactToolRuntime | None = None, root: str | Path | None = None) -> tuple[RegisteredTool, ...]:
    active = runtime or ArtifactToolRuntime(root)
    return (
        RegisteredTool(_tool(ARTIFACT_WRITE_MARKDOWN, "write_markdown", {"name": {"type": "string"}, "content": {"type": "string"}, "title": {"type": "string"}, "generate_toc": {"type": "boolean"}, "append_mode": {"type": "boolean"}, "validate_markdown": {"type": "boolean"}}, "Write a Markdown artifact.", ("name", "content")), lambda args: _write_markdown(active, args)),
        RegisteredTool(_tool(ARTIFACT_WRITE_JSON, "write_json", {"name": {"type": "string"}, "data": {}, "schema": {"type": ["object", "null"]}, "indent": {"type": "integer"}, "sort_keys": {"type": "boolean"}, "include_checksum": {"type": "boolean"}}, "Write a JSON artifact.", ("name", "data")), lambda args: _write_json_artifact(active, args)),
        RegisteredTool(_tool(ARTIFACT_WRITE_CSV, "write_csv", {"name": {"type": "string"}, "records": {"type": "array", "items": {"type": "object"}}, "columns": {"type": ["array", "null"], "items": {"type": "string"}}, "column_order": {"type": "string", "enum": ["union_sorted", "first_record", "explicit"]}, "delimiter": {"type": "string"}, "include_summary_row": {"type": "boolean"}}, "Write a CSV artifact.", ("name", "records")), lambda args: _write_csv(active, args)),
        RegisteredTool(_tool(ARTIFACT_APPEND_RUN_LOG, "append_run_log", {"event": {"type": "string"}, "category": {"type": "string", "enum": ["info", "warning", "error", "decision", "milestone", "tool_call_summary", "custom"]}, "data": {"type": ["object", "null"]}, "run_log_name": {"type": "string"}}, "Append a run-log entry.", ("event",)), lambda args: _append_run_log(active, args)),
        RegisteredTool(_tool(ARTIFACT_SNAPSHOT_OUTPUT, "snapshot_output", {"artifact_names": {"type": "array", "items": {"type": "string"}}, "snapshot_label": {"type": "string"}, "description": {"type": "string"}}, "Snapshot artifacts.", ("artifact_names",)), lambda args: _snapshot(active, args)),
        RegisteredTool(_tool(ARTIFACT_RENDER_TABLE, "render_table", {"name": {"type": "string"}, "records": {"type": "array", "items": {"type": "object"}}, "columns": {"type": ["array", "null"], "items": {"type": "string"}}, "max_col_width": {"type": ["integer", "null"]}, "highlight_condition": {"type": ["object", "null"]}, "caption": {"type": "string"}}, "Render a Markdown table artifact.", ("name", "records")), lambda args: _render_table(active, args)),
        RegisteredTool(_tool(ARTIFACT_LIST_ARTIFACTS, "list_artifacts", {"type_filter": {"type": "array", "items": {"type": "string"}}, "include_snapshots": {"type": "boolean"}}, "List known artifacts.", ()), lambda args: _list_artifacts(active, args)),
        RegisteredTool(_tool(ARTIFACT_READ_ARTIFACT, "read_artifact", {"name": {"type": "string"}, "parse_json": {"type": "boolean"}, "max_bytes": {"type": ["integer", "null"]}}, "Read an artifact.", ("name",)), lambda args: _read_artifact(active, args)),
        RegisteredTool(_tool(ARTIFACT_FINALIZE_REPORT, "finalize_report", {"report_name": {"type": "string"}, "sections": {"type": "array", "items": {"type": "object"}}, "include_run_metadata": {"type": "boolean"}, "include_assumption_log": {"type": "boolean"}, "include_decision_log": {"type": "boolean"}}, "Compose a final report artifact.", ()), lambda args: _finalize_report(active, args)),
    )


def _write_markdown(runtime: ArtifactToolRuntime, arguments: ToolArguments) -> dict[str, Any]:
    name = _str(arguments, "name")
    target = runtime.artifact_dir / f"{name}.md"
    content = _str(arguments, "content")
    title = _str(arguments, "title", "")
    if _bool(arguments, "validate_markdown", True):
        _validate_markdown(content)
    toc = _generate_toc(content) if _bool(arguments, "generate_toc", False) else ""
    body = f"---\ntitle: {title or name}\ntimestamp: {utc_now()}\n---\n\n# {title or name}\n\n{toc}{content}".replace("\n\n\n", "\n\n")
    if _bool(arguments, "append_mode", False) and target.exists():
        target.write_text(target.read_text(encoding="utf-8") + "\n" + body, encoding="utf-8")
    else:
        target.write_text(body, encoding="utf-8")
    meta = _register(runtime, target)
    return {"path": str(target), "word_count": len(body.split()), **meta}


def _write_json_artifact(runtime: ArtifactToolRuntime, arguments: ToolArguments) -> dict[str, Any]:
    from .validation import schema_validate

    name = _str(arguments, "name")
    target = runtime.artifact_dir / f"{name}.json"
    data = arguments["data"]
    schema = arguments.get("schema")
    if isinstance(schema, dict):
        validation = schema_validate(data, schema)
        if not validation["valid"]:
            raise ValueError("JSON artifact data did not satisfy the provided schema.")
    rendered = json.dumps(data, indent=_int(arguments, "indent", 2), sort_keys=_bool(arguments, "sort_keys", False), default=str)
    target.write_text(rendered, encoding="utf-8")
    meta = _register(runtime, target)
    if _bool(arguments, "include_checksum", False):
        meta["checksum"] = meta["content_hash"]
    return {"path": str(target), **meta}


def _write_csv(runtime: ArtifactToolRuntime, arguments: ToolArguments) -> dict[str, Any]:
    name = _str(arguments, "name")
    records = _records(arguments, "records")
    target = runtime.artifact_dir / f"{name}.csv"
    column_order = _str(arguments, "column_order", "union_sorted")
    explicit = _str_list(arguments, "columns")
    if column_order == "explicit" and not explicit:
        raise ValueError("'columns' is required when column_order='explicit'.")
    if column_order == "first_record" and records:
        columns = list(records[0])
    elif column_order == "explicit":
        columns = explicit
    else:
        columns = sorted({field for record in records for field in record})
    with target.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, delimiter=_str(arguments, "delimiter", ","))
        writer.writeheader()
        for record in records:
            writer.writerow({column: record.get(column, "") for column in columns})
        if _bool(arguments, "include_summary_row", False):
            writer.writerow({columns[0]: "summary", **{column: "" for column in columns[1:]}})
    meta = _register(runtime, target)
    return {"path": str(target), "row_count": len(records), "columns": columns, **meta}


def _append_run_log(runtime: ArtifactToolRuntime, arguments: ToolArguments) -> dict[str, Any]:
    name = _str(arguments, "run_log_name", "run_log")
    target = runtime.artifact_dir / f"{name}.jsonl"
    payload = {"timestamp": utc_now(), "category": _str(arguments, "category", "info"), "event": _str(arguments, "event"), "data": arguments.get("data")}
    append_jsonl(target, payload)
    meta = _register(runtime, target)
    return {"path": str(target), "entry": payload, **meta}


def _snapshot(runtime: ArtifactToolRuntime, arguments: ToolArguments) -> dict[str, Any]:
    items = runtime.read_index()
    names = _str_list(arguments, "artifact_names")
    selected = items if names == ["*"] else [item for item in items if Path(item["path"]).stem in names]
    snapshot_id = f"snapshot_{utc_now().replace(':', '').replace('-', '')}"
    snapshot_dir = runtime.artifact_dir / "snapshots" / snapshot_id
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    for item in selected:
        shutil.copy2(item["path"], snapshot_dir / Path(item["path"]).name)
    return {"snapshot_id": snapshot_id, "artifacts": [Path(item["path"]).name for item in selected], "snapshot_dir": str(snapshot_dir)}


def _render_table(runtime: ArtifactToolRuntime, arguments: ToolArguments) -> dict[str, Any]:
    name = _str(arguments, "name")
    records = _records(arguments, "records")
    columns = _str_list(arguments, "columns") or sorted({field for record in records for field in record})
    caption = _str(arguments, "caption", "")
    max_width = arguments.get("max_col_width")
    lines = [f"{caption}\n" if caption else "", "| " + " | ".join(_header(column) for column in columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    condition = arguments.get("highlight_condition")
    for record in records:
        values = []
        highlight = isinstance(condition, dict) and all(record.get(field) == value for field, value in condition.items())
        for column in columns:
            value = str(record.get(column, "")).replace("|", "\\|")
            if isinstance(max_width, int) and len(value) > max_width:
                value = value[: max_width - 3] + "..."
            values.append(f"**{value}**" if highlight and value else value)
        lines.append("| " + " | ".join(values) + " |")
    target = runtime.artifact_dir / f"{name}.md"
    target.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    meta = _register(runtime, target)
    return {"path": str(target), "rows": len(records), "columns": len(columns), **meta}


def _list_artifacts(runtime: ArtifactToolRuntime, arguments: ToolArguments) -> dict[str, Any]:
    include_snapshots = _bool(arguments, "include_snapshots", False)
    type_filter = set(_str_list(arguments, "type_filter"))
    items = []
    for item in runtime.read_index():
        path = Path(item["path"])
        if not include_snapshots and "snapshots" in path.parts:
            continue
        if type_filter and path.suffix.lstrip(".") not in type_filter:
            continue
        items.append(item)
    return {"artifacts": items, "count": len(items), "total_size_bytes": sum(int(item.get("size_bytes", 0)) for item in items)}


def _read_artifact(runtime: ArtifactToolRuntime, arguments: ToolArguments) -> dict[str, Any]:
    name = _str(arguments, "name")
    matches = [item for item in runtime.read_index() if Path(item["path"]).stem == name]
    if not matches:
        return {"found": False}
    entry = matches[-1]
    raw = Path(entry["path"]).read_bytes()
    max_bytes = arguments.get("max_bytes")
    visible = raw[:max_bytes] if isinstance(max_bytes, int) else raw
    if _bool(arguments, "parse_json", False) and Path(entry["path"]).suffix == ".json":
        content: Any = json.loads(visible.decode("utf-8"))
    else:
        content = visible.decode("utf-8", errors="replace")
    return {"found": True, "content": content, "metadata": entry}


def _finalize_report(runtime: ArtifactToolRuntime, arguments: ToolArguments) -> dict[str, Any]:
    name = _str(arguments, "report_name", "final_report")
    sections = arguments.get("sections")
    artifacts = runtime.read_index()
    if not isinstance(sections, list) or not sections:
        selected = [{"artifact_name": Path(item["path"]).stem, "include_as": "full_content"} for item in artifacts]
    else:
        selected = sections
    blocks = [f"# {name}\n"]
    if _bool(arguments, "include_run_metadata", True):
        blocks.append(f"Generated at: {utc_now()}\nArtifact count: {len(artifacts)}\n")
    for section in selected:
        if not isinstance(section, dict):
            continue
        artifact_name = section.get("artifact_name")
        matches = [item for item in artifacts if Path(item["path"]).stem == artifact_name]
        if not matches:
            continue
        path = Path(matches[-1]["path"])
        blocks.append(f"## {artifact_name}\n")
        if section.get("include_as") == "toc_entry":
            blocks.append(f"- {artifact_name}\n")
        elif section.get("include_as") == "summary":
            blocks.append(path.read_text(encoding="utf-8", errors="ignore")[:500] + "\n")
        else:
            blocks.append(path.read_text(encoding="utf-8", errors="ignore") + "\n")
    return _write_markdown(runtime, {"name": name, "content": "\n".join(blocks), "title": name, "generate_toc": False, "append_mode": False, "validate_markdown": False})


def _register(runtime: ArtifactToolRuntime, path: Path) -> dict[str, Any]:
    stat = path.stat()
    record = {"name": path.stem, "path": str(path), "size_bytes": stat.st_size, "created_at": utc_now(), "modified_at": utc_now(), "content_hash": hashlib.sha256(path.read_bytes()).hexdigest()}
    items = [item for item in runtime.read_index() if item["path"] != str(path)]
    items.append(record)
    runtime.write_index(items)
    return record


def _validate_markdown(content: str) -> None:
    if content.count("```") % 2 != 0:
        raise ValueError("Markdown contains an unmatched fenced code block.")


def _generate_toc(content: str) -> str:
    lines = [line for line in content.splitlines() if line.startswith("#")]
    if not lines:
        return ""
    toc = ["## Table of Contents"]
    previous = 1
    for line in lines:
        level = len(line) - len(line.lstrip("#"))
        if level - previous > 1:
            raise ValueError("Markdown headings skip levels.")
        previous = level
        title = line.lstrip("#").strip()
        toc.append(f"- {title}")
    return "\n".join(toc) + "\n\n"


def _header(name: str) -> str:
    return name.replace("_", " ").title()


def _tool(key: str, name: str, properties: dict[str, object], description: str, required: tuple[str, ...]) -> ToolDefinition:
    return ToolDefinition(key=key, name=name, description=description, input_schema={"type": "object", "properties": properties, "required": list(required), "additionalProperties": False})


def _records(arguments: ToolArguments, key: str) -> list[dict[str, Any]]:
    value = arguments[key]
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise ValueError(f"The '{key}' argument must be an array of objects.")
    return [dict(item) for item in value]


def _str(arguments: ToolArguments, key: str, default: str | None = None) -> str:
    if key not in arguments:
        if default is None:
            raise ValueError(f"The '{key}' argument is required.")
        return default
    value = arguments[key]
    if not isinstance(value, str):
        raise ValueError(f"The '{key}' argument must be a string.")
    return value


def _str_list(arguments: ToolArguments, key: str) -> list[str]:
    if key not in arguments:
        return []
    value = arguments[key]
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"The '{key}' argument must be an array of strings.")
    return list(value)


def _int(arguments: ToolArguments, key: str, default: int | None = None) -> int:
    if key not in arguments:
        if default is None:
            raise ValueError(f"The '{key}' argument is required.")
        return default
    value = arguments[key]
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"The '{key}' argument must be an integer.")
    return value


def _bool(arguments: ToolArguments, key: str, default: bool) -> bool:
    value = arguments.get(key, default)
    if not isinstance(value, bool):
        raise ValueError(f"The '{key}' argument must be a boolean.")
    return value


__all__ = ["ArtifactToolRuntime", "create_artifact_tools"]
