"""Structured validation tools."""

from __future__ import annotations

from collections import Counter, OrderedDict, defaultdict
from collections.abc import Mapping, Sequence
from typing import Any

import jsonschema

from harnessiq.shared.tools import (
    RegisteredTool,
    ToolArguments,
    ToolDefinition,
    VALIDATION_ASSERT_NOT_EMPTY,
    VALIDATION_CHECK_TYPE,
    VALIDATION_DETECT_CONFLICTS,
    VALIDATION_DETECT_DUPLICATES,
    VALIDATION_DETECT_MISSING,
    VALIDATION_DIFF_EXPECTED_ACTUAL,
    VALIDATION_GATE,
    VALIDATION_REQUIRE_FIELDS,
    VALIDATION_SCHEMA_VALIDATE,
    VALIDATION_SUMMARIZE_QUALITY,
)


def schema_validate(data: Any, schema: Mapping[str, Any], *, coerce_types: bool = False, abort_on_first_error: bool = False) -> dict[str, Any]:
    candidate = _coerce_schema_data(data, schema) if coerce_types else data
    validator = jsonschema.Draft7Validator(dict(schema))
    errors = []
    for error in validator.iter_errors(candidate):
        errors.append({"path": ".".join(str(item) for item in error.path), "message": error.message, "keyword": error.validator})
        if abort_on_first_error:
            break
    return {"valid": not errors, "errors": errors, "error_keywords": sorted({item["keyword"] for item in errors})}


def require_fields(record: Mapping[str, Any], required_fields: Sequence[str], *, allow_empty: bool = False, nested_paths: bool = False) -> dict[str, Any]:
    missing = []
    for field in required_fields:
        value = _path_get(record, field) if nested_paths else record.get(field)
        if value is None:
            missing.append(field)
            continue
        if not allow_empty:
            if isinstance(value, str) and value == "":
                missing.append(field)
                continue
            if isinstance(value, (list, dict, tuple, set)) and len(value) == 0:
                missing.append(field)
                continue
    return {"valid": not missing, "missing_fields": missing}


def detect_missing(records: Sequence[Mapping[str, Any]], required_fields: Sequence[str], *, min_missing_to_flag: int = 1, include_frequency_table: bool = True) -> dict[str, Any]:
    failures = []
    counter: Counter[str] = Counter()
    for index, record in enumerate(records):
        missing = [field for field in required_fields if record.get(field) is None]
        if len(missing) >= min_missing_to_flag:
            failures.append({"index": index, "record": dict(record), "missing_fields": missing})
            counter.update(missing)
    return {"records_checked": len(records), "records_with_missing": len(failures), "failures": failures, "frequency_table": dict(counter) if include_frequency_table else None}


def detect_duplicates(records: Sequence[Mapping[str, Any]], key_fields: Sequence[str], *, highlight_conflicts: bool = True, min_group_size: int = 2) -> dict[str, Any]:
    groups: OrderedDict[tuple[Any, ...], list[dict[str, Any]]] = OrderedDict()
    for record in records:
        groups.setdefault(tuple(record.get(field) for field in key_fields), []).append(dict(record))
    duplicates = []
    for key, members in groups.items():
        if len(members) < min_group_size:
            continue
        payload: dict[str, Any] = {"key": dict(zip(key_fields, key, strict=False)), "records": members}
        if highlight_conflicts:
            payload["conflicts"] = _duplicate_conflicts(members, key_fields)
        duplicates.append(payload)
    return {"duplicate_groups": duplicates, "duplicate_group_count": len(duplicates), "records_involved": sum(len(group["records"]) for group in duplicates)}


def detect_conflicts(records: Sequence[Mapping[str, Any]], key_fields: Sequence[str], conflict_fields: Sequence[str], *, ignore_null_conflicts: bool = True) -> dict[str, Any]:
    groups: defaultdict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        groups[tuple(record.get(field) for field in key_fields)].append(dict(record))
    conflicts = []
    for key, members in groups.items():
        field_conflicts = {}
        for field in conflict_fields:
            values = {member.get(field) for member in members if not (ignore_null_conflicts and member.get(field) is None)}
            if len(values) > 1:
                field_conflicts[field] = sorted(values, key=str)
        if field_conflicts:
            conflicts.append({"key": dict(zip(key_fields, key, strict=False)), "records": members, "conflicts": field_conflicts, "severity": "high" if len(members) > 2 else "medium"})
    return {"conflicts": conflicts, "conflict_group_count": len(conflicts)}


def diff_expected_actual(expected: Any, actual: Any, *, comparison_mode: str = "fields", key_fields: Sequence[str] = (), ignore_fields: Sequence[str] = (), numeric_tolerance: float | None = None) -> dict[str, Any]:
    discrepancies = []
    if comparison_mode == "records":
        expected_map = {tuple(item.get(field) for field in key_fields): item for item in expected}
        actual_map = {tuple(item.get(field) for field in key_fields): item for item in actual}
        for key in expected_map:
            if key not in actual_map:
                discrepancies.append({"type": "missing", "key": key})
            else:
                discrepancies.extend(_field_diff(expected_map[key], actual_map[key], ignore_fields=ignore_fields, numeric_tolerance=numeric_tolerance))
        for key in actual_map:
            if key not in expected_map:
                discrepancies.append({"type": "extra", "key": key})
    else:
        discrepancies.extend(_field_diff(expected, actual, ignore_fields=ignore_fields, numeric_tolerance=numeric_tolerance))
    counts = Counter(item["type"] for item in discrepancies)
    return {"matches": not discrepancies, "discrepancies": discrepancies, "summary": dict(counts)}


def assert_not_empty(value: Any, *, label: str = "value", fail_message: str = "", min_length: int = 1, strip_strings: bool = True) -> dict[str, Any]:
    if isinstance(value, str) and strip_strings:
        value = value.strip()
    length = len(value) if isinstance(value, (str, list, dict, tuple, set)) else int(bool(value))
    valid = length >= min_length
    return {"valid": valid, "message": "" if valid else (fail_message or f"{label} must not be empty."), "length": length}


def check_type(value: Any, expected_type: str, *, constraints: Mapping[str, Any] | None = None, coerce: bool = False) -> dict[str, Any]:
    candidate = _coerce_value(value, expected_type) if coerce else value
    actual_type = _type_name(candidate)
    valid = actual_type == expected_type
    if valid and constraints:
        valid = _check_constraints(candidate, constraints)
    return {"valid": valid, "actual_type": actual_type, "message": "" if valid else f"Expected {expected_type}, got {actual_type}."}


def summarize_quality(records: Sequence[Mapping[str, Any]], *, completeness_threshold: float = 0.9, include_value_distribution: bool = True, numeric_fields: Sequence[str] = ()) -> dict[str, Any]:
    field_names = sorted({field for record in records for field in record})
    summary = {}
    numeric_field_set = set(numeric_fields)
    for field in field_names:
        values = [record.get(field) for record in records]
        present = [value for value in values if value is not None]
        predominant = Counter(_type_name(value) for value in present).most_common(1)
        dominant = predominant[0][0] if predominant else "null"
        payload: dict[str, Any] = {
            "completeness": len(present) / len(records) if records else 0.0,
            "type_consistency": (sum(1 for value in present if _type_name(value) == dominant) / len(present)) if present else 1.0,
            "flagged": (len(present) / len(records) if records else 0.0) < completeness_threshold,
        }
        if include_value_distribution:
            distribution = {"unique_count": len({repr(value) for value in present}), "most_common": Counter(repr(value) for value in present).most_common(1)[0][0] if present else None}
            if field in numeric_field_set or all(isinstance(value, (int, float)) for value in present if value is not None):
                numeric = [float(value) for value in present if isinstance(value, (int, float))]
                if numeric:
                    distribution.update({"min": min(numeric), "mean": sum(numeric) / len(numeric), "max": max(numeric)})
            payload["distribution"] = distribution
        summary[field] = payload
    return {"fields": summary}


def gate(check_results: Sequence[Mapping[str, Any]], *, mode: str = "all", pass_fraction: float = 1.0, required_checks: Sequence[str] = (), gate_name: str = "validation_gate") -> dict[str, Any]:
    passed = [item for item in check_results if bool(item.get("valid"))]
    failed = [item for item in check_results if not bool(item.get("valid"))]
    passed_names = {str(item.get("check_name")) for item in passed}
    required_ok = all(name in passed_names for name in required_checks)
    if mode == "all":
        valid = not failed
    elif mode == "threshold":
        valid = (len(passed) / len(check_results)) >= pass_fraction if check_results else True
    else:
        valid = required_ok and ((len(passed) / len(check_results)) >= pass_fraction if check_results else True)
    return {"check_name": gate_name, "valid": valid, "passed_count": len(passed), "failed_count": len(failed), "blocking_checks": [item.get("check_name") for item in failed if item.get("check_name") in required_checks or mode == "all"]}


def create_validation_tools() -> tuple[RegisteredTool, ...]:
    return (
        RegisteredTool(_tool(VALIDATION_SCHEMA_VALIDATE, "schema_validate", {"data": {}, "schema": {"type": "object"}, "coerce_types": {"type": "boolean"}, "abort_on_first_error": {"type": "boolean"}}, "Validate against JSON Schema.", ("data", "schema")), _schema_tool),
        RegisteredTool(_tool(VALIDATION_REQUIRE_FIELDS, "require_fields", {"record": {"type": "object"}, "required_fields": {"type": "array", "items": {"type": "string"}}, "allow_empty": {"type": "boolean"}, "nested_paths": {"type": "boolean"}}, "Require fields in one record.", ("record", "required_fields")), _require_tool),
        RegisteredTool(_tool(VALIDATION_DETECT_MISSING, "detect_missing", {"records": {"type": "array", "items": {"type": "object"}}, "required_fields": {"type": "array", "items": {"type": "string"}}, "min_missing_to_flag": {"type": "integer"}, "include_frequency_table": {"type": "boolean"}}, "Detect missing fields in records.", ("records", "required_fields")), _missing_tool),
        RegisteredTool(_tool(VALIDATION_DETECT_DUPLICATES, "detect_duplicates", {"records": {"type": "array", "items": {"type": "object"}}, "key_fields": {"type": "array", "items": {"type": "string"}}, "highlight_conflicts": {"type": "boolean"}, "min_group_size": {"type": "integer"}}, "Detect duplicate records.", ("records", "key_fields")), _duplicates_tool),
        RegisteredTool(_tool(VALIDATION_DETECT_CONFLICTS, "detect_conflicts", {"records": {"type": "array", "items": {"type": "object"}}, "key_fields": {"type": "array", "items": {"type": "string"}}, "conflict_fields": {"type": "array", "items": {"type": "string"}}, "ignore_null_conflicts": {"type": "boolean"}}, "Detect conflicting values.", ("records", "key_fields", "conflict_fields")), _conflicts_tool),
        RegisteredTool(_tool(VALIDATION_DIFF_EXPECTED_ACTUAL, "diff_expected_actual", {"expected": {}, "actual": {}, "comparison_mode": {"type": "string", "enum": ["fields", "records"]}, "key_fields": {"type": "array", "items": {"type": "string"}}, "ignore_fields": {"type": "array", "items": {"type": "string"}}, "numeric_tolerance": {"type": ["number", "null"]}}, "Diff expected and actual outputs.", ("expected", "actual")), _diff_tool),
        RegisteredTool(_tool(VALIDATION_ASSERT_NOT_EMPTY, "assert_not_empty", {"value": {}, "label": {"type": "string"}, "fail_message": {"type": "string"}, "min_length": {"type": "integer"}, "strip_strings": {"type": "boolean"}}, "Assert non-empty values.", ("value",)), _assert_tool),
        RegisteredTool(_tool(VALIDATION_CHECK_TYPE, "check_type", {"value": {}, "expected_type": {"type": "string"}, "constraints": {"type": ["object", "null"]}, "coerce": {"type": "boolean"}}, "Check a value type.", ("value", "expected_type")), _type_tool),
        RegisteredTool(_tool(VALIDATION_SUMMARIZE_QUALITY, "summarize_quality", {"records": {"type": "array", "items": {"type": "object"}}, "completeness_threshold": {"type": "number"}, "include_value_distribution": {"type": "boolean"}, "numeric_fields": {"type": "array", "items": {"type": "string"}}}, "Summarize dataset quality.", ("records",)), _quality_tool),
        RegisteredTool(_tool(VALIDATION_GATE, "gate", {"check_results": {"type": "array", "items": {"type": "object"}}, "mode": {"type": "string", "enum": ["all", "threshold", "required_plus_threshold"]}, "pass_fraction": {"type": "number"}, "required_checks": {"type": "array", "items": {"type": "string"}}, "gate_name": {"type": "string"}}, "Evaluate a validation gate.", ("check_results",)), _gate_tool),
    )


def _schema_tool(arguments: ToolArguments) -> dict[str, Any]:
    return schema_validate(arguments["data"], _obj(arguments, "schema"), coerce_types=_bool(arguments, "coerce_types", False), abort_on_first_error=_bool(arguments, "abort_on_first_error", False))


def _require_tool(arguments: ToolArguments) -> dict[str, Any]:
    return require_fields(_obj(arguments, "record"), _str_list(arguments, "required_fields"), allow_empty=_bool(arguments, "allow_empty", False), nested_paths=_bool(arguments, "nested_paths", False))


def _missing_tool(arguments: ToolArguments) -> dict[str, Any]:
    return detect_missing(_obj_list(arguments, "records"), _str_list(arguments, "required_fields"), min_missing_to_flag=_int(arguments, "min_missing_to_flag", 1), include_frequency_table=_bool(arguments, "include_frequency_table", True))


def _duplicates_tool(arguments: ToolArguments) -> dict[str, Any]:
    return detect_duplicates(_obj_list(arguments, "records"), _str_list(arguments, "key_fields"), highlight_conflicts=_bool(arguments, "highlight_conflicts", True), min_group_size=_int(arguments, "min_group_size", 2))


def _conflicts_tool(arguments: ToolArguments) -> dict[str, Any]:
    return detect_conflicts(_obj_list(arguments, "records"), _str_list(arguments, "key_fields"), _str_list(arguments, "conflict_fields"), ignore_null_conflicts=_bool(arguments, "ignore_null_conflicts", True))


def _diff_tool(arguments: ToolArguments) -> dict[str, Any]:
    return diff_expected_actual(arguments["expected"], arguments["actual"], comparison_mode=_str(arguments, "comparison_mode", "fields"), key_fields=_str_list(arguments, "key_fields"), ignore_fields=_str_list(arguments, "ignore_fields"), numeric_tolerance=arguments.get("numeric_tolerance"))


def _assert_tool(arguments: ToolArguments) -> dict[str, Any]:
    return assert_not_empty(arguments["value"], label=_str(arguments, "label", "value"), fail_message=_str(arguments, "fail_message", ""), min_length=_int(arguments, "min_length", 1), strip_strings=_bool(arguments, "strip_strings", True))


def _type_tool(arguments: ToolArguments) -> dict[str, Any]:
    return check_type(arguments["value"], _str(arguments, "expected_type"), constraints=arguments.get("constraints"), coerce=_bool(arguments, "coerce", False))


def _quality_tool(arguments: ToolArguments) -> dict[str, Any]:
    return summarize_quality(_obj_list(arguments, "records"), completeness_threshold=float(arguments.get("completeness_threshold", 0.9)), include_value_distribution=_bool(arguments, "include_value_distribution", True), numeric_fields=_str_list(arguments, "numeric_fields"))


def _gate_tool(arguments: ToolArguments) -> dict[str, Any]:
    return gate(_obj_list(arguments, "check_results"), mode=_str(arguments, "mode", "all"), pass_fraction=float(arguments.get("pass_fraction", 1.0)), required_checks=_str_list(arguments, "required_checks"), gate_name=_str(arguments, "gate_name", "validation_gate"))


def _field_diff(expected: Mapping[str, Any], actual: Mapping[str, Any], *, ignore_fields: Sequence[str], numeric_tolerance: float | None) -> list[dict[str, Any]]:
    ignored = set(ignore_fields)
    items = []
    for field in sorted((set(expected) | set(actual)) - ignored):
        if field not in actual:
            items.append({"type": "missing", "field": field})
        elif field not in expected:
            items.append({"type": "extra", "field": field})
        else:
            left = expected[field]
            right = actual[field]
            if type(left) is not type(right):
                items.append({"type": "type_mismatch", "field": field, "expected": type(left).__name__, "actual": type(right).__name__})
            elif isinstance(left, (int, float)) and numeric_tolerance is not None and abs(float(left) - float(right)) <= numeric_tolerance:
                continue
            elif left != right:
                items.append({"type": "value_mismatch", "field": field, "expected": left, "actual": right})
    return items


def _duplicate_conflicts(records: Sequence[Mapping[str, Any]], key_fields: Sequence[str]) -> dict[str, list[Any]]:
    conflicts = {}
    for field in sorted({key for record in records for key in record} - set(key_fields)):
        values = {record.get(field) for record in records}
        if len(values) > 1:
            conflicts[field] = sorted(values, key=str)
    return conflicts


def _path_get(record: Mapping[str, Any], path: str) -> Any:
    current: Any = record
    for part in path.split("."):
        if not isinstance(current, Mapping) or part not in current:
            return None
        current = current[part]
    return current


def _coerce_schema_data(data: Any, schema: Mapping[str, Any]) -> Any:
    if not isinstance(data, Mapping) or not isinstance(schema.get("properties"), Mapping):
        return data
    payload = dict(data)
    for key, spec in schema["properties"].items():
        if key not in payload or not isinstance(spec, Mapping):
            continue
        if spec.get("type") == "integer" and isinstance(payload[key], str) and payload[key].isdigit():
            payload[key] = int(payload[key])
        elif spec.get("type") == "number" and isinstance(payload[key], str):
            try:
                payload[key] = float(payload[key])
            except ValueError:
                pass
        elif spec.get("type") == "boolean" and isinstance(payload[key], str):
            lowered = payload[key].lower()
            if lowered in {"true", "false"}:
                payload[key] = lowered == "true"
    return payload


def _coerce_value(value: Any, expected_type: str) -> Any:
    if expected_type == "integer" and isinstance(value, str) and value.isdigit():
        return int(value)
    if expected_type == "float" and isinstance(value, str):
        return float(value)
    if expected_type == "boolean" and isinstance(value, str) and value.lower() in {"true", "false"}:
        return value.lower() == "true"
    if expected_type == "list" and isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return value


def _check_constraints(value: Any, constraints: Mapping[str, Any]) -> bool:
    if constraints.get("type") == "list" and "items" in constraints:
        subtype = constraints["items"].get("type")
        return isinstance(value, list) and all(_type_name(item) == subtype for item in value)
    if "minimum" in constraints and value < constraints["minimum"]:
        return False
    if "maximum" in constraints and value > constraints["maximum"]:
        return False
    if "required_keys" in constraints:
        return isinstance(value, Mapping) and all(key in value for key in constraints["required_keys"])
    return True


def _type_name(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "list"
    if isinstance(value, Mapping):
        return "dict"
    return type(value).__name__


def _tool(key: str, name: str, properties: dict[str, object], description: str, required: Sequence[str]) -> ToolDefinition:
    return ToolDefinition(key=key, name=name, description=description, input_schema={"type": "object", "properties": properties, "required": list(required), "additionalProperties": False})


def _obj(arguments: ToolArguments, key: str) -> Mapping[str, Any]:
    value = arguments[key]
    if not isinstance(value, Mapping):
        raise ValueError(f"The '{key}' argument must be an object.")
    return value


def _obj_list(arguments: ToolArguments, key: str) -> list[Mapping[str, Any]]:
    value = arguments[key]
    if not isinstance(value, list) or not all(isinstance(item, Mapping) for item in value):
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


__all__ = ["assert_not_empty", "check_type", "create_validation_tools", "detect_conflicts", "detect_duplicates", "detect_missing", "diff_expected_actual", "gate", "require_fields", "schema_validate", "summarize_quality"]
