"""
===============================================================================
File: harnessiq/tools/control.py

What this file does:
- Defines the `ControlToolRuntime` type and the supporting logic it needs in
  the `harnessiq/tools` module.
- Runtime-backed control-flow tools.

Use cases:
- Import `ControlToolRuntime` when composing higher-level HarnessIQ runtime
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

from harnessiq.shared.agents import AgentPauseSignal
from harnessiq.shared.tools import (
    CONTROL_EMIT_DECISION,
    CONTROL_GET_FLAG,
    CONTROL_MARK_BLOCKED,
    CONTROL_MARK_COMPLETE,
    CONTROL_PAUSE_FOR_HUMAN,
    CONTROL_RECORD_ASSUMPTION,
    CONTROL_REQUEST_CLARIFICATION,
    CONTROL_SET_FLAG,
    RegisteredTool,
    ToolArguments,
    ToolDefinition,
)

from .runtime_support import read_json, resolve_runtime_root, utc_now, write_json


@dataclass(slots=True)
class ControlToolRuntime:
    root: Path

    def __init__(self, root: str | Path | None = None) -> None:
        self.root = resolve_runtime_root(root)

    @property
    def state_path(self) -> Path:
        return self.root / "control_state.json"

    def read_state(self) -> dict[str, Any]:
        return read_json(
            self.state_path,
            {"flags": {}, "decisions": [], "assumptions": [], "blocked_steps": [], "clarification_requests": [], "completion": None},
        )

    def write_state(self, state: dict[str, Any]) -> None:
        write_json(self.state_path, state)


def create_control_tools(*, runtime: ControlToolRuntime | None = None, root: str | Path | None = None) -> tuple[RegisteredTool, ...]:
    active = runtime or ControlToolRuntime(root)
    return (
        RegisteredTool(_tool(CONTROL_PAUSE_FOR_HUMAN, "pause_for_human", {"message": {"type": "string"}, "reason": {"type": "string"}, "options": {"type": "array", "items": {"type": "string"}}, "urgency": {"type": "string", "enum": ["low", "normal", "high"]}, "timeout_seconds": {"type": ["integer", "null"]}, "default_response": {"type": "string"}, "context_summary": {"type": "string"}}, "Pause for human review.", ()), lambda args: _pause(active, args)),
        RegisteredTool(_tool(CONTROL_EMIT_DECISION, "emit_decision", {"decision_id": {"type": "string"}, "chosen": {"type": "string"}, "rationale": {"type": "string"}, "alternatives": {"type": "array", "items": {"type": "string"}}, "confidence": {"type": "string", "enum": ["low", "medium", "high"]}, "persist_to_memory": {"type": "boolean"}}, "Record a decision.", ("decision_id", "chosen", "rationale")), lambda args: _emit_decision(active, args)),
        RegisteredTool(_tool(CONTROL_RECORD_ASSUMPTION, "record_assumption", {"assumption_id": {"type": "string"}, "statement": {"type": "string"}, "basis": {"type": "string"}, "impact_if_wrong": {"type": "string", "enum": ["low", "medium", "high"]}, "requires_confirmation": {"type": "boolean"}}, "Record an assumption.", ("assumption_id", "statement", "basis")), lambda args: _record_assumption(active, args)),
        RegisteredTool(_tool(CONTROL_MARK_BLOCKED, "mark_blocked", {"step_id": {"type": "string"}, "reason": {"type": "string"}, "block_type": {"type": "string", "enum": ["missing_input", "permission", "ambiguous_instruction", "dependency_failure", "resource_unavailable", "other"]}, "steps_attempted": {"type": "array", "items": {"type": "string"}}, "halt_all": {"type": "boolean"}}, "Mark a step as blocked.", ("step_id", "reason")), lambda args: _mark_blocked(active, args)),
        RegisteredTool(_tool(CONTROL_MARK_COMPLETE, "mark_complete", {"summary": {"type": "string"}, "artifacts_produced": {"type": "array", "items": {"type": "string"}}, "quality_assessment": {"type": "string", "enum": ["excellent", "good", "acceptable", "uncertain"]}, "open_questions": {"type": "array", "items": {"type": "string"}}, "trigger_final_report": {"type": "boolean"}}, "Signal task completion.", ("summary",)), lambda args: _mark_complete(active, args)),
        RegisteredTool(_tool(CONTROL_SET_FLAG, "set_flag", {"name": {"type": "string"}, "value": {}, "description": {"type": "string"}}, "Set a run-scoped flag.", ("name", "value")), lambda args: _set_flag(active, args)),
        RegisteredTool(_tool(CONTROL_GET_FLAG, "get_flag", {"name": {"type": "string"}, "default": {}}, "Read a run-scoped flag.", ("name",)), lambda args: _get_flag(active, args)),
        RegisteredTool(_tool(CONTROL_REQUEST_CLARIFICATION, "request_clarification", {"question_id": {"type": "string"}, "question": {"type": "string"}, "context": {"type": "string"}, "priority": {"type": "string", "enum": ["low", "normal", "high"]}, "default_answer": {"type": "string"}}, "Request clarification without blocking.", ("question_id", "question")), lambda args: _request_clarification(active, args)),
    )


def _pause(runtime: ControlToolRuntime, arguments: ToolArguments) -> AgentPauseSignal:
    payload = {"options": _str_list(arguments, "options"), "urgency": _str(arguments, "urgency", "normal"), "timeout_seconds": arguments.get("timeout_seconds"), "default_response": _str(arguments, "default_response", ""), "context_summary": _str(arguments, "context_summary", "")}
    reason = _optional_str(arguments, "message") or _optional_str(arguments, "reason")
    if reason is None:
        raise ValueError("The 'message' argument is required.")
    return AgentPauseSignal(reason=reason, details=payload)


def _emit_decision(runtime: ControlToolRuntime, arguments: ToolArguments) -> dict[str, Any]:
    state = runtime.read_state()
    payload = {"decision_id": _str(arguments, "decision_id"), "chosen": _str(arguments, "chosen"), "rationale": _str(arguments, "rationale"), "alternatives": _str_list(arguments, "alternatives"), "confidence": _str(arguments, "confidence", "medium"), "persist_to_memory": _bool(arguments, "persist_to_memory", True), "recorded_at": utc_now()}
    state["decisions"].append(payload)
    runtime.write_state(state)
    return payload


def _record_assumption(runtime: ControlToolRuntime, arguments: ToolArguments) -> dict[str, Any]:
    state = runtime.read_state()
    payload = {"assumption_id": _str(arguments, "assumption_id"), "statement": _str(arguments, "statement"), "basis": _str(arguments, "basis"), "impact_if_wrong": _str(arguments, "impact_if_wrong", "medium"), "requires_confirmation": _bool(arguments, "requires_confirmation", False), "recorded_at": utc_now()}
    state["assumptions"].append(payload)
    runtime.write_state(state)
    return payload


def _mark_blocked(runtime: ControlToolRuntime, arguments: ToolArguments) -> Any:
    state = runtime.read_state()
    payload = {"step_id": _str(arguments, "step_id"), "reason": _str(arguments, "reason"), "block_type": _str(arguments, "block_type", "other"), "steps_attempted": _str_list(arguments, "steps_attempted"), "blocked_at": utc_now()}
    state["blocked_steps"].append(payload)
    runtime.write_state(state)
    if _bool(arguments, "halt_all", False):
        return AgentPauseSignal(reason=payload["reason"], details={"status": "blocked", **payload})
    return payload


def _mark_complete(runtime: ControlToolRuntime, arguments: ToolArguments) -> AgentPauseSignal:
    state = runtime.read_state()
    payload = {"summary": _str(arguments, "summary"), "artifacts_produced": _str_list(arguments, "artifacts_produced"), "quality_assessment": _str(arguments, "quality_assessment", "good"), "open_questions": _str_list(arguments, "open_questions"), "trigger_final_report": _bool(arguments, "trigger_final_report", True), "completed_at": utc_now()}
    state["completion"] = payload
    runtime.write_state(state)
    return AgentPauseSignal(reason=payload["summary"], details={"status": "completed", **payload})


def _set_flag(runtime: ControlToolRuntime, arguments: ToolArguments) -> dict[str, Any]:
    state = runtime.read_state()
    state["flags"][_str(arguments, "name")] = {"value": arguments["value"], "description": _str(arguments, "description", ""), "updated_at": utc_now()}
    runtime.write_state(state)
    return {"name": _str(arguments, "name"), "value": arguments["value"]}


def _get_flag(runtime: ControlToolRuntime, arguments: ToolArguments) -> dict[str, Any]:
    state = runtime.read_state()
    name = _str(arguments, "name")
    if name in state["flags"]:
        return {"exists": True, "name": name, "value": state["flags"][name]["value"]}
    return {"exists": False, "name": name, "value": arguments.get("default")}


def _request_clarification(runtime: ControlToolRuntime, arguments: ToolArguments) -> dict[str, Any]:
    state = runtime.read_state()
    payload = {"question_id": _str(arguments, "question_id"), "question": _str(arguments, "question"), "context": _str(arguments, "context", ""), "priority": _str(arguments, "priority", "normal"), "default_answer": _str(arguments, "default_answer", ""), "requested_at": utc_now()}
    state["clarification_requests"].append(payload)
    runtime.write_state(state)
    return payload


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


def _optional_str(arguments: ToolArguments, key: str) -> str | None:
    if key not in arguments or arguments[key] is None:
        return None
    return _str(arguments, key)


def _str_list(arguments: ToolArguments, key: str) -> list[str]:
    if key not in arguments:
        return []
    value = arguments[key]
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"The '{key}' argument must be an array of strings.")
    return list(value)


def _bool(arguments: ToolArguments, key: str, default: bool) -> bool:
    value = arguments.get(key, default)
    if not isinstance(value, bool):
        raise ValueError(f"The '{key}' argument must be a boolean.")
    return value


__all__ = ["ControlToolRuntime", "create_control_tools"]
