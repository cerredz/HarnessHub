"""Explicit non-destructive filesystem tools."""

from __future__ import annotations

import shutil
from collections.abc import Sequence
from copy import deepcopy
from pathlib import Path
from typing import Any

from harnessiq.shared.tools import (
    FILESYSTEM_APPEND_TEXT_FILE,
    FILESYSTEM_COPY_PATH,
    FILESYSTEM_GET_CURRENT_DIRECTORY,
    FILESYSTEM_LIST_DIRECTORY,
    FILESYSTEM_MAKE_DIRECTORY,
    FILESYSTEM_PATH_EXISTS,
    FILESYSTEM_READ_TEXT_FILE,
    FILESYSTEM_REPLACE_TEXT_FILE,
    FILESYSTEM_WRITE_TEXT_FILE,
    RegisteredTool,
    ToolArguments,
    ToolDefinition,
)

_PATH_PROPERTY = {"type": "string", "description": "A filesystem path. Relative paths resolve from the current working directory."}


def get_current_directory() -> str:
    """Return the current working directory."""
    return str(Path.cwd())


def path_exists(path: str) -> dict[str, object]:
    """Return existence metadata for a path."""
    normalized = _normalize_path(path)
    exists = normalized.exists()
    return {
        "path": str(normalized),
        "exists": exists,
        "is_file": normalized.is_file() if exists else False,
        "is_dir": normalized.is_dir() if exists else False,
    }


def list_directory(path: str, *, max_entries: int = 200) -> list[dict[str, object]]:
    """List entries in a directory."""
    if max_entries < 0:
        raise ValueError("max_entries must be greater than or equal to zero.")
    directory = _require_existing_path(path)
    if not directory.is_dir():
        raise ValueError(f"Path '{directory}' is not a directory.")
    entries = sorted(directory.iterdir(), key=lambda item: (not item.is_dir(), item.name.lower()))
    limited_entries = entries[:max_entries]
    return [_describe_child_path(entry) for entry in limited_entries]


def read_text_file(path: str, *, encoding: str = "utf-8", max_chars: int = 20_000) -> dict[str, object]:
    """Read a text file with optional truncation."""
    if max_chars < 0:
        raise ValueError("max_chars must be greater than or equal to zero.")
    file_path = _require_existing_path(path)
    if not file_path.is_file():
        raise ValueError(f"Path '{file_path}' is not a file.")
    try:
        content = file_path.read_text(encoding=encoding)
    except UnicodeDecodeError as exc:
        raise ValueError(f"Could not decode '{file_path}' with encoding '{encoding}'.") from exc
    truncated = len(content) > max_chars
    visible_content = content[:max_chars] if truncated else content
    return {
        "path": str(file_path),
        "content": visible_content,
        "encoding": encoding,
        "truncated": truncated,
        "character_count": len(content),
    }


def write_text_file(
    path: str,
    content: str,
    *,
    encoding: str = "utf-8",
    create_parents: bool = False,
) -> dict[str, object]:
    """Create a new text file without overwriting existing content."""
    file_path = _normalize_path(path)
    if file_path.exists():
        raise ValueError(f"Path '{file_path}' already exists; overwriting is not allowed.")
    _ensure_parent_directory(file_path, create_parents=create_parents)
    file_path.write_text(content, encoding=encoding)
    return {
        "path": str(file_path),
        "created": True,
        "character_count": len(content),
        "encoding": encoding,
    }


def append_text_file(
    path: str,
    content: str,
    *,
    encoding: str = "utf-8",
    create_parents: bool = False,
) -> dict[str, object]:
    """Append text to a file, creating it if it does not already exist."""
    file_path = _normalize_path(path)
    if file_path.exists() and file_path.is_dir():
        raise ValueError(f"Path '{file_path}' is a directory and cannot be appended to.")
    existed_before = file_path.exists()
    _ensure_parent_directory(file_path, create_parents=create_parents)
    with file_path.open("a", encoding=encoding) as handle:
        handle.write(content)
    return {
        "path": str(file_path),
        "appended": True,
        "created": not existed_before,
        "character_count": len(content),
        "encoding": encoding,
    }


def replace_text_file(
    path: str,
    content: str,
    *,
    encoding: str = "utf-8",
    create_parents: bool = False,
) -> dict[str, object]:
    """Write text to a file, replacing any existing file content."""
    file_path = _normalize_path(path)
    if file_path.exists() and file_path.is_dir():
        raise ValueError(f"Path '{file_path}' is a directory and cannot be overwritten.")
    existed_before = file_path.exists()
    _ensure_parent_directory(file_path, create_parents=create_parents)
    file_path.write_text(content, encoding=encoding)
    return {
        "path": str(file_path),
        "created": not existed_before,
        "overwritten": existed_before,
        "character_count": len(content),
        "encoding": encoding,
    }


def make_directory(path: str, *, parents: bool = True, exist_ok: bool = True) -> dict[str, object]:
    """Create a directory path."""
    directory = _normalize_path(path)
    existed_before = directory.exists()
    if existed_before and not directory.is_dir():
        raise ValueError(f"Path '{directory}' exists and is not a directory.")
    directory.mkdir(parents=parents, exist_ok=exist_ok)
    return {"path": str(directory), "created": not existed_before}


def copy_path(
    source: str,
    destination: str,
    *,
    create_parents: bool = False,
) -> dict[str, object]:
    """Copy a file or directory without overwriting an existing destination."""
    source_path = _require_existing_path(source)
    destination_path = _normalize_path(destination)
    if destination_path.exists():
        raise ValueError(f"Destination '{destination_path}' already exists; overwriting is not allowed.")
    _ensure_parent_directory(destination_path, create_parents=create_parents)
    if source_path.is_dir():
        shutil.copytree(source_path, destination_path)
        copied_type = "directory"
    else:
        shutil.copy2(source_path, destination_path)
        copied_type = "file"
    return {
        "source": str(source_path),
        "destination": str(destination_path),
        "copied_type": copied_type,
    }


def create_filesystem_tools() -> tuple[RegisteredTool, ...]:
    """Return the registered tool set for filesystem access."""
    return (
        RegisteredTool(
            definition=_tool_definition(
                key=FILESYSTEM_GET_CURRENT_DIRECTORY,
                name="get_current_directory",
                description="Return the current working directory.",
                properties={},
            ),
            handler=_get_current_directory_tool,
        ),
        RegisteredTool(
            definition=_tool_definition(
                key=FILESYSTEM_PATH_EXISTS,
                name="path_exists",
                description="Return whether a filesystem path exists and what kind of path it is.",
                properties={"path": deepcopy(_PATH_PROPERTY)},
                required=("path",),
            ),
            handler=_path_exists_tool,
        ),
        RegisteredTool(
            definition=_tool_definition(
                key=FILESYSTEM_LIST_DIRECTORY,
                name="list_directory",
                description="List entries in a directory without modifying the filesystem.",
                properties={
                    "path": deepcopy(_PATH_PROPERTY),
                    "max_entries": {
                        "type": "integer",
                        "description": "Maximum number of directory entries to return.",
                    },
                },
                required=("path",),
            ),
            handler=_list_directory_tool,
        ),
        RegisteredTool(
            definition=_tool_definition(
                key=FILESYSTEM_READ_TEXT_FILE,
                name="read_text_file",
                description="Read a text file with optional truncation.",
                properties={
                    "path": deepcopy(_PATH_PROPERTY),
                    "encoding": {"type": "string", "description": "Text encoding used to decode the file."},
                    "max_chars": {
                        "type": "integer",
                        "description": "Maximum number of characters to return from the file.",
                    },
                },
                required=("path",),
            ),
            handler=_read_text_file_tool,
        ),
        RegisteredTool(
            definition=_tool_definition(
                key=FILESYSTEM_WRITE_TEXT_FILE,
                name="write_text_file",
                description="Create a new text file without overwriting any existing path.",
                properties={
                    "path": deepcopy(_PATH_PROPERTY),
                    "content": {"type": "string", "description": "Full text content to write."},
                    "encoding": {"type": "string", "description": "Text encoding used to encode the file."},
                    "create_parents": {
                        "type": "boolean",
                        "description": "Create missing parent directories before writing.",
                    },
                },
                required=("path", "content"),
            ),
            handler=_write_text_file_tool,
        ),
        RegisteredTool(
            definition=_tool_definition(
                key=FILESYSTEM_REPLACE_TEXT_FILE,
                name="replace_text_file",
                description="Write text to a file, replacing any existing file content.",
                properties={
                    "path": deepcopy(_PATH_PROPERTY),
                    "content": {"type": "string", "description": "Full text content to write."},
                    "encoding": {"type": "string", "description": "Text encoding used to encode the file."},
                    "create_parents": {
                        "type": "boolean",
                        "description": "Create missing parent directories before writing.",
                    },
                },
                required=("path", "content"),
            ),
            handler=_replace_text_file_tool,
        ),
        RegisteredTool(
            definition=_tool_definition(
                key=FILESYSTEM_APPEND_TEXT_FILE,
                name="append_text_file",
                description="Append text to a file, creating it if it does not already exist.",
                properties={
                    "path": deepcopy(_PATH_PROPERTY),
                    "content": {"type": "string", "description": "Text content to append."},
                    "encoding": {"type": "string", "description": "Text encoding used to encode the file."},
                    "create_parents": {
                        "type": "boolean",
                        "description": "Create missing parent directories before appending.",
                    },
                },
                required=("path", "content"),
            ),
            handler=_append_text_file_tool,
        ),
        RegisteredTool(
            definition=_tool_definition(
                key=FILESYSTEM_MAKE_DIRECTORY,
                name="make_directory",
                description="Create a directory path without deleting or overwriting anything.",
                properties={
                    "path": deepcopy(_PATH_PROPERTY),
                    "parents": {
                        "type": "boolean",
                        "description": "Create any missing parent directories.",
                    },
                    "exist_ok": {
                        "type": "boolean",
                        "description": "Treat an existing directory as success.",
                    },
                },
                required=("path",),
            ),
            handler=_make_directory_tool,
        ),
        RegisteredTool(
            definition=_tool_definition(
                key=FILESYSTEM_COPY_PATH,
                name="copy_path",
                description="Copy a file or directory to a new destination path without overwriting.",
                properties={
                    "source": deepcopy(_PATH_PROPERTY),
                    "destination": deepcopy(_PATH_PROPERTY),
                    "create_parents": {
                        "type": "boolean",
                        "description": "Create missing parent directories for the destination path.",
                    },
                },
                required=("source", "destination"),
            ),
            handler=_copy_path_tool,
        ),
    )


def _get_current_directory_tool(arguments: ToolArguments) -> dict[str, str]:
    return {"path": get_current_directory()}


def _path_exists_tool(arguments: ToolArguments) -> dict[str, object]:
    return path_exists(_require_string(arguments, "path"))


def _list_directory_tool(arguments: ToolArguments) -> dict[str, object]:
    path = _require_string(arguments, "path")
    max_entries = _require_int(arguments, "max_entries", default=200)
    entries = list_directory(path, max_entries=max_entries)
    return {"path": str(_normalize_path(path)), "entries": entries, "count": len(entries)}


def _read_text_file_tool(arguments: ToolArguments) -> dict[str, object]:
    path = _require_string(arguments, "path")
    encoding = _require_optional_string(arguments, "encoding") or "utf-8"
    max_chars = _require_int(arguments, "max_chars", default=20_000)
    return read_text_file(path, encoding=encoding, max_chars=max_chars)


def _write_text_file_tool(arguments: ToolArguments) -> dict[str, object]:
    path = _require_string(arguments, "path")
    content = _require_string(arguments, "content")
    encoding = _require_optional_string(arguments, "encoding") or "utf-8"
    create_parents = _require_bool(arguments, "create_parents", default=False)
    return write_text_file(path, content, encoding=encoding, create_parents=create_parents)


def _append_text_file_tool(arguments: ToolArguments) -> dict[str, object]:
    path = _require_string(arguments, "path")
    content = _require_string(arguments, "content")
    encoding = _require_optional_string(arguments, "encoding") or "utf-8"
    create_parents = _require_bool(arguments, "create_parents", default=False)
    return append_text_file(path, content, encoding=encoding, create_parents=create_parents)


def _replace_text_file_tool(arguments: ToolArguments) -> dict[str, object]:
    path = _require_string(arguments, "path")
    content = _require_string(arguments, "content")
    encoding = _require_optional_string(arguments, "encoding") or "utf-8"
    create_parents = _require_bool(arguments, "create_parents", default=False)
    return replace_text_file(path, content, encoding=encoding, create_parents=create_parents)


def _make_directory_tool(arguments: ToolArguments) -> dict[str, object]:
    path = _require_string(arguments, "path")
    parents = _require_bool(arguments, "parents", default=True)
    exist_ok = _require_bool(arguments, "exist_ok", default=True)
    return make_directory(path, parents=parents, exist_ok=exist_ok)


def _copy_path_tool(arguments: ToolArguments) -> dict[str, object]:
    source = _require_string(arguments, "source")
    destination = _require_string(arguments, "destination")
    create_parents = _require_bool(arguments, "create_parents", default=False)
    return copy_path(source, destination, create_parents=create_parents)


def _tool_definition(
    *,
    key: str,
    name: str,
    description: str,
    properties: dict[str, object],
    required: Sequence[str] = (),
) -> ToolDefinition:
    return ToolDefinition(
        key=key,
        name=name,
        description=description,
        input_schema={
            "type": "object",
            "properties": properties,
            "required": list(required),
            "additionalProperties": False,
        },
    )


def _normalize_path(path: str) -> Path:
    if not path.strip():
        raise ValueError("Path arguments must not be empty.")
    return Path(path).expanduser().resolve()


def _require_existing_path(path: str) -> Path:
    normalized = _normalize_path(path)
    if not normalized.exists():
        raise ValueError(f"Path '{normalized}' does not exist.")
    return normalized


def _ensure_parent_directory(path: Path, *, create_parents: bool) -> None:
    parent = path.parent
    if parent.exists():
        if not parent.is_dir():
            raise ValueError(f"Parent path '{parent}' is not a directory.")
        return
    if not create_parents:
        raise ValueError(f"Parent directory '{parent}' does not exist.")
    parent.mkdir(parents=True, exist_ok=True)


def _describe_child_path(path: Path) -> dict[str, object]:
    payload: dict[str, object] = {
        "name": path.name,
        "path": str(path),
        "is_dir": path.is_dir(),
        "is_file": path.is_file(),
    }
    if path.is_file():
        payload["size_bytes"] = path.stat().st_size
    return payload


def _require_string(arguments: ToolArguments, key: str) -> str:
    value = arguments[key]
    if not isinstance(value, str):
        raise ValueError(f"The '{key}' argument must be a string.")
    return value


def _require_optional_string(arguments: ToolArguments, key: str) -> str | None:
    if key not in arguments or arguments[key] is None:
        return None
    value = arguments[key]
    if not isinstance(value, str):
        raise ValueError(f"The '{key}' argument must be a string when provided.")
    return value


def _require_bool(arguments: ToolArguments, key: str, *, default: bool) -> bool:
    if key not in arguments:
        return default
    value = arguments[key]
    if not isinstance(value, bool):
        raise ValueError(f"The '{key}' argument must be a boolean.")
    return value


def _require_int(arguments: ToolArguments, key: str, *, default: int) -> int:
    if key not in arguments:
        return default
    value = arguments[key]
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"The '{key}' argument must be an integer.")
    return value


__all__ = [
    "append_text_file",
    "copy_path",
    "create_filesystem_tools",
    "get_current_directory",
    "list_directory",
    "make_directory",
    "path_exists",
    "read_text_file",
    "replace_text_file",
    "write_text_file",
]
