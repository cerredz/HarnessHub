"""Shared DTOs for platform CLI and profile persistence boundaries."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Mapping

from .base import SerializableDTO, coerce_serializable_mapping


def _normalize_value(value: Any) -> Any:
    if isinstance(value, SerializableDTO):
        return value.to_dict()
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, Mapping):
        return {str(key): _normalize_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_normalize_value(item) for item in value]
    return value


@dataclass(frozen=True, slots=True)
class HarnessParameterBundleDTO(SerializableDTO):
    """Explicit runtime/custom parameter bundle passed between CLI layers."""

    runtime_parameters: Mapping[str, Any] = field(default_factory=dict)
    custom_parameters: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "runtime_parameters": _normalize_value(self.runtime_parameters),
            "custom_parameters": _normalize_value(self.custom_parameters),
        }


@dataclass(frozen=True, slots=True)
class HarnessRunSummaryDTO(SerializableDTO):
    """Summary metadata for one persisted CLI run."""

    recorded_at: str | None = None
    run_number: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "recorded_at": self.recorded_at,
            "run_number": self.run_number,
        }


@dataclass(frozen=True, slots=True)
class HarnessRunSnapshotDTO(SerializableDTO):
    """Explicit persisted transport for one harness run snapshot."""

    model_factory: str | None = None
    model: str | None = None
    model_profile: str | None = None
    sink_specs: tuple[str, ...] = ()
    max_cycles: int | None = None
    adapter_arguments: Mapping[str, Any] = field(default_factory=dict)
    runtime_parameters: Mapping[str, Any] = field(default_factory=dict)
    custom_parameters: Mapping[str, Any] = field(default_factory=dict)
    recorded_at: str | None = None
    run_number: int | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "adapter_arguments": _normalize_value(self.adapter_arguments),
            "custom_parameters": _normalize_value(self.custom_parameters),
            "max_cycles": self.max_cycles,
            "recorded_at": self.recorded_at,
            "runtime_parameters": _normalize_value(self.runtime_parameters),
            "sink_specs": list(self.sink_specs),
        }
        if self.model_factory is not None:
            payload["model_factory"] = self.model_factory
        if self.model is not None:
            payload["model"] = self.model
        if self.model_profile is not None:
            payload["model_profile"] = self.model_profile
        if self.run_number is not None:
            payload["run_number"] = self.run_number
        return payload

    @property
    def summary(self) -> HarnessRunSummaryDTO:
        return HarnessRunSummaryDTO(
            recorded_at=self.recorded_at,
            run_number=self.run_number,
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "HarnessRunSnapshotDTO":
        sink_specs = payload.get("sink_specs", ())
        adapter_arguments = payload.get("adapter_arguments", {})
        runtime_parameters = payload.get("runtime_parameters", {})
        custom_parameters = payload.get("custom_parameters", {})
        if not isinstance(sink_specs, (list, tuple)):
            raise ValueError("Harness run snapshot 'sink_specs' must be a JSON array.")
        if not isinstance(adapter_arguments, Mapping):
            raise ValueError("Harness run snapshot 'adapter_arguments' must be a JSON object.")
        if not isinstance(runtime_parameters, Mapping):
            raise ValueError("Harness run snapshot 'runtime_parameters' must be a JSON object.")
        if not isinstance(custom_parameters, Mapping):
            raise ValueError("Harness run snapshot 'custom_parameters' must be a JSON object.")
        max_cycles = payload.get("max_cycles")
        if max_cycles is not None and not isinstance(max_cycles, int):
            raise ValueError("Harness run snapshot 'max_cycles' must be an integer or null.")
        recorded_at = payload.get("recorded_at")
        if recorded_at is not None and not isinstance(recorded_at, str):
            raise ValueError("Harness run snapshot 'recorded_at' must be a string when present.")
        run_number = payload.get("run_number")
        if run_number is not None and not isinstance(run_number, int):
            raise ValueError("Harness run snapshot 'run_number' must be an integer when present.")
        return cls(
            model_factory=_normalize_optional_string(payload.get("model_factory")),
            model=_normalize_optional_string(payload.get("model")),
            model_profile=_normalize_optional_string(payload.get("model_profile")),
            sink_specs=tuple(str(spec) for spec in sink_specs),
            max_cycles=max_cycles,
            adapter_arguments=dict(adapter_arguments),
            runtime_parameters=dict(runtime_parameters),
            custom_parameters=dict(custom_parameters),
            recorded_at=recorded_at,
            run_number=run_number,
        )


@dataclass(frozen=True, slots=True)
class HarnessProfileDTO(SerializableDTO):
    """Explicit persisted transport for one harness profile file."""

    manifest_id: str
    agent_name: str
    runtime_parameters: Mapping[str, Any] = field(default_factory=dict)
    custom_parameters: Mapping[str, Any] = field(default_factory=dict)
    last_run: HarnessRunSnapshotDTO | None = None
    run_history: tuple[HarnessRunSnapshotDTO, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "agent_name": self.agent_name,
            "custom_parameters": _normalize_value(self.custom_parameters),
            "manifest_id": self.manifest_id,
            "runtime_parameters": _normalize_value(self.runtime_parameters),
        }
        if self.last_run is not None:
            payload["last_run"] = self.last_run.to_dict()
        if self.run_history:
            payload["run_history"] = [snapshot.to_dict() for snapshot in self.run_history]
        return payload

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "HarnessProfileDTO":
        runtime_parameters = payload.get("runtime_parameters", {})
        custom_parameters = payload.get("custom_parameters", {})
        run_history_payload = payload.get("run_history", [])
        if not isinstance(runtime_parameters, Mapping):
            raise ValueError("Harness profile 'runtime_parameters' must be a JSON object.")
        if not isinstance(custom_parameters, Mapping):
            raise ValueError("Harness profile 'custom_parameters' must be a JSON object.")
        if not isinstance(run_history_payload, list):
            raise ValueError("Harness profile 'run_history' must be a JSON array when present.")
        last_run_payload = payload.get("last_run")
        if last_run_payload is not None and not isinstance(last_run_payload, Mapping):
            raise ValueError("Harness profile 'last_run' must be a JSON object when present.")
        return cls(
            manifest_id=str(payload["manifest_id"]),
            agent_name=str(payload["agent_name"]),
            runtime_parameters=dict(runtime_parameters),
            custom_parameters=dict(custom_parameters),
            last_run=(HarnessRunSnapshotDTO.from_dict(last_run_payload) if last_run_payload is not None else None),
            run_history=tuple(HarnessRunSnapshotDTO.from_dict(item) for item in run_history_payload),
        )


@dataclass(frozen=True, slots=True)
class HarnessProfileIndexRecordDTO(SerializableDTO):
    """Explicit persisted transport for one repo-level harness profile locator."""

    manifest_id: str
    agent_name: str
    memory_path: str
    updated_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_name": self.agent_name,
            "manifest_id": self.manifest_id,
            "memory_path": self.memory_path,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "HarnessProfileIndexRecordDTO":
        return cls(
            manifest_id=str(payload["manifest_id"]),
            agent_name=str(payload["agent_name"]),
            memory_path=str(payload["memory_path"]),
            updated_at=str(payload["updated_at"]),
        )


@dataclass(frozen=True, slots=True)
class HarnessProfileIndexDTO(SerializableDTO):
    """Explicit persisted transport for the repo-level harness profile index."""

    records: tuple[HarnessProfileIndexRecordDTO, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {"records": [record.to_dict() for record in self.records]}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "HarnessProfileIndexDTO":
        raw_records = payload.get("records", [])
        if not isinstance(raw_records, list):
            raise ValueError("Harness profile index payload must define 'records' as a list.")
        return cls(records=tuple(HarnessProfileIndexRecordDTO.from_dict(item) for item in raw_records))


@dataclass(frozen=True, slots=True)
class HarnessProfileViewDTO(SerializableDTO):
    """Public CLI profile payload rendered into terminal JSON output."""

    config_path: str
    runtime_parameters: Mapping[str, Any]
    custom_parameters: Mapping[str, Any]
    effective_runtime_parameters: Mapping[str, Any]
    effective_custom_parameters: Mapping[str, Any]
    last_run: HarnessRunSnapshotDTO | None = None
    run_history: tuple[HarnessRunSummaryDTO, ...] = ()

    @property
    def run_count(self) -> int:
        return len(self.run_history)

    def to_dict(self) -> dict[str, Any]:
        return {
            "config_path": self.config_path,
            "custom_parameters": _normalize_value(self.custom_parameters),
            "effective_custom_parameters": _normalize_value(self.effective_custom_parameters),
            "effective_runtime_parameters": _normalize_value(self.effective_runtime_parameters),
            "last_run": (self.last_run.to_dict() if self.last_run is not None else None),
            "run_count": self.run_count,
            "run_history": [entry.to_dict() for entry in self.run_history],
            "runtime_parameters": _normalize_value(self.runtime_parameters),
        }


@dataclass(frozen=True, slots=True)
class HarnessStatePayloadDTO(SerializableDTO):
    """Generic DTO wrapper for adapter `show()` state payloads."""

    payload: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _normalize_value(self.payload)


@dataclass(frozen=True, slots=True)
class HarnessRunResultDTO(SerializableDTO):
    """Shared CLI DTO for the common `agent.run()` result envelope."""

    cycles_completed: int | None = None
    pause_reason: str | None = None
    resets: int | None = None
    status: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "cycles_completed": self.cycles_completed,
            "pause_reason": self.pause_reason,
            "resets": self.resets,
            "status": self.status,
        }

    @classmethod
    def from_result(cls, result: Any) -> "HarnessRunResultDTO":
        return cls(
            cycles_completed=getattr(result, "cycles_completed", None),
            pause_reason=getattr(result, "pause_reason", None),
            resets=getattr(result, "resets", None),
            status=getattr(result, "status", None),
        )


@dataclass(frozen=True, slots=True)
class HarnessResumePayloadDTO(SerializableDTO):
    """CLI DTO for the resolved resume request payload emitted to stdout."""

    adapter_arguments: Mapping[str, Any] = field(default_factory=dict)
    sink_specs: tuple[str, ...] = ()
    max_cycles: int | None = None
    model_factory: str | None = None
    model: str | None = None
    model_profile: str | None = None
    source_recorded_at: str | None = None
    source_run_number: int | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "adapter_arguments": _normalize_value(self.adapter_arguments),
            "max_cycles": self.max_cycles,
            "sink_specs": list(self.sink_specs),
        }
        if self.model_factory is not None:
            payload["model_factory"] = self.model_factory
        if self.model is not None:
            payload["model"] = self.model
        if self.model_profile is not None:
            payload["profile"] = self.model_profile
        if self.source_recorded_at is not None:
            payload["source_recorded_at"] = self.source_recorded_at
        if self.source_run_number is not None:
            payload["source_run_number"] = self.source_run_number
        return payload


@dataclass(frozen=True, slots=True)
class HarnessAdapterResponseDTO(SerializableDTO):
    """Explicit DTO returned from platform CLI adapters for `run` responses."""

    result: HarnessRunResultDTO | None = None
    state: SerializableDTO | Mapping[str, Any] | None = None
    extra: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = _normalize_value(self.extra)
        if self.result is not None:
            payload["result"] = self.result.to_dict()
        if self.state is not None:
            payload["state"] = _normalize_value(self.state)
        return payload


@dataclass(frozen=True, slots=True)
class HarnessCommandPayloadDTO(SerializableDTO):
    """DTO for the top-level JSON payload emitted by platform CLI commands."""

    agent: str
    harness: str
    memory_path: str
    credential_binding_name: str
    bound_credential_families: tuple[str, ...]
    profile: HarnessProfileViewDTO
    status: str | None = None
    state: SerializableDTO | Mapping[str, Any] | None = None
    resume: HarnessResumePayloadDTO | None = None
    result: HarnessRunResultDTO | None = None
    extra: Mapping[str, Any] = field(default_factory=dict)

    def with_status(self, status: str | None) -> "HarnessCommandPayloadDTO":
        return replace(self, status=status)

    def with_state(self, state: SerializableDTO | Mapping[str, Any] | None) -> "HarnessCommandPayloadDTO":
        return replace(self, state=state)

    def with_resume(self, resume: HarnessResumePayloadDTO | None) -> "HarnessCommandPayloadDTO":
        return replace(self, resume=resume)

    def with_extra(self, **payload: Any) -> "HarnessCommandPayloadDTO":
        merged = {**coerce_serializable_mapping(self.extra), **payload}
        return replace(self, extra=merged)

    def merge_response(
        self,
        response: HarnessAdapterResponseDTO | Mapping[str, Any],
    ) -> "HarnessCommandPayloadDTO":
        if not isinstance(response, HarnessAdapterResponseDTO):
            coerced = coerce_serializable_mapping(response)
            result_payload = coerced.pop("result", None)
            state_payload = coerced.pop("state", None)
            response = HarnessAdapterResponseDTO(
                result=(
                    HarnessRunResultDTO(
                        cycles_completed=result_payload.get("cycles_completed"),
                        pause_reason=result_payload.get("pause_reason"),
                        resets=result_payload.get("resets"),
                        status=result_payload.get("status"),
                    )
                    if isinstance(result_payload, Mapping)
                    else None
                ),
                state=(state_payload if isinstance(state_payload, Mapping) else None),
                extra=coerced,
            )
        merged_extra = {**coerce_serializable_mapping(self.extra), **coerce_serializable_mapping(response.extra)}
        return replace(
            self,
            result=response.result or self.result,
            state=response.state or self.state,
            extra=merged_extra,
        )

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "agent": self.agent,
            "bound_credential_families": list(self.bound_credential_families),
            "credential_binding_name": self.credential_binding_name,
            "harness": self.harness,
            "memory_path": self.memory_path,
            "profile": self.profile.to_dict(),
        }
        payload.update(_normalize_value(self.extra))
        if self.status is not None:
            payload["status"] = self.status
        if self.state is not None:
            payload["state"] = _normalize_value(self.state)
        if self.resume is not None:
            payload["resume"] = self.resume.to_dict()
        if self.result is not None:
            payload["result"] = self.result.to_dict()
        return payload


def _normalize_optional_string(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


__all__ = [
    "HarnessAdapterResponseDTO",
    "HarnessCommandPayloadDTO",
    "HarnessParameterBundleDTO",
    "HarnessProfileDTO",
    "HarnessProfileIndexDTO",
    "HarnessProfileIndexRecordDTO",
    "HarnessProfileViewDTO",
    "HarnessResumePayloadDTO",
    "HarnessRunResultDTO",
    "HarnessRunSnapshotDTO",
    "HarnessRunSummaryDTO",
    "HarnessStatePayloadDTO",
]
