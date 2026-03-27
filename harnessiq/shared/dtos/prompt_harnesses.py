"""DTOs for prompt-driven harness boundaries."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from harnessiq.shared.dtos.base import SerializableDTO


@dataclass(frozen=True, slots=True)
class MissionDrivenInstancePayload(SerializableDTO):
    """Persisted payload describing one mission-driven agent instance."""

    memory_path: Path | None
    mission_goal: str
    mission_type: str
    additional_prompt: str = ""
    max_tokens: int = 80_000
    reset_threshold: float = 0.85

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "mission_goal": self.mission_goal,
            "mission_type": self.mission_type,
            "additional_prompt": self.additional_prompt,
            "runtime": {
                "max_tokens": self.max_tokens,
                "reset_threshold": self.reset_threshold,
            },
        }
        if self.memory_path is not None:
            payload["memory_path"] = self.memory_path.as_posix()
        return payload


@dataclass(frozen=True, slots=True)
class SubAgentAssignmentDTO(SerializableDTO):
    """Typed assignment contract for the spawn-specialized-subagents harness."""

    assignment_id: str
    title: str
    objective: str
    owner: str
    deliverable: str
    completion_condition: str
    write_scope: tuple[str, ...] = ()
    context_items: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "assignment_id": self.assignment_id,
            "title": self.title,
            "objective": self.objective,
            "owner": self.owner,
            "deliverable": self.deliverable,
            "completion_condition": self.completion_condition,
            "write_scope": list(self.write_scope),
            "context_items": list(self.context_items),
        }


@dataclass(frozen=True, slots=True)
class WorkerExecutionResultDTO(SerializableDTO):
    """Typed worker-stage result for the spawn-specialized-subagents harness."""

    assignment_id: str
    status: str
    summary: str
    artifact: dict[str, Any] = field(default_factory=dict)
    risks: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "assignment_id": self.assignment_id,
            "status": self.status,
            "summary": self.summary,
            "artifact": dict(self.artifact),
            "risks": list(self.risks),
        }


@dataclass(frozen=True, slots=True)
class SpawnSpecializedSubagentsInstancePayload(SerializableDTO):
    """Persisted payload describing one spawn-specialized-subagents instance."""

    memory_path: Path | None
    objective: str
    available_agent_types: tuple[str, ...] = ()
    current_context: str = ""
    additional_prompt: str = ""
    max_tokens: int = 80_000
    reset_threshold: float = 0.85

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "objective": self.objective,
            "available_agent_types": list(self.available_agent_types),
            "current_context": self.current_context,
            "additional_prompt": self.additional_prompt,
            "runtime": {
                "max_tokens": self.max_tokens,
                "reset_threshold": self.reset_threshold,
            },
        }
        if self.memory_path is not None:
            payload["memory_path"] = self.memory_path.as_posix()
        return payload


__all__ = [
    "MissionDrivenInstancePayload",
    "SpawnSpecializedSubagentsInstancePayload",
    "SubAgentAssignmentDTO",
    "WorkerExecutionResultDTO",
]
