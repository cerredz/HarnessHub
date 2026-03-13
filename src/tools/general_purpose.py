"""General-purpose text, record, and control-flow tools."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from copy import deepcopy
from typing import Any, Literal

from src.shared.agents import AgentPauseSignal
from src.shared.tools import (
    CONTROL_PAUSE_FOR_HUMAN,
    RECORDS_COUNT_BY_FIELD,
    RECORDS_FILTER_RECORDS,
    RECORDS_LIMIT_RECORDS,
    RECORDS_SELECT_FIELDS,
    RECORDS_SORT_RECORDS,
    RECORDS_UNIQUE_RECORDS,
    RegisteredTool,
    TEXT_NORMALIZE_WHITESPACE,
    TEXT_REGEX_EXTRACT,
    TEXT_TRUNCATE_TEXT,
    ToolArguments,
    ToolDefinition,
)

FilterOperator = Literal["eq", "ne", "contains", "in", "not_in", "gt", "gte", "lt", "lte"]
TruncatePosition = Literal["start", "middle", "end"]
_RECORDS_PROPERTY: dict[str, object] = {
    "type": "array",
    "description": "An ordered list of JSON-like record objects.",
    "items": {"type": "object"},
}
_FILTER_OPERATORS = frozenset({"eq", "ne", "contains", "in", "not_in", "gt", "gte", "lt", "lte"})
_TRUNCATE_POSITIONS = frozenset({"start", "middle", "end"})


def normalize_whitespace(text: str, *, preserve_newlines: bool = False) -> str:
    """Collapse repeated whitespace into a stable form."""
    if preserve_newlines:
        return "\n".join(" ".join(line.split()) for line in text.splitlines()).strip()
    return " ".join(text.split())


def regex_extract(
    text: str,
    pattern: str,
    *,
    ignore_case: bool = False,
    multiline: bool = False,
) -> list[dict[str, object]]:
    """Return structured regex matches for the provided text."""
    flags = 0
    if ignore_case:
        flags |= re.IGNORECASE
    if multiline:
        flags |= re.MULTILINE

    try:
        compiled = re.compile(pattern, flags)
    except re.error as exc:
        raise ValueError(f"Invalid regex pattern: {exc}") from exc

    matches: list[dict[str, object]] = []
    for match in compiled.finditer(text):
        payload: dict[str, object] = {
            "match": match.group(0),
            "span": [match.start(), match.end()],
        }
        groups = list(match.groups())
        if groups:
            payload["groups"] = groups
        named_groups = {key: value for key, value in match.groupdict().items() if value is not None}
        if named_groups:
            payload["named_groups"] = named_groups
        matches.append(payload)
    return matches


def truncate_text(
    text: str,
    max_length: int,
    *,
    position: TruncatePosition = "end",
    ellipsis: str = "...",
) -> str:
    """Trim text to a deterministic maximum length."""
    if max_length < 0:
        raise ValueError("max_length must be greater than or equal to zero.")
    if position not in _TRUNCATE_POSITIONS:
        raise ValueError(f"Unsupported truncate position '{position}'.")
    if len(text) <= max_length:
        return text
    if max_length == 0:
        return ""
    if max_length <= len(ellipsis):
        return ellipsis[:max_length]

    available = max_length - len(ellipsis)
    if position == "start":
        return f"{ellipsis}{text[-available:]}"
    if position == "middle":
        head = (available + 1) // 2
        tail = available // 2
        suffix = text[-tail:] if tail else ""
        return f"{text[:head]}{ellipsis}{suffix}"
    return f"{text[:available]}{ellipsis}"


def select_fields(
    records: list[Mapping[str, Any]],
    fields: Sequence[str],
    *,
    include_missing: bool = False,
) -> list[dict[str, Any]]:
    """Project each record to a smaller field set."""
    normalized_records = _normalize_records(records)
    normalized_fields = _normalize_fields(fields)
    projected: list[dict[str, Any]] = []
    for record in normalized_records:
        item: dict[str, Any] = {}
        for field in normalized_fields:
            if field in record:
                item[field] = deepcopy(record[field])
            elif include_missing:
                item[field] = None
        projected.append(item)
    return projected


def filter_records(
    records: list[Mapping[str, Any]],
    *,
    field: str,
    operator: FilterOperator,
    value: Any,
    case_insensitive: bool = False,
) -> list[dict[str, Any]]:
    """Return records matching a simple top-level field comparison."""
    if operator not in _FILTER_OPERATORS:
        raise ValueError(f"Unsupported filter operator '{operator}'.")

    normalized_records = _normalize_records(records)
    return [
        record
        for record in normalized_records
        if _matches_filter(record.get(field), operator, value, case_insensitive=case_insensitive)
    ]


def sort_records(
    records: list[Mapping[str, Any]],
    *,
    field: str,
    descending: bool = False,
    missing_last: bool = True,
) -> list[dict[str, Any]]:
    """Sort records deterministically by a single top-level field."""
    normalized_records = _normalize_records(records)
    present = [record for record in normalized_records if field in record and record[field] is not None]
    missing = [record for record in normalized_records if field not in record or record[field] is None]
    sorted_present = sorted(present, key=lambda record: _sortable_value(record[field]), reverse=descending)
    if missing_last:
        return [*sorted_present, *missing]
    return [*missing, *sorted_present]


def limit_records(
    records: list[Mapping[str, Any]],
    *,
    limit: int,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """Return a bounded slice of records."""
    normalized_records = _normalize_records(records)
    if limit < 0:
        raise ValueError("limit must be greater than or equal to zero.")
    if offset < 0:
        raise ValueError("offset must be greater than or equal to zero.")
    return normalized_records[offset : offset + limit]


def unique_records(
    records: list[Mapping[str, Any]],
    *,
    field: str | None = None,
) -> list[dict[str, Any]]:
    """Remove duplicates while preserving first-seen order."""
    normalized_records = _normalize_records(records)
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for record in normalized_records:
        value = record.get(field) if field is not None else record
        signature = _signature(value)
        if signature in seen:
            continue
        seen.add(signature)
        unique.append(record)
    return unique


def count_by_field(records: list[Mapping[str, Any]], *, field: str) -> list[dict[str, Any]]:
    """Count records by one top-level field while preserving first-seen order."""
    normalized_records = _normalize_records(records)
    counts: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for record in normalized_records:
        value = deepcopy(record.get(field))
        signature = _signature(value)
        if signature not in counts:
            counts[signature] = {"value": value, "count": 0}
            order.append(signature)
        counts[signature]["count"] += 1
    return [counts[signature] for signature in order]


def pause_for_human(reason: str, *, details: Mapping[str, Any] | None = None) -> AgentPauseSignal:
    """Return a structured pause signal for the agent runtime."""
    payload = deepcopy(dict(details)) if details is not None else None
    return AgentPauseSignal(reason=reason, details=payload)


def create_general_purpose_tools() -> tuple[RegisteredTool, ...]:
    """Return the registered tool set for broad agent reuse."""
    return (
        RegisteredTool(
            definition=_tool_definition(
                key=TEXT_NORMALIZE_WHITESPACE,
                name="normalize_whitespace",
                description="Collapse repeated whitespace into a stable text form.",
                properties={
                    "text": {"type": "string", "description": "The text to normalize."},
                    "preserve_newlines": {
                        "type": "boolean",
                        "description": "Keep line breaks while collapsing whitespace within each line.",
                    },
                },
                required=("text",),
            ),
            handler=_normalize_whitespace_tool,
        ),
        RegisteredTool(
            definition=_tool_definition(
                key=TEXT_REGEX_EXTRACT,
                name="regex_extract",
                description="Extract structured regex matches from text.",
                properties={
                    "text": {"type": "string", "description": "The text to search."},
                    "pattern": {"type": "string", "description": "The regex pattern to apply."},
                    "ignore_case": {
                        "type": "boolean",
                        "description": "Whether to compile the pattern case-insensitively.",
                    },
                    "multiline": {
                        "type": "boolean",
                        "description": "Whether ^ and $ should match line boundaries.",
                    },
                },
                required=("text", "pattern"),
            ),
            handler=_regex_extract_tool,
        ),
        RegisteredTool(
            definition=_tool_definition(
                key=TEXT_TRUNCATE_TEXT,
                name="truncate_text",
                description="Trim text to a maximum length with a deterministic truncation strategy.",
                properties={
                    "text": {"type": "string", "description": "The text to trim."},
                    "max_length": {"type": "integer", "description": "Maximum allowed text length."},
                    "position": {
                        "type": "string",
                        "enum": ["start", "middle", "end"],
                        "description": "Where to place the ellipsis relative to retained content.",
                    },
                    "ellipsis": {
                        "type": "string",
                        "description": "Marker inserted when the text is truncated.",
                    },
                },
                required=("text", "max_length"),
            ),
            handler=_truncate_text_tool,
        ),
        RegisteredTool(
            definition=_tool_definition(
                key=RECORDS_SELECT_FIELDS,
                name="select_fields",
                description="Project each record to a smaller set of fields.",
                properties={
                    "records": _records_property(),
                    "fields": {
                        "type": "array",
                        "description": "Ordered list of field names to retain.",
                        "items": {"type": "string"},
                    },
                    "include_missing": {
                        "type": "boolean",
                        "description": "Include requested fields with null values when missing.",
                    },
                },
                required=("records", "fields"),
            ),
            handler=_select_fields_tool,
        ),
        RegisteredTool(
            definition=_tool_definition(
                key=RECORDS_FILTER_RECORDS,
                name="filter_records",
                description="Filter records by a simple top-level field comparison.",
                properties={
                    "records": _records_property(),
                    "field": {"type": "string", "description": "Field name to compare."},
                    "operator": {
                        "type": "string",
                        "enum": sorted(_FILTER_OPERATORS),
                        "description": "Comparison operator to apply.",
                    },
                    "value": {"description": "Comparison value used by the selected operator."},
                    "case_insensitive": {
                        "type": "boolean",
                        "description": "Lower-case string comparisons before matching.",
                    },
                },
                required=("records", "field", "operator", "value"),
            ),
            handler=_filter_records_tool,
        ),
        RegisteredTool(
            definition=_tool_definition(
                key=RECORDS_SORT_RECORDS,
                name="sort_records",
                description="Sort records by a single top-level field.",
                properties={
                    "records": _records_property(),
                    "field": {"type": "string", "description": "Field name to sort by."},
                    "descending": {
                        "type": "boolean",
                        "description": "Sort from highest to lowest when true.",
                    },
                    "missing_last": {
                        "type": "boolean",
                        "description": "Keep records with missing values after sortable records.",
                    },
                },
                required=("records", "field"),
            ),
            handler=_sort_records_tool,
        ),
        RegisteredTool(
            definition=_tool_definition(
                key=RECORDS_LIMIT_RECORDS,
                name="limit_records",
                description="Return a bounded slice of records.",
                properties={
                    "records": _records_property(),
                    "limit": {"type": "integer", "description": "Maximum number of records to return."},
                    "offset": {
                        "type": "integer",
                        "description": "Number of leading records to skip before limiting.",
                    },
                },
                required=("records", "limit"),
            ),
            handler=_limit_records_tool,
        ),
        RegisteredTool(
            definition=_tool_definition(
                key=RECORDS_UNIQUE_RECORDS,
                name="unique_records",
                description="Remove duplicate records while preserving first-seen order.",
                properties={
                    "records": _records_property(),
                    "field": {
                        "type": "string",
                        "description": "Optional field used as the uniqueness key instead of the full record.",
                    },
                },
                required=("records",),
            ),
            handler=_unique_records_tool,
        ),
        RegisteredTool(
            definition=_tool_definition(
                key=RECORDS_COUNT_BY_FIELD,
                name="count_by_field",
                description="Count records grouped by a single top-level field.",
                properties={
                    "records": _records_property(),
                    "field": {"type": "string", "description": "Field name to count by."},
                },
                required=("records", "field"),
            ),
            handler=_count_by_field_tool,
        ),
        RegisteredTool(
            definition=_tool_definition(
                key=CONTROL_PAUSE_FOR_HUMAN,
                name="pause_for_human",
                description="Return a structured pause signal so a human can review or unblock the workflow.",
                properties={
                    "reason": {"type": "string", "description": "Why human intervention is required."},
                    "details": {
                        "type": "object",
                        "description": "Optional structured context for the person reviewing the pause.",
                    },
                },
                required=("reason",),
            ),
            handler=_pause_for_human_tool,
        ),
    )


def _normalize_whitespace_tool(arguments: ToolArguments) -> dict[str, object]:
    text = _require_string(arguments, "text")
    preserve_newlines = _require_bool(arguments, "preserve_newlines", default=False)
    return {"text": normalize_whitespace(text, preserve_newlines=preserve_newlines)}


def _regex_extract_tool(arguments: ToolArguments) -> dict[str, object]:
    text = _require_string(arguments, "text")
    pattern = _require_string(arguments, "pattern")
    ignore_case = _require_bool(arguments, "ignore_case", default=False)
    multiline = _require_bool(arguments, "multiline", default=False)
    matches = regex_extract(text, pattern, ignore_case=ignore_case, multiline=multiline)
    return {"matches": matches, "count": len(matches)}


def _truncate_text_tool(arguments: ToolArguments) -> dict[str, object]:
    text = _require_string(arguments, "text")
    max_length = _require_int(arguments, "max_length")
    position = _require_optional_string(arguments, "position") or "end"
    ellipsis = _require_optional_string(arguments, "ellipsis") or "..."
    truncated_text = truncate_text(text, max_length, position=position, ellipsis=ellipsis)
    return {
        "text": truncated_text,
        "truncated": truncated_text != text,
        "original_length": len(text),
    }


def _select_fields_tool(arguments: ToolArguments) -> dict[str, object]:
    records = _require_records(arguments, "records")
    fields = _require_string_sequence(arguments, "fields")
    include_missing = _require_bool(arguments, "include_missing", default=False)
    return {"records": select_fields(records, fields, include_missing=include_missing)}


def _filter_records_tool(arguments: ToolArguments) -> dict[str, object]:
    records = _require_records(arguments, "records")
    field = _require_string(arguments, "field")
    operator = _require_string(arguments, "operator")
    case_insensitive = _require_bool(arguments, "case_insensitive", default=False)
    filtered = filter_records(
        records,
        field=field,
        operator=operator,
        value=arguments["value"],
        case_insensitive=case_insensitive,
    )
    return {"records": filtered, "count": len(filtered)}


def _sort_records_tool(arguments: ToolArguments) -> dict[str, object]:
    records = _require_records(arguments, "records")
    field = _require_string(arguments, "field")
    descending = _require_bool(arguments, "descending", default=False)
    missing_last = _require_bool(arguments, "missing_last", default=True)
    return {
        "records": sort_records(
            records,
            field=field,
            descending=descending,
            missing_last=missing_last,
        )
    }


def _limit_records_tool(arguments: ToolArguments) -> dict[str, object]:
    records = _require_records(arguments, "records")
    limit = _require_int(arguments, "limit")
    offset = _require_int(arguments, "offset", default=0)
    limited = limit_records(records, limit=limit, offset=offset)
    return {
        "records": limited,
        "count": len(limited),
        "total": len(records),
    }


def _unique_records_tool(arguments: ToolArguments) -> dict[str, object]:
    records = _require_records(arguments, "records")
    field = _require_optional_string(arguments, "field")
    unique = unique_records(records, field=field)
    return {
        "records": unique,
        "duplicates_removed": len(records) - len(unique),
    }


def _count_by_field_tool(arguments: ToolArguments) -> dict[str, object]:
    records = _require_records(arguments, "records")
    field = _require_string(arguments, "field")
    counts = count_by_field(records, field=field)
    return {
        "counts": counts,
        "total": len(records),
    }


def _pause_for_human_tool(arguments: ToolArguments) -> AgentPauseSignal:
    reason = _require_string(arguments, "reason")
    details = _require_optional_mapping(arguments, "details")
    return pause_for_human(reason, details=details)


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


def _require_int(arguments: ToolArguments, key: str, *, default: int | None = None) -> int:
    if key not in arguments:
        if default is None:
            raise ValueError(f"The '{key}' argument is required.")
        return default
    value = arguments[key]
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"The '{key}' argument must be an integer.")
    return value


def _require_records(arguments: ToolArguments, key: str) -> list[Mapping[str, Any]]:
    value = arguments[key]
    if not isinstance(value, list):
        raise ValueError(f"The '{key}' argument must be a list of record mappings.")
    for index, record in enumerate(value):
        if not isinstance(record, Mapping):
            raise ValueError(f"Record at index {index} must be a mapping.")
    return value


def _require_string_sequence(arguments: ToolArguments, key: str) -> list[str]:
    value = arguments[key]
    if not isinstance(value, list):
        raise ValueError(f"The '{key}' argument must be a list of strings.")
    return _normalize_fields(value)


def _require_optional_mapping(arguments: ToolArguments, key: str) -> Mapping[str, Any] | None:
    if key not in arguments or arguments[key] is None:
        return None
    value = arguments[key]
    if not isinstance(value, Mapping):
        raise ValueError(f"The '{key}' argument must be an object when provided.")
    return value


def _normalize_fields(fields: Sequence[str]) -> list[str]:
    normalized: list[str] = []
    for index, field in enumerate(fields):
        if not isinstance(field, str):
            raise ValueError(f"Field at index {index} must be a string.")
        normalized.append(field)
    return normalized


def _normalize_records(records: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for index, record in enumerate(records):
        if not isinstance(record, Mapping):
            raise ValueError(f"Record at index {index} must be a mapping.")
        normalized.append(deepcopy(dict(record)))
    return normalized


def _matches_filter(
    candidate: Any,
    operator: FilterOperator,
    value: Any,
    *,
    case_insensitive: bool,
) -> bool:
    left = _normalize_string(candidate, case_insensitive=case_insensitive)
    right = _normalize_string(value, case_insensitive=case_insensitive)

    if operator == "eq":
        return left == right
    if operator == "ne":
        return left != right
    if operator == "contains":
        if isinstance(left, str) and isinstance(right, str):
            return right in left
        if isinstance(candidate, Sequence) and not isinstance(candidate, (str, bytes, bytearray)):
            return any(_normalize_string(item, case_insensitive=case_insensitive) == right for item in candidate)
        return False
    if operator in {"in", "not_in"}:
        if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
            raise ValueError(f"The '{operator}' operator requires a list-like comparison value.")
        normalized_values = [_normalize_string(item, case_insensitive=case_insensitive) for item in value]
        is_member = left in normalized_values
        return is_member if operator == "in" else not is_member

    left_comparable = _coerce_comparable(candidate)
    right_comparable = _coerce_comparable(value)
    if left_comparable is None or right_comparable is None:
        return False
    if operator == "gt":
        return left_comparable > right_comparable
    if operator == "gte":
        return left_comparable >= right_comparable
    if operator == "lt":
        return left_comparable < right_comparable
    return left_comparable <= right_comparable


def _normalize_string(value: Any, *, case_insensitive: bool) -> Any:
    if case_insensitive and isinstance(value, str):
        return value.lower()
    return value


def _coerce_comparable(value: Any) -> float | str | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return float(int(value))
    if isinstance(value, (int, float)):
        return float(value)
    return str(value)


def _sortable_value(value: Any) -> tuple[int, float | str]:
    if isinstance(value, bool):
        return (0, float(int(value)))
    if isinstance(value, (int, float)):
        return (1, float(value))
    return (2, str(value).lower())


def _signature(value: Any) -> str:
    return json.dumps(value, sort_keys=True, default=str)


def _records_property() -> dict[str, object]:
    return deepcopy(_RECORDS_PROPERTY)


__all__ = [
    "FilterOperator",
    "TruncatePosition",
    "count_by_field",
    "create_general_purpose_tools",
    "filter_records",
    "limit_records",
    "normalize_whitespace",
    "pause_for_human",
    "regex_extract",
    "select_fields",
    "sort_records",
    "truncate_text",
    "unique_records",
]

