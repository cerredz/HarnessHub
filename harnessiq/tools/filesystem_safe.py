"""Additive and non-destructive filesystem tools."""

from __future__ import annotations

import csv
import difflib
import filecmp
import mimetypes
import os
import shutil
import zlib
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from typing import Any

from charset_normalizer import from_bytes

from harnessiq.shared.tools import (
    FILESYSTEM_SAFE_APPEND,
    FILESYSTEM_SAFE_COPY,
    FILESYSTEM_SAFE_DIFF,
    FILESYSTEM_SAFE_EXISTS,
    FILESYSTEM_SAFE_FIND,
    FILESYSTEM_SAFE_LIST,
    FILESYSTEM_SAFE_READ,
    FILESYSTEM_SAFE_STAT,
    FILESYSTEM_SAFE_WRITE,
    RegisteredTool,
    ToolArguments,
    ToolDefinition,
)


def read_file(path: str, *, max_bytes: int | None = None, lines: dict[str, int] | None = None, encoding: str | None = None) -> dict[str, Any]:
    target = _path(path)
    if not target.is_file():
        raise ValueError(f"Path '{target}' is not a file.")
    raw = target.read_bytes()
    detected = encoding or _detect_encoding(raw)
    text = raw.decode(detected, errors="replace")
    truncated = False
    if lines is not None:
        start = int(lines.get("start", 1))
        end = int(lines.get("end", start))
        content = "\n".join(text.splitlines()[start - 1 : end])
    elif max_bytes is not None and len(raw) > max_bytes:
        content = raw[:max_bytes].decode(detected, errors="replace")
        truncated = True
    else:
        content = text
    return {"path": str(target), "content": content, "size_bytes": len(raw), "line_count": len(text.splitlines()), "encoding": detected, "truncated": truncated}


def list_directory(path: str, *, recursive: bool = False, max_depth: int = 3, pattern: str | None = None, include_hidden: bool = False, summary_only: bool = False) -> dict[str, Any]:
    root = _path(path)
    if not root.is_dir():
        raise ValueError(f"Path '{root}' is not a directory.")
    entries = list(_walk(root, recursive=recursive, max_depth=max_depth, include_hidden=include_hidden, pattern=pattern))
    entries.sort(key=lambda item: (item["type"] != "directory", item["path"].lower()))
    summary = {"total_files": sum(1 for item in entries if item["type"] == "file"), "total_dirs": sum(1 for item in entries if item["type"] == "directory"), "total_size_bytes": sum(int(item.get("size_bytes", 0)) for item in entries)}
    return {"path": str(root), "entries": [] if summary_only else entries, "summary": summary}


def exists(path: str, *, expect_type: str | None = None, follow_symlinks: bool = True) -> dict[str, Any]:
    target = _path(path)
    exists_value = target.exists() if follow_symlinks else os.path.lexists(target)
    entry_type = "directory" if target.is_dir() else "file" if target.is_file() else "symlink" if target.is_symlink() else None
    return {"path": str(target), "exists": exists_value, "entry_type": entry_type, "resolved_path": str(target.resolve(strict=False)), "readable": os.access(target, os.R_OK), "expected_type_matches": expect_type is None or entry_type == expect_type}


def copy_path(source: str, destination: str, *, if_exists: str = "error", create_parents: bool = True) -> dict[str, Any]:
    src = _path(source)
    dst = _path(destination)
    if not src.is_file():
        raise ValueError("filesystem_safe.copy only supports files.")
    if create_parents:
        dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        if if_exists == "error":
            raise ValueError(f"Destination '{dst}' already exists.")
        if if_exists == "rename":
            stamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
            dst = dst.with_stem(f"{dst.stem}_{stamp}")
    shutil.copy2(src, dst)
    return {"destination": str(dst), "bytes_copied": dst.stat().st_size, "integrity_ok": _crc32(src) == _crc32(dst)}


def append_file(path: str, content: str, *, line_separator: str = "\n", ensure_newline_before: bool = True, create_parents: bool = True) -> dict[str, Any]:
    target = _path(path)
    if create_parents:
        target.parent.mkdir(parents=True, exist_ok=True)
    prefix = ""
    if target.exists() and ensure_newline_before and target.read_text(encoding="utf-8", errors="ignore") and not target.read_text(encoding="utf-8", errors="ignore").endswith("\n"):
        prefix = "\n"
    rendered = f"{prefix}{line_separator if target.exists() else ''}{content}"
    with target.open("a", encoding="utf-8") as handle:
        handle.write(rendered)
    return {"path": str(target), "bytes_written": len(rendered.encode('utf-8')), "size_bytes": target.stat().st_size}


def write_file(path: str, content: str, *, if_exists: str = "error", encoding: str = "utf-8", create_parents: bool = True) -> dict[str, Any]:
    target = _path(path)
    if create_parents:
        target.parent.mkdir(parents=True, exist_ok=True)
    backup_path = None
    if target.exists():
        if if_exists == "error":
            raise ValueError(f"Target '{target}' already exists.")
        if if_exists == "backup":
            backup_path = target.with_suffix(f"{target.suffix}.bak.{datetime.utcnow().strftime('%Y%m%d%H%M%S')}")
            target.replace(backup_path)
    target.write_text(content, encoding=encoding)
    return {"path": str(target), "bytes_written": len(content.encode(encoding)), "backup_path": str(backup_path) if backup_path else None}


def stat_path(path: str, *, inspect_mime: bool = True) -> dict[str, Any]:
    target = _path(path)
    if not target.exists():
        raise ValueError(f"Path '{target}' does not exist.")
    stat = target.stat()
    mime_type = mimetypes.guess_type(target.name)[0] if inspect_mime else None
    sample = target.read_bytes()[:512] if inspect_mime and target.is_file() else b""
    is_text = target.is_dir() or not b"\x00" in sample
    return {"path": str(target), "size_bytes": stat.st_size, "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(), "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(), "accessed_at": datetime.fromtimestamp(stat.st_atime).isoformat(), "permissions": oct(stat.st_mode)[-3:], "mime_type": mime_type, "is_text": is_text}


def find_paths(root: str, pattern: str, *, entry_type: str = "file", min_size_bytes: int | None = None, max_size_bytes: int | None = None, modified_after: str | None = None, max_results: int = 100, sort_by: str = "mtime_desc") -> list[dict[str, Any]]:
    threshold = datetime.fromisoformat(modified_after) if modified_after else None
    results: list[dict[str, Any]] = []
    for path in _path(root).rglob(pattern):
        if entry_type == "file" and not path.is_file():
            continue
        if entry_type == "directory" and not path.is_dir():
            continue
        stat = path.stat()
        if min_size_bytes is not None and stat.st_size < min_size_bytes:
            continue
        if max_size_bytes is not None and stat.st_size > max_size_bytes:
            continue
        if threshold is not None and datetime.fromtimestamp(stat.st_mtime) <= threshold:
            continue
        results.append({"path": str(path), "size_bytes": stat.st_size, "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat()})
    results.sort(key=lambda item: _sort_value(item, sort_by), reverse=sort_by in {"mtime_desc", "size_desc"})
    return results[:max_results]


def diff_inputs(left: str, right: str, *, input_mode: str = "files", format: str = "unified", context_lines: int = 3, left_label: str = "left", right_label: str = "right") -> dict[str, Any]:
    if input_mode == "files":
        left_lines = _path(left).read_text(encoding="utf-8").splitlines()
        right_lines = _path(right).read_text(encoding="utf-8").splitlines()
    else:
        left_lines = left.splitlines()
        right_lines = right.splitlines()
    if format == "summary":
        matcher = difflib.SequenceMatcher(a=left_lines, b=right_lines)
        summary = {"lines_added": 0, "lines_removed": 0, "lines_changed": 0, "lines_unchanged": 0}
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "equal":
                summary["lines_unchanged"] += i2 - i1
            elif tag == "insert":
                summary["lines_added"] += j2 - j1
            elif tag == "delete":
                summary["lines_removed"] += i2 - i1
            else:
                summary["lines_changed"] += max(i2 - i1, j2 - j1)
        return summary
    if format == "side_by_side":
        width = max([len(line) for line in left_lines + right_lines], default=0)
        rows = [f"{l:<{width}} | {r}" for l, r in zip(left_lines, right_lines, strict=False)]
        return {"diff": "\n".join(rows)}
    return {"diff": "\n".join(difflib.unified_diff(left_lines, right_lines, fromfile=left_label, tofile=right_label, n=context_lines, lineterm=""))}


def create_filesystem_safe_tools() -> tuple[RegisteredTool, ...]:
    return (
        RegisteredTool(_tool(FILESYSTEM_SAFE_READ, "read", {"path": {"type": "string"}, "max_bytes": {"type": ["integer", "null"]}, "lines": {"type": ["object", "null"]}, "encoding": {"type": ["string", "null"]}}, "Read a text file safely.", ("path",)), _read_tool),
        RegisteredTool(_tool(FILESYSTEM_SAFE_LIST, "list", {"path": {"type": "string"}, "recursive": {"type": "boolean"}, "max_depth": {"type": "integer"}, "pattern": {"type": ["string", "null"]}, "include_hidden": {"type": "boolean"}, "summary_only": {"type": "boolean"}}, "List a directory.", ("path",)), _list_tool),
        RegisteredTool(_tool(FILESYSTEM_SAFE_EXISTS, "exists", {"path": {"type": "string"}, "expect_type": {"type": ["string", "null"]}, "follow_symlinks": {"type": "boolean"}}, "Check path existence.", ("path",)), _exists_tool),
        RegisteredTool(_tool(FILESYSTEM_SAFE_COPY, "copy", {"source": {"type": "string"}, "destination": {"type": "string"}, "if_exists": {"type": "string", "enum": ["error", "overwrite", "rename"]}, "create_parents": {"type": "boolean"}}, "Copy a file safely.", ("source", "destination")), _copy_tool),
        RegisteredTool(_tool(FILESYSTEM_SAFE_APPEND, "append", {"path": {"type": "string"}, "content": {"type": "string"}, "line_separator": {"type": "string"}, "ensure_newline_before": {"type": "boolean"}, "create_parents": {"type": "boolean"}}, "Append to a file.", ("path", "content")), _append_tool),
        RegisteredTool(_tool(FILESYSTEM_SAFE_WRITE, "write", {"path": {"type": "string"}, "content": {"type": "string"}, "if_exists": {"type": "string", "enum": ["error", "overwrite", "backup"]}, "encoding": {"type": "string"}, "create_parents": {"type": "boolean"}}, "Write a file with overwrite protection.", ("path", "content")), _write_tool),
        RegisteredTool(_tool(FILESYSTEM_SAFE_STAT, "stat", {"path": {"type": "string"}, "inspect_mime": {"type": "boolean"}}, "Inspect file metadata.", ("path",)), _stat_tool),
        RegisteredTool(_tool(FILESYSTEM_SAFE_FIND, "find", {"root": {"type": "string"}, "pattern": {"type": "string"}, "type": {"type": "string", "enum": ["file", "directory", "any"]}, "min_size_bytes": {"type": ["integer", "null"]}, "max_size_bytes": {"type": ["integer", "null"]}, "modified_after": {"type": ["string", "null"]}, "max_results": {"type": "integer"}, "sort_by": {"type": "string", "enum": ["mtime_desc", "mtime_asc", "name_asc", "size_desc"]}}, "Find matching paths.", ("root", "pattern")), _find_tool),
        RegisteredTool(_tool(FILESYSTEM_SAFE_DIFF, "diff", {"left": {"type": "string"}, "right": {"type": "string"}, "input_mode": {"type": "string", "enum": ["files", "strings"]}, "format": {"type": "string", "enum": ["unified", "side_by_side", "summary"]}, "context_lines": {"type": "integer"}, "left_label": {"type": "string"}, "right_label": {"type": "string"}}, "Diff files or strings.", ("left", "right")), _diff_tool),
    )


def _read_tool(arguments: ToolArguments) -> dict[str, Any]:
    return read_file(_str(arguments, "path"), max_bytes=_opt_int(arguments, "max_bytes"), lines=arguments.get("lines"), encoding=_opt_str(arguments, "encoding"))


def _list_tool(arguments: ToolArguments) -> dict[str, Any]:
    return list_directory(_str(arguments, "path"), recursive=_bool(arguments, "recursive", False), max_depth=_int(arguments, "max_depth", 3), pattern=_opt_str(arguments, "pattern"), include_hidden=_bool(arguments, "include_hidden", False), summary_only=_bool(arguments, "summary_only", False))


def _exists_tool(arguments: ToolArguments) -> dict[str, Any]:
    return exists(_str(arguments, "path"), expect_type=_opt_str(arguments, "expect_type"), follow_symlinks=_bool(arguments, "follow_symlinks", True))


def _copy_tool(arguments: ToolArguments) -> dict[str, Any]:
    return copy_path(_str(arguments, "source"), _str(arguments, "destination"), if_exists=_str(arguments, "if_exists", "error"), create_parents=_bool(arguments, "create_parents", True))


def _append_tool(arguments: ToolArguments) -> dict[str, Any]:
    return append_file(_str(arguments, "path"), _str(arguments, "content"), line_separator=_str(arguments, "line_separator", "\n"), ensure_newline_before=_bool(arguments, "ensure_newline_before", True), create_parents=_bool(arguments, "create_parents", True))


def _write_tool(arguments: ToolArguments) -> dict[str, Any]:
    return write_file(_str(arguments, "path"), _str(arguments, "content"), if_exists=_str(arguments, "if_exists", "error"), encoding=_str(arguments, "encoding", "utf-8"), create_parents=_bool(arguments, "create_parents", True))


def _stat_tool(arguments: ToolArguments) -> dict[str, Any]:
    return stat_path(_str(arguments, "path"), inspect_mime=_bool(arguments, "inspect_mime", True))


def _find_tool(arguments: ToolArguments) -> dict[str, Any]:
    return {"results": find_paths(_str(arguments, "root"), _str(arguments, "pattern"), entry_type=_str(arguments, "type", "file"), min_size_bytes=_opt_int(arguments, "min_size_bytes"), max_size_bytes=_opt_int(arguments, "max_size_bytes"), modified_after=_opt_str(arguments, "modified_after"), max_results=_int(arguments, "max_results", 100), sort_by=_str(arguments, "sort_by", "mtime_desc"))}


def _diff_tool(arguments: ToolArguments) -> dict[str, Any]:
    return diff_inputs(_str(arguments, "left"), _str(arguments, "right"), input_mode=_str(arguments, "input_mode", "files"), format=_str(arguments, "format", "unified"), context_lines=_int(arguments, "context_lines", 3), left_label=_str(arguments, "left_label", "left"), right_label=_str(arguments, "right_label", "right"))


def _walk(root: Path, *, recursive: bool, max_depth: int, include_hidden: bool, pattern: str | None):
    for child in root.iterdir():
        if not include_hidden and child.name.startswith("."):
            continue
        if pattern is not None and not child.match(pattern):
            if not (recursive and child.is_dir()):
                continue
        yield {"name": child.name, "path": str(child), "type": "directory" if child.is_dir() else "file", "size_bytes": child.stat().st_size if child.is_file() else 0, "modified_at": datetime.fromtimestamp(child.stat().st_mtime).isoformat()}
        if recursive and child.is_dir() and max_depth > 1:
            yield from _walk(child, recursive=True, max_depth=max_depth - 1, include_hidden=include_hidden, pattern=pattern)


def _detect_encoding(raw: bytes) -> str:
    best = from_bytes(raw).best()
    return best.encoding if best and best.encoding else "utf-8"


def _crc32(path: Path) -> int:
    return zlib.crc32(path.read_bytes())


def _sort_value(item: dict[str, Any], sort_by: str) -> Any:
    if sort_by.startswith("mtime"):
        return item["modified_at"]
    if sort_by == "size_desc":
        return item["size_bytes"]
    return Path(item["path"]).name.lower()


def _path(value: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Path arguments must be non-empty strings.")
    return Path(value).expanduser().resolve()


def _tool(key: str, name: str, properties: dict[str, object], description: str, required: Sequence[str]) -> ToolDefinition:
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


def _int(arguments: ToolArguments, key: str, default: int | None = None) -> int:
    if key not in arguments:
        if default is None:
            raise ValueError(f"The '{key}' argument is required.")
        return default
    value = arguments[key]
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"The '{key}' argument must be an integer.")
    return value


def _opt_int(arguments: ToolArguments, key: str) -> int | None:
    if key not in arguments or arguments[key] is None:
        return None
    return _int(arguments, key)


def _bool(arguments: ToolArguments, key: str, default: bool) -> bool:
    value = arguments.get(key, default)
    if not isinstance(value, bool):
        raise ValueError(f"The '{key}' argument must be a boolean.")
    return value


__all__ = ["append_file", "copy_path", "create_filesystem_safe_tools", "diff_inputs", "exists", "find_paths", "list_directory", "read_file", "stat_path", "write_file"]
