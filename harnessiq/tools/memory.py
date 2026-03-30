"""
===============================================================================
File: harnessiq/tools/memory.py

What this file does:
- Defines the `MemoryToolRuntime` type and the supporting logic it needs in the
  `harnessiq/tools` module.
- Local durable memory tools.

Use cases:
- Import `MemoryToolRuntime` when composing higher-level HarnessIQ runtime
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

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from harnessiq.shared.tools import (
    MEMORY_APPEND_JOURNAL,
    MEMORY_CHECKPOINT,
    MEMORY_COMPARE_CHECKPOINTS,
    MEMORY_DELETE,
    MEMORY_INCREMENT_COUNTER,
    MEMORY_LIST_KEYS,
    MEMORY_LOAD,
    MEMORY_LOAD_CHECKPOINT,
    MEMORY_SAVE,
    MEMORY_UPSERT_JSON,
    RegisteredTool,
    ToolArguments,
    ToolDefinition,
)

from .runtime_support import read_json, resolve_runtime_root, utc_now, write_json


@dataclass(slots=True)
class MemoryToolRuntime:
    root: Path

    def __init__(self, root: str | Path | None = None) -> None:
        self.root = resolve_runtime_root(root)

    @property
    def entries_path(self) -> Path:
        return self.root / "memory_entries.json"

    @property
    def checkpoints_path(self) -> Path:
        return self.root / "memory_checkpoints.json"

    def read_entries(self) -> dict[str, Any]:
        return read_json(self.entries_path, {})

    def write_entries(self, entries: dict[str, Any]) -> None:
        write_json(self.entries_path, entries)

    def read_checkpoints(self) -> list[dict[str, Any]]:
        return read_json(self.checkpoints_path, [])

    def write_checkpoints(self, checkpoints: list[dict[str, Any]]) -> None:
        write_json(self.checkpoints_path, checkpoints)


def create_memory_tools(*, runtime: MemoryToolRuntime | None = None, root: str | Path | None = None) -> tuple[RegisteredTool, ...]:
    active = runtime or MemoryToolRuntime(root)
    return (
        RegisteredTool(_tool(MEMORY_LOAD, "load", {"key": {"type": "string"}, "expected_type": {"type": "string", "enum": ["string", "integer", "boolean", "list", "object", "any"]}, "default": {}}, "Load one memory key.", ("key",)), lambda args: _load(active, args)),
        RegisteredTool(_tool(MEMORY_SAVE, "save", {"key": {"type": "string"}, "value": {}, "append_to_list": {"type": "boolean"}, "write_if_absent_only": {"type": "boolean"}}, "Save one memory key.", ("key", "value")), lambda args: _save(active, args)),
        RegisteredTool(_tool(MEMORY_APPEND_JOURNAL, "append_journal", {"event_type": {"type": "string"}, "description": {"type": "string"}, "data": {"type": ["object", "null"]}, "journal_key": {"type": "string"}, "max_journal_entries": {"type": "integer"}}, "Append to a journal list.", ("event_type", "description")), lambda args: _append_journal(active, args)),
        RegisteredTool(_tool(MEMORY_CHECKPOINT, "checkpoint", {"fields": {"type": "object"}, "checkpoint_label": {"type": "string"}, "overwrite_fields": {"type": "boolean"}}, "Write a memory checkpoint.", ("fields",)), lambda args: _checkpoint(active, args)),
        RegisteredTool(_tool(MEMORY_UPSERT_JSON, "upsert_json", {"key": {"type": "string"}, "path": {"type": "string"}, "value": {}, "create_path": {"type": "boolean"}, "list_append": {"type": "boolean"}}, "Upsert one JSON path.", ("key", "path", "value")), lambda args: _upsert_json(active, args)),
        RegisteredTool(_tool(MEMORY_LIST_KEYS, "list_keys", {"prefix": {"type": "string"}, "include_values": {"type": "boolean"}, "sort_by": {"type": "string", "enum": ["key_asc", "written_desc", "size_desc"]}}, "List stored memory keys.", ()), lambda args: _list_keys(active, args)),
        RegisteredTool(_tool(MEMORY_LOAD_CHECKPOINT, "load_checkpoint", {"checkpoint_label": {"type": ["string", "null"]}, "reset_count": {"type": ["integer", "null"]}}, "Load a stored checkpoint.", ()), lambda args: _load_checkpoint(active, args)),
        RegisteredTool(_tool(MEMORY_INCREMENT_COUNTER, "increment_counter", {"key": {"type": "string"}, "amount": {"type": "integer"}, "initial_value": {"type": "integer"}, "max_value": {"type": ["integer", "null"]}}, "Increment a numeric counter.", ("key",)), lambda args: _increment(active, args)),
        RegisteredTool(_tool(MEMORY_DELETE, "delete", {"key": {"type": "string"}, "strict": {"type": "boolean"}}, "Delete a memory key.", ("key",)), lambda args: _delete(active, args)),
        RegisteredTool(_tool(MEMORY_COMPARE_CHECKPOINTS, "compare_checkpoints", {"checkpoint_a": {}, "checkpoint_b": {}, "include_values": {"type": "boolean"}, "ignore_fields": {"type": "array", "items": {"type": "string"}}}, "Compare two checkpoints.", ("checkpoint_a", "checkpoint_b")), lambda args: _compare_checkpoints(active, args)),
    )


def _load(runtime: MemoryToolRuntime, arguments: ToolArguments) -> dict[str, Any]:
    key = _str(arguments, "key")
    entries = runtime.read_entries()
    entry = entries.get(key)
    default = arguments.get("default")
    if entry is None:
        return {"found": False, "value": default, "written_at": None, "write_count": 0}
    expected = _str(arguments, "expected_type", "any")
    if expected != "any" and _type_name(entry["value"]) != expected:
        raise ValueError(f"Memory key '{key}' has type {_type_name(entry['value'])}, expected {expected}.")
    return {"found": True, "value": entry["value"], "written_at": entry["written_at"], "write_count": entry["write_count"]}


def _save(runtime: MemoryToolRuntime, arguments: ToolArguments) -> dict[str, Any]:
    key = _str(arguments, "key")
    entries = runtime.read_entries()
    previous = entries.get(key)
    if _bool(arguments, "write_if_absent_only", False) and previous is not None:
        return {"key": key, "value": previous["value"], "previous_value": previous["value"], "status": "unchanged"}
    value = arguments["value"]
    if _bool(arguments, "append_to_list", False):
        existing = previous["value"] if previous else []
        if not isinstance(existing, list):
            raise ValueError(f"Memory key '{key}' is not a list.")
        appended = list(existing)
        appended.extend(value if isinstance(value, list) else [value])
        value = appended
    entries[key] = {"value": value, "written_at": utc_now(), "write_count": int(previous["write_count"]) + 1 if previous else 1}
    runtime.write_entries(entries)
    return {"key": key, "value": value, "previous_value": None if previous is None else previous["value"], "status": "updated" if previous else "new"}


def _append_journal(runtime: MemoryToolRuntime, arguments: ToolArguments) -> dict[str, Any]:
    key = _str(arguments, "journal_key", "agent_journal")
    payload = {"event_type": _str(arguments, "event_type"), "description": _str(arguments, "description"), "data": arguments.get("data"), "timestamp": utc_now()}
    result = _save(runtime, {"key": key, "value": [payload], "append_to_list": True})
    entries = runtime.read_entries()
    max_entries = _int(arguments, "max_journal_entries", 500)
    journal = entries[key]["value"]
    pruned = 0
    if len(journal) > max_entries:
        pruned = len(journal) - max_entries
        entries[key]["value"] = journal[-max_entries:]
        runtime.write_entries(entries)
    return {"journal_key": key, "entry": payload, "pruned_count": pruned}


def _checkpoint(runtime: MemoryToolRuntime, arguments: ToolArguments) -> dict[str, Any]:
    fields = _obj(arguments, "fields")
    overwrite = _bool(arguments, "overwrite_fields", True)
    checkpoints = runtime.read_checkpoints()
    entries = runtime.read_entries()
    written = {}
    for key, value in fields.items():
        if key in entries and not overwrite:
            continue
        entries[key] = {"value": value, "written_at": utc_now(), "write_count": int(entries[key]["write_count"]) + 1 if key in entries else 1}
        written[key] = value
    runtime.write_entries(entries)
    checkpoint = {"checkpoint_id": f"ckpt_{len(checkpoints) + 1}", "label": _str(arguments, "checkpoint_label", "pre_reset"), "timestamp": utc_now(), "reset_count": len(checkpoints), "fields": written}
    checkpoints.append(checkpoint)
    runtime.write_checkpoints(checkpoints)
    return {"checkpoint_id": checkpoint["checkpoint_id"], "fields_written": sorted(written), "serialized_size": len(str(written))}


def _upsert_json(runtime: MemoryToolRuntime, arguments: ToolArguments) -> dict[str, Any]:
    key = _str(arguments, "key")
    entries = runtime.read_entries()
    existing = entries.get(key, {"value": {}, "write_count": 0})
    root = dict(existing["value"]) if isinstance(existing["value"], dict) else {}
    cursor: Any = root
    parts = _str(arguments, "path").split(".")
    for part in parts[:-1]:
        if part not in cursor:
            if not _bool(arguments, "create_path", True):
                raise ValueError(f"Missing path component '{part}'.")
            cursor[part] = {}
        if not isinstance(cursor[part], dict):
            raise ValueError(f"Path component '{part}' is not an object.")
        cursor = cursor[part]
    last = parts[-1]
    if _bool(arguments, "list_append", False):
        cursor.setdefault(last, [])
        if not isinstance(cursor[last], list):
            raise ValueError(f"Path '{last}' is not a list.")
        cursor[last].append(arguments["value"])
    else:
        cursor[last] = arguments["value"]
    entries[key] = {"value": root, "written_at": utc_now(), "write_count": int(existing["write_count"]) + 1}
    runtime.write_entries(entries)
    return {"updated_value": cursor[last], "object": root}


def _list_keys(runtime: MemoryToolRuntime, arguments: ToolArguments) -> dict[str, Any]:
    prefix = _str(arguments, "prefix", "")
    include_values = _bool(arguments, "include_values", False)
    entries = runtime.read_entries()
    rows = []
    for key, entry in entries.items():
        if prefix and not key.startswith(prefix):
            continue
        payload = {"key": key, "type": _type_name(entry["value"]), "written_at": entry["written_at"], "size_bytes": len(str(entry["value"]))}
        if include_values:
            payload["value"] = entry["value"]
        rows.append(payload)
    sort_by = _str(arguments, "sort_by", "key_asc")
    rows.sort(key=lambda item: item["key"] if sort_by == "key_asc" else item["written_at"] if sort_by == "written_desc" else item["size_bytes"], reverse=sort_by != "key_asc")
    return {"keys": rows}


def _load_checkpoint(runtime: MemoryToolRuntime, arguments: ToolArguments) -> dict[str, Any]:
    checkpoints = runtime.read_checkpoints()
    label = _opt_str(arguments, "checkpoint_label")
    reset_count = arguments.get("reset_count")
    matches = [item for item in checkpoints if (label is None or item["label"] == label) and (reset_count is None or item["reset_count"] == reset_count)]
    if not matches:
        return {"found": False}
    checkpoint = matches[-1]
    return {"found": True, "checkpoint_id": checkpoint["checkpoint_id"], "label": checkpoint["label"], "timestamp": checkpoint["timestamp"], "reset_count": checkpoint["reset_count"], "fields": checkpoint["fields"]}


def _increment(runtime: MemoryToolRuntime, arguments: ToolArguments) -> dict[str, Any]:
    key = _str(arguments, "key")
    amount = _int(arguments, "amount", 1)
    initial = _int(arguments, "initial_value", 0)
    max_value = arguments.get("max_value")
    entries = runtime.read_entries()
    previous = int(entries.get(key, {"value": initial})["value"])
    value = previous + amount
    capped = False
    if isinstance(max_value, int) and value > max_value:
        value = max_value
        capped = True
    entries[key] = {"value": value, "written_at": utc_now(), "write_count": int(entries.get(key, {"write_count": 0})["write_count"]) + 1}
    runtime.write_entries(entries)
    return {"previous_value": previous, "new_value": value, "capped": capped}


def _delete(runtime: MemoryToolRuntime, arguments: ToolArguments) -> dict[str, Any]:
    key = _str(arguments, "key")
    entries = runtime.read_entries()
    if key not in entries:
        if _bool(arguments, "strict", False):
            raise ValueError(f"Memory key '{key}' does not exist.")
        return {"key": key, "found": False, "previous_value": None}
    previous = entries.pop(key)
    runtime.write_entries(entries)
    return {"key": key, "found": True, "previous_value": previous["value"]}


def _compare_checkpoints(runtime: MemoryToolRuntime, arguments: ToolArguments) -> dict[str, Any]:
    left = _resolve_checkpoint(runtime, arguments["checkpoint_a"])
    right = _resolve_checkpoint(runtime, arguments["checkpoint_b"])
    ignore = set(_str_list(arguments, "ignore_fields"))
    include_values = _bool(arguments, "include_values", True)
    left_fields = {key: value for key, value in left["fields"].items() if key not in ignore}
    right_fields = {key: value for key, value in right["fields"].items() if key not in ignore}
    added = sorted(set(right_fields) - set(left_fields))
    removed = sorted(set(left_fields) - set(right_fields))
    changed = []
    for key in sorted(set(left_fields) & set(right_fields)):
        if left_fields[key] != right_fields[key]:
            payload = {"field": key}
            if include_values:
                payload["old"] = left_fields[key]
                payload["new"] = right_fields[key]
            changed.append(payload)
    return {"added_fields": added, "removed_fields": removed, "changed_fields": changed}


def _resolve_checkpoint(runtime: MemoryToolRuntime, identifier: Any) -> dict[str, Any]:
    checkpoints = runtime.read_checkpoints()
    if isinstance(identifier, str):
        for item in checkpoints:
            if item["checkpoint_id"] == identifier or item["label"] == identifier:
                return item
    if isinstance(identifier, dict):
        if "label" in identifier:
            matches = [item for item in checkpoints if item["label"] == identifier["label"]]
            if matches:
                return matches[-1]
        if "reset_count" in identifier:
            matches = [item for item in checkpoints if item["reset_count"] == identifier["reset_count"]]
            if matches:
                return matches[-1]
    raise ValueError("Checkpoint identifier did not match any stored checkpoint.")


def _type_name(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "list"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def _tool(key: str, name: str, properties: dict[str, object], description: str, required: tuple[str, ...]) -> ToolDefinition:
    return ToolDefinition(key=key, name=name, description=description, input_schema={"type": "object", "properties": properties, "required": list(required), "additionalProperties": False})


def _str(arguments: ToolArguments, key: str, default: str | None = None) -> str:
    if key not in arguments:
        if default is None:
            raise ValueError(f"The '{key}' argument is required.")
        return default
    value = arguments[key]
    if not isinstance(value, str):
        raise ValueError(f"The '{key}' argument must be a string.")
    return value


def _opt_str(arguments: ToolArguments, key: str) -> str | None:
    if key not in arguments or arguments[key] is None:
        return None
    return _str(arguments, key)


def _obj(arguments: ToolArguments, key: str) -> dict[str, Any]:
    value = arguments[key]
    if not isinstance(value, dict):
        raise ValueError(f"The '{key}' argument must be an object.")
    return dict(value)


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


def _str_list(arguments: ToolArguments, key: str) -> list[str]:
    if key not in arguments:
        return []
    value = arguments[key]
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"The '{key}' argument must be an array of strings.")
    return list(value)


__all__ = ["MemoryToolRuntime", "create_memory_tools"]
