"""Deterministic record-transformation tools."""

from __future__ import annotations

import json
import math
import statistics
from collections import OrderedDict
from collections.abc import Mapping, Sequence
from copy import deepcopy
from typing import Any

from harnessiq.shared.tools import (
    RECORDS_AGGREGATE,
    RECORDS_COUNT,
    RECORDS_FILTER,
    RECORDS_FLATTEN,
    RECORDS_GROUP_BY,
    RECORDS_JOIN,
    RECORDS_LIMIT,
    RECORDS_RENAME_FIELDS,
    RECORDS_SELECT,
    RECORDS_SORT,
    RECORDS_UNIQUE,
    RegisteredTool,
    ToolArguments,
    ToolDefinition,
)


def filter_records(records: list[Mapping[str, Any]], condition: Mapping[str, Any], *, missing_field_behavior: str = "exclude") -> list[dict[str, Any]]:
    items = _records(records)
    return [item for item in items if _evaluate_condition(item, condition, missing_field_behavior=missing_field_behavior)]


def sort_records(records: list[Mapping[str, Any]], keys: Sequence[Mapping[str, Any]], *, type_coerce: bool = True) -> list[dict[str, Any]]:
    items = _records(records)
    result = items[:]
    for spec in reversed(list(keys)):
        field = _string(spec, "field")
        reverse = _string(spec, "direction", "asc") == "desc"
        nulls = _string(spec, "nulls", "last")
        result.sort(key=lambda record: _sort_key(record.get(field), type_coerce=type_coerce, nulls=nulls), reverse=reverse)
    return result


def select_records(records: list[Mapping[str, Any]], fields: Sequence[Any], *, exclude: Sequence[str] = (), missing_behavior: str = "omit") -> list[dict[str, Any]]:
    items = _records(records)
    excluded = set(exclude)
    projected: list[dict[str, Any]] = []
    for item in items:
        target: dict[str, Any] = {}
        if fields == ["*"]:
            for key, value in item.items():
                if key not in excluded:
                    target[key] = deepcopy(value)
        for field in fields:
            if field == "*":
                continue
            if isinstance(field, str):
                source, destination = field, field
            elif isinstance(field, Mapping):
                source = _string(field, "from")
                destination = _string(field, "to")
            else:
                raise ValueError("Field selectors must be strings or mapping rename specs.")
            if source in item:
                target[destination] = deepcopy(item[source])
            elif missing_behavior == "null":
                target[destination] = None
            elif missing_behavior == "error":
                raise ValueError(f"Missing selected field '{source}'.")
        projected.append(target)
    return projected


def limit_records(records: list[Mapping[str, Any]], n: int, *, offset: int = 0, from_end: bool = False) -> list[dict[str, Any]]:
    items = _records(records)
    if n < 0 or offset < 0:
        raise ValueError("'n' and 'offset' must be non-negative.")
    if from_end:
        end = len(items) - offset
        start = max(0, end - n)
        return items[start:end]
    return items[offset : offset + n]


def unique_records(records: list[Mapping[str, Any]], key_fields: Sequence[str], *, keep: str = "first", longest_field: str | None = None) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    items = _records(records)
    groups: OrderedDict[str, list[dict[str, Any]]] = OrderedDict()
    for item in items:
        groups.setdefault(_signature(tuple(item.get(field) for field in key_fields)), []).append(item)
    kept: list[dict[str, Any]] = []
    dropped: list[dict[str, Any]] = []
    for group in groups.values():
        if keep == "last":
            winner = group[-1]
        elif keep == "longest_field":
            if not longest_field:
                raise ValueError("'longest_field' is required when keep='longest_field'.")
            winner = max(group, key=lambda item: len(str(item.get(longest_field, ""))))
        else:
            winner = group[0]
        kept.append(deepcopy(winner))
        dropped.extend(deepcopy(item) for item in group if item is not winner)
    return kept, dropped


def count_records(records: list[Mapping[str, Any]], *, condition: Mapping[str, Any] | None = None, group_by_field: str | None = None) -> Any:
    items = filter_records(records, condition) if condition is not None else _records(records)
    if group_by_field is None:
        return len(items)
    counts: OrderedDict[str, int] = OrderedDict()
    for item in items:
        key = _signature(item.get(group_by_field))
        counts.setdefault(key, 0)
        counts[key] += 1
    return {json.loads(key): value for key, value in counts.items()}


def group_by_records(records: list[Mapping[str, Any]], field: str, *, multi_key: Sequence[str] | None = None, sort_groups: str = "key_asc") -> OrderedDict[str, list[dict[str, Any]]]:
    items = _records(records)
    groups: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        key_value = "|".join(str(item.get(name)) for name in multi_key) if multi_key else str(item.get(field))
        groups.setdefault(key_value, []).append(item)
    ordered_items = list(groups.items())
    if sort_groups == "key_desc":
        ordered_items.sort(key=lambda pair: pair[0], reverse=True)
    elif sort_groups == "size_asc":
        ordered_items.sort(key=lambda pair: len(pair[1]))
    elif sort_groups == "size_desc":
        ordered_items.sort(key=lambda pair: len(pair[1]), reverse=True)
    else:
        ordered_items.sort(key=lambda pair: pair[0])
    return OrderedDict((key, [deepcopy(item) for item in values]) for key, values in ordered_items)


def aggregate_records(records: list[Mapping[str, Any]], field: str, aggregations: Sequence[Any], *, group_by: str | None = None, on_non_numeric: str = "skip") -> dict[str, Any]:
    items = _records(records)
    grouped = group_by_records(items, group_by, sort_groups="key_asc") if group_by else OrderedDict({"all": items})
    results: list[dict[str, Any]] = []
    for key, values in grouped.items():
        numeric_values, excluded = _numeric_values(values, field, on_non_numeric=on_non_numeric)
        payload: dict[str, Any] = {"group": key, "included_count": len(numeric_values), "excluded_count": excluded}
        for aggregation in aggregations:
            if isinstance(aggregation, str):
                payload[aggregation] = _apply_aggregation(aggregation, numeric_values)
            elif isinstance(aggregation, Mapping) and aggregation.get("type") == "percentile":
                rank = float(aggregation.get("rank", 50))
                payload[f"percentile_{int(rank)}"] = _percentile(numeric_values, rank)
            else:
                raise ValueError("Unsupported aggregation spec.")
        results.append(payload)
    return {"results": results if group_by else results[0]}


def join_records(left: list[Mapping[str, Any]], right: list[Mapping[str, Any]], on: str, *, join_type: str = "inner", conflict_strategy: str = "prefix_right", right_prefix: str = "right_") -> list[dict[str, Any]]:
    left_items = _records(left)
    right_items = _records(right)
    right_index: dict[str, list[dict[str, Any]]] = {}
    for item in right_items:
        right_index.setdefault(_signature(item.get(on)), []).append(item)
    results: list[dict[str, Any]] = []
    matched_right: set[int] = set()
    for left_item in left_items:
        candidates = right_index.get(_signature(left_item.get(on)), [])
        if not candidates and join_type in {"left", "outer"}:
            results.append(_merge_join_pair(left_item, None, on=on, conflict_strategy=conflict_strategy, right_prefix=right_prefix))
        for candidate in candidates:
            matched_right.add(id(candidate))
            results.append(_merge_join_pair(left_item, candidate, on=on, conflict_strategy=conflict_strategy, right_prefix=right_prefix))
    if join_type in {"right", "outer"}:
        for item in right_items:
            if id(item) not in matched_right:
                results.append(_merge_join_pair(None, item, on=on, conflict_strategy=conflict_strategy, right_prefix=right_prefix))
    return results


def rename_fields(records: list[Mapping[str, Any]], mapping: Mapping[str, str], *, strict: bool = False) -> tuple[list[dict[str, Any]], dict[str, list[str]]]:
    items = _records(records)
    applied: set[str] = set()
    renamed: list[dict[str, Any]] = []
    for item in items:
        target: dict[str, Any] = {}
        for key, value in item.items():
            if key in mapping:
                applied.add(key)
                target[mapping[key]] = deepcopy(value)
            else:
                target[key] = deepcopy(value)
        renamed.append(target)
    skipped = sorted(set(mapping) - applied)
    if strict and skipped:
        raise ValueError(f"Mapped fields not present in any record: {', '.join(skipped)}")
    return renamed, {"applied": sorted(applied), "skipped": skipped}


def flatten_records(records: list[Mapping[str, Any]], *, separator: str = ".", depth: int | str = "full", fields: Sequence[str] | None = None, expand_lists: bool = False) -> list[dict[str, Any]]:
    selected = set(fields or [])
    limit = None if depth == "full" else int(depth)
    return [_flatten_dict(item, separator=separator, depth=limit, selected=selected, expand_lists=expand_lists) for item in _records(records)]


def create_records_tools() -> tuple[RegisteredTool, ...]:
    return (
        RegisteredTool(_tool(RECORDS_FILTER, "filter", {"records": {"type": "array", "items": {"type": "object"}}, "condition": {"type": "object"}, "missing_field_behavior": {"type": "string", "enum": ["exclude", "include", "error"]}}, "Filter a record list.", ("records", "condition")), _filter_tool),
        RegisteredTool(_tool(RECORDS_SORT, "sort", {"records": {"type": "array", "items": {"type": "object"}}, "keys": {"type": "array", "items": {"type": "object"}}, "type_coerce": {"type": "boolean"}}, "Sort records.", ("records", "keys")), _sort_tool),
        RegisteredTool(_tool(RECORDS_SELECT, "select", {"records": {"type": "array", "items": {"type": "object"}}, "fields": {"type": "array"}, "exclude": {"type": "array", "items": {"type": "string"}}, "missing_behavior": {"type": "string", "enum": ["omit", "null", "error"]}}, "Project or rename fields.", ("records", "fields")), _select_tool),
        RegisteredTool(_tool(RECORDS_LIMIT, "limit", {"records": {"type": "array", "items": {"type": "object"}}, "n": {"type": "integer"}, "offset": {"type": "integer"}, "from_end": {"type": "boolean"}}, "Take the first or last N records.", ("records", "n")), _limit_tool),
        RegisteredTool(_tool(RECORDS_UNIQUE, "unique", {"records": {"type": "array", "items": {"type": "object"}}, "key_fields": {"type": "array", "items": {"type": "string"}}, "keep": {"type": "string", "enum": ["first", "last", "longest_field"]}, "longest_field": {"type": ["string", "null"]}, "return_dropped": {"type": "boolean"}}, "Deduplicate records.", ("records", "key_fields")), _unique_tool),
        RegisteredTool(_tool(RECORDS_COUNT, "count", {"records": {"type": "array", "items": {"type": "object"}}, "condition": {"type": ["object", "null"]}, "group_by_field": {"type": ["string", "null"]}}, "Count records.", ("records",)), _count_tool),
        RegisteredTool(_tool(RECORDS_GROUP_BY, "group_by", {"records": {"type": "array", "items": {"type": "object"}}, "field": {"type": "string"}, "multi_key": {"type": ["array", "null"], "items": {"type": "string"}}, "sort_groups": {"type": "string", "enum": ["none", "key_asc", "key_desc", "size_asc", "size_desc"]}, "include_summary": {"type": "boolean"}}, "Group records.", ("records", "field")), _group_tool),
        RegisteredTool(_tool(RECORDS_AGGREGATE, "aggregate", {"records": {"type": "array", "items": {"type": "object"}}, "field": {"type": "string"}, "aggregations": {"type": "array"}, "group_by": {"type": ["string", "null"]}, "on_non_numeric": {"type": "string", "enum": ["skip", "zero", "error"]}}, "Aggregate numeric fields.", ("records", "field", "aggregations")), _aggregate_tool),
        RegisteredTool(_tool(RECORDS_JOIN, "join", {"left": {"type": "array", "items": {"type": "object"}}, "right": {"type": "array", "items": {"type": "object"}}, "on": {"type": "string"}, "join_type": {"type": "string", "enum": ["inner", "left", "right", "outer"]}, "conflict_strategy": {"type": "string", "enum": ["prefix_right", "prefix_both", "error"]}, "right_prefix": {"type": "string"}}, "Join record lists.", ("left", "right", "on")), _join_tool),
        RegisteredTool(_tool(RECORDS_RENAME_FIELDS, "rename_fields", {"records": {"type": "array", "items": {"type": "object"}}, "mapping": {"type": "object"}, "strict": {"type": "boolean"}}, "Rename fields.", ("records", "mapping")), _rename_tool),
        RegisteredTool(_tool(RECORDS_FLATTEN, "flatten", {"records": {"type": "array", "items": {"type": "object"}}, "separator": {"type": "string"}, "depth": {"type": ["integer", "string"]}, "fields": {"type": ["array", "null"], "items": {"type": "string"}}, "expand_lists": {"type": "boolean"}}, "Flatten nested dict fields.", ("records",)), _flatten_tool),
    )


def _filter_tool(arguments: ToolArguments) -> dict[str, Any]:
    records = filter_records(_arg_records(arguments, "records"), _arg_object(arguments, "condition"), missing_field_behavior=_arg_str(arguments, "missing_field_behavior", "exclude"))
    return {"records": records, "filtered_out": len(_arg_records(arguments, "records")) - len(records)}


def _sort_tool(arguments: ToolArguments) -> dict[str, Any]:
    return {"records": sort_records(_arg_records(arguments, "records"), _arg_list(arguments, "keys"), type_coerce=_arg_bool(arguments, "type_coerce", True))}


def _select_tool(arguments: ToolArguments) -> dict[str, Any]:
    return {"records": select_records(_arg_records(arguments, "records"), _arg_list(arguments, "fields"), exclude=_arg_str_list(arguments, "exclude"), missing_behavior=_arg_str(arguments, "missing_behavior", "omit"))}


def _limit_tool(arguments: ToolArguments) -> dict[str, Any]:
    original = _arg_records(arguments, "records")
    limited = limit_records(original, _arg_int(arguments, "n"), offset=_arg_int(arguments, "offset", 0), from_end=_arg_bool(arguments, "from_end", False))
    return {"records": limited, "total": len(original), "count": len(limited), "has_more": len(limited) < max(0, len(original) - _arg_int(arguments, "offset", 0))}


def _unique_tool(arguments: ToolArguments) -> dict[str, Any]:
    unique, dropped = unique_records(_arg_records(arguments, "records"), _arg_str_list(arguments, "key_fields"), keep=_arg_str(arguments, "keep", "first"), longest_field=_arg_opt_str(arguments, "longest_field"))
    payload = {"records": unique, "duplicates_removed": len(dropped)}
    if _arg_bool(arguments, "return_dropped", False):
        payload["dropped"] = dropped
    return payload


def _count_tool(arguments: ToolArguments) -> dict[str, Any]:
    return {"count": count_records(_arg_records(arguments, "records"), condition=arguments.get("condition"), group_by_field=_arg_opt_str(arguments, "group_by_field"))}


def _group_tool(arguments: ToolArguments) -> dict[str, Any]:
    groups = group_by_records(_arg_records(arguments, "records"), _arg_str(arguments, "field"), multi_key=arguments.get("multi_key"), sort_groups=_arg_str(arguments, "sort_groups", "key_asc"))
    payload: dict[str, Any] = {"groups": groups}
    if _arg_bool(arguments, "include_summary", True):
        payload["summary"] = {key: len(value) for key, value in groups.items()}
    return payload


def _aggregate_tool(arguments: ToolArguments) -> dict[str, Any]:
    return aggregate_records(_arg_records(arguments, "records"), _arg_str(arguments, "field"), _arg_list(arguments, "aggregations"), group_by=_arg_opt_str(arguments, "group_by"), on_non_numeric=_arg_str(arguments, "on_non_numeric", "skip"))


def _join_tool(arguments: ToolArguments) -> dict[str, Any]:
    joined = join_records(_arg_records(arguments, "left"), _arg_records(arguments, "right"), _arg_str(arguments, "on"), join_type=_arg_str(arguments, "join_type", "inner"), conflict_strategy=_arg_str(arguments, "conflict_strategy", "prefix_right"), right_prefix=_arg_str(arguments, "right_prefix", "right_"))
    return {"records": joined, "count": len(joined)}


def _rename_tool(arguments: ToolArguments) -> dict[str, Any]:
    mapping = _arg_object(arguments, "mapping")
    renamed, report = rename_fields(_arg_records(arguments, "records"), {str(key): str(value) for key, value in mapping.items()}, strict=_arg_bool(arguments, "strict", False))
    return {"records": renamed, "report": report}


def _flatten_tool(arguments: ToolArguments) -> dict[str, Any]:
    return {"records": flatten_records(_arg_records(arguments, "records"), separator=_arg_str(arguments, "separator", "."), depth=arguments.get("depth", "full"), fields=arguments.get("fields"), expand_lists=_arg_bool(arguments, "expand_lists", False))}


def _evaluate_condition(record: Mapping[str, Any], condition: Mapping[str, Any], *, missing_field_behavior: str) -> bool:
    if "and" in condition:
        values = condition["and"]
        if not isinstance(values, list):
            raise ValueError("'and' must be a list.")
        return all(_evaluate_condition(record, _arg_object_value(value), missing_field_behavior=missing_field_behavior) for value in values)
    if "or" in condition:
        values = condition["or"]
        if not isinstance(values, list):
            raise ValueError("'or' must be a list.")
        return any(_evaluate_condition(record, _arg_object_value(value), missing_field_behavior=missing_field_behavior) for value in values)
    if "not" in condition:
        branch = condition["not"]
        if isinstance(branch, list):
            return not all(_evaluate_condition(record, _arg_object_value(value), missing_field_behavior=missing_field_behavior) for value in branch)
        return not _evaluate_condition(record, _arg_object_value(branch), missing_field_behavior=missing_field_behavior)
    field = _string(condition, "field")
    operator = _string(condition, "op")
    if field not in record:
        if missing_field_behavior == "include":
            return True
        if missing_field_behavior == "error":
            raise ValueError(f"Missing field '{field}' referenced by condition.")
        return False
    return _compare(record.get(field), operator, condition.get("value"))


def _compare(candidate: Any, operator: str, value: Any) -> bool:
    if operator == "eq":
        return candidate == value
    if operator == "ne":
        return candidate != value
    if operator == "lt":
        return _coerce_number(candidate) < _coerce_number(value)
    if operator == "lte":
        return _coerce_number(candidate) <= _coerce_number(value)
    if operator == "gt":
        return _coerce_number(candidate) > _coerce_number(value)
    if operator == "gte":
        return _coerce_number(candidate) >= _coerce_number(value)
    if operator == "contains":
        return value in candidate if isinstance(candidate, (list, tuple, set, str)) else False
    if operator == "startswith":
        return isinstance(candidate, str) and candidate.startswith(str(value))
    if operator == "endswith":
        return isinstance(candidate, str) and candidate.endswith(str(value))
    if operator == "is_null":
        return candidate is None
    if operator == "is_not_null":
        return candidate is not None
    if operator == "in":
        return candidate in (value if isinstance(value, list) else [])
    if operator == "not_in":
        return candidate not in (value if isinstance(value, list) else [])
    raise ValueError(f"Unsupported operator '{operator}'.")


def _numeric_values(records: Sequence[Mapping[str, Any]], field: str, *, on_non_numeric: str) -> tuple[list[float], int]:
    values: list[float] = []
    excluded = 0
    for record in records:
        try:
            values.append(_coerce_number(record.get(field)))
        except ValueError:
            if on_non_numeric == "zero":
                values.append(0.0)
            elif on_non_numeric == "error":
                raise
            else:
                excluded += 1
    return values, excluded


def _apply_aggregation(name: str, values: Sequence[float]) -> float | int | None:
    if name == "count":
        return len(values)
    if not values:
        return None
    return {
        "sum": sum(values),
        "mean": statistics.mean(values),
        "median": statistics.median(values),
        "min": min(values),
        "max": max(values),
        "std_dev": statistics.pstdev(values),
    }[name]


def _percentile(values: Sequence[float], rank: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    index = (len(ordered) - 1) * (rank / 100)
    lower = math.floor(index)
    upper = math.ceil(index)
    if lower == upper:
        return ordered[lower]
    fraction = index - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def _merge_join_pair(left: Mapping[str, Any] | None, right: Mapping[str, Any] | None, *, on: str, conflict_strategy: str, right_prefix: str) -> dict[str, Any]:
    payload: dict[str, Any] = deepcopy(dict(left or {}))
    right_item = dict(right or {})
    for key, value in right_item.items():
        if key == on and key in payload:
            continue
        if key not in payload:
            payload[key] = deepcopy(value)
            continue
        if conflict_strategy == "error":
            raise ValueError(f"Conflicting join field '{key}'.")
        if conflict_strategy == "prefix_both":
            left_value = payload.pop(key)
            payload[f"left_{key}"] = left_value
        payload[f"{right_prefix}{key}"] = deepcopy(value)
    return payload


def _flatten_dict(item: Mapping[str, Any], *, separator: str, depth: int | None, selected: set[str], expand_lists: bool, prefix: str = "", level: int = 0) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in item.items():
        current = f"{prefix}{separator}{key}" if prefix else key
        if selected and not prefix and key not in selected:
            result[key] = deepcopy(value)
        elif isinstance(value, Mapping) and (depth is None or level < depth):
            result.update(_flatten_dict(value, separator=separator, depth=depth, selected=set(), expand_lists=expand_lists, prefix=current, level=level + 1))
        elif isinstance(value, list) and expand_lists:
            for index, entry in enumerate(value):
                result[f"{current}{separator}{index}"] = deepcopy(entry)
        else:
            result[current] = deepcopy(value)
    return result


def _tool(key: str, name: str, properties: dict[str, object], description: str, required: Sequence[str]) -> ToolDefinition:
    return ToolDefinition(key=key, name=name, description=description, input_schema={"type": "object", "properties": properties, "required": list(required), "additionalProperties": False})


def _records(value: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise ValueError("Expected a list of records.")
    return [deepcopy(dict(item)) if isinstance(item, Mapping) else _raise("Record values must be objects.") for item in value]


def _coerce_number(value: Any) -> float:
    if isinstance(value, bool) or value is None:
        raise ValueError("Value is not numeric.")
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str) and value.strip():
        return float(value)
    raise ValueError("Value is not numeric.")


def _sort_key(value: Any, *, type_coerce: bool, nulls: str) -> tuple[int, Any]:
    if value is None:
        return (0 if nulls == "first" else 2, "")
    if type_coerce:
        try:
            return (1, _coerce_number(value))
        except ValueError:
            pass
    return (1, str(value).lower())


def _signature(value: Any) -> str:
    return json.dumps(value, sort_keys=True, default=str)


def _string(mapping: Mapping[str, Any], key: str, default: str | None = None) -> str:
    if key not in mapping:
        if default is None:
            raise ValueError(f"Missing '{key}'.")
        return default
    value = mapping[key]
    if not isinstance(value, str):
        raise ValueError(f"'{key}' must be a string.")
    return value


def _arg_records(arguments: ToolArguments, key: str) -> list[Mapping[str, Any]]:
    return _records(arguments[key])


def _arg_object(arguments: ToolArguments, key: str) -> Mapping[str, Any]:
    value = arguments[key]
    if not isinstance(value, Mapping):
        raise ValueError(f"The '{key}' argument must be an object.")
    return value


def _arg_object_value(value: Any) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("Condition branches must be objects.")
    return value


def _arg_list(arguments: ToolArguments, key: str) -> list[Any]:
    value = arguments[key]
    if not isinstance(value, list):
        raise ValueError(f"The '{key}' argument must be an array.")
    return value


def _arg_str(arguments: ToolArguments, key: str, default: str | None = None) -> str:
    if key not in arguments:
        if default is None:
            raise ValueError(f"The '{key}' argument is required.")
        return default
    value = arguments[key]
    if not isinstance(value, str):
        raise ValueError(f"The '{key}' argument must be a string.")
    return value


def _arg_opt_str(arguments: ToolArguments, key: str) -> str | None:
    if key not in arguments or arguments[key] is None:
        return None
    return _arg_str(arguments, key)


def _arg_int(arguments: ToolArguments, key: str, default: int | None = None) -> int:
    if key not in arguments:
        if default is None:
            raise ValueError(f"The '{key}' argument is required.")
        return default
    value = arguments[key]
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"The '{key}' argument must be an integer.")
    return value


def _arg_bool(arguments: ToolArguments, key: str, default: bool) -> bool:
    value = arguments.get(key, default)
    if not isinstance(value, bool):
        raise ValueError(f"The '{key}' argument must be a boolean.")
    return value


def _arg_str_list(arguments: ToolArguments, key: str) -> list[str]:
    if key not in arguments:
        return []
    value = arguments[key]
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"The '{key}' argument must be an array of strings.")
    return list(value)


def _raise(message: str) -> Any:
    raise ValueError(message)


__all__ = ["aggregate_records", "count_records", "create_records_tools", "filter_records", "flatten_records", "group_by_records", "join_records", "limit_records", "rename_fields", "select_records", "sort_records", "unique_records"]
