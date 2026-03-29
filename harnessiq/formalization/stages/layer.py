from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from harnessiq.formalization.base import BaseFormalizationLayer, LayerRuleRecord
from harnessiq.shared.agents import AgentParameterSection
from harnessiq.shared.tools import RegisteredTool, ToolResult
from harnessiq.tools.hooks.defaults import is_tool_allowed

from .context import StageContext
from .exceptions import StageAdvancementError
from .executor import StageAwareToolExecutor
from .spec import StageSpec
from .tools import STAGE_COMPLETE_TOOL

_STAGE_OUTPUTS_FILENAME = "stage_outputs.json"
_STAGE_INDEX_FILENAME = "stage_index.json"


class StageLayer(BaseFormalizationLayer):
    """Runtime manager for a sequence of executable stage specifications."""

    def __init__(self, stages: Sequence[StageSpec]) -> None:
        if not stages:
            raise ValueError("StageLayer requires at least one StageSpec.")

        seen: set[str] = set()
        for index, stage in enumerate(stages):
            if not stage.name.strip():
                raise ValueError(f"StageSpec at index {index} has a blank name.")
            if stage.name in seen:
                raise ValueError(f"Duplicate stage name '{stage.name}' at index {index}.")
            seen.add(stage.name)

        self._stages: tuple[StageSpec, ...] = tuple(stages)
        self._stage_map = {stage.name: stage for stage in self._stages}
        self._index_map = {stage.name: index for index, stage in enumerate(self._stages)}
        self._current_index = 0
        self._completion_pending = False
        self._pending_outputs: dict[str, Any] = {}
        self._pending_summary = ""
        self._prior_outputs: dict[str, dict[str, Any]] = {}
        self._memory_path: Path | None = None
        self._agent_name = ""
        self._reset_count = 0
        self._stage_executor: StageAwareToolExecutor | None = None

    @property
    def layer_id(self) -> str:
        return "StageLayer"

    def _describe_identity(self) -> str:
        names = " -> ".join(stage.name for stage in self._stages)
        return (
            f"You are executing a {len(self._stages)}-stage harness: {names}. "
            "Each stage has its own tools and instructions. "
            "Stage advancement is deterministic and controlled by Python code. "
            "Call formalization.stage_complete when the current stage is done."
        )

    def _describe_contract(self) -> str:
        lines = [
            "Call formalization.stage_complete when the current stage is done.",
            "Pass a summary= string and any required outputs= for this stage.",
            "",
            "Stages:",
        ]
        for index, stage in enumerate(self._stages, start=1):
            required = ""
            if stage.required_output_keys:
                required = f" -> required: {', '.join(stage.required_output_keys)}"
            lines.append(f"  {index}. {stage.name}: {stage.description}{required}")
        return "\n".join(lines)

    def _describe_rules(self) -> tuple[LayerRuleRecord, ...]:
        rules: list[LayerRuleRecord] = [
            LayerRuleRecord(
                rule_id="STAGE-TOOL-SWAP",
                description=(
                    "Each stage's tools are installed into the StageAwareToolExecutor via "
                    "swap_stage_tools() when a stage transition completes."
                ),
                enforced_at="on_post_reset",
                enforcement_type="inject",
            ),
            LayerRuleRecord(
                rule_id="STAGE-TOOL-FILTER",
                description=(
                    "Base executor tools not matching the current stage's allowed tool "
                    "patterns are removed before the next model turn."
                ),
                enforced_at="filter_tool_keys",
                enforcement_type="block",
            ),
            LayerRuleRecord(
                rule_id="STAGE-ADVANCE",
                description=(
                    "Stage advancement happens after a successful stage_complete call when "
                    "the next reset completes."
                ),
                enforced_at="on_post_reset",
                enforcement_type="advance",
            ),
        ]
        for stage in self._stages:
            if not stage.required_output_keys:
                continue
            rules.append(
                LayerRuleRecord(
                    rule_id=f"STAGE-{stage.name.upper()}-OUTPUTS",
                    description=(
                        f"'{stage.name}': stage_complete is blocked unless outputs= contains "
                        f"[{', '.join(stage.required_output_keys)}]."
                    ),
                    enforced_at="on_tool_result",
                    enforcement_type="transform",
                )
            )
        return tuple(rules)

    def _describe_configuration(self) -> dict[str, Any]:
        return {
            "stage_count": len(self._stages),
            "current_stage": self._current_stage.name,
            "current_index": self._current_index,
            "stages": [stage._describe_configuration() for stage in self._stages],
        }

    def get_parameter_sections(self) -> Sequence[AgentParameterSection]:
        static_sections = super().get_parameter_sections()
        stage = self._current_stage
        index = self._current_index
        total = len(self._stages)

        lines = [
            f"Stage {index + 1} of {total}: {stage.name.upper()}",
            stage.description,
        ]
        fragment = stage.build_system_prompt_fragment()
        if fragment:
            lines.extend(["", fragment])
        completion_hint = stage.get_completion_hint()
        if completion_hint:
            lines.extend(["", f"Done when: {completion_hint}"])
        if stage.required_output_keys:
            lines.extend(["", "Pass to stage_complete outputs=: " + ", ".join(stage.required_output_keys)])
        if index < len(self._stages) - 1:
            next_hint = stage.get_next_stage_hint()
            next_name = self._stages[index + 1].name
            lines.extend(["", next_hint or f"Next stage: {next_name}"])

        sections = [
            *static_sections,
            AgentParameterSection(title="Current Stage", content="\n".join(lines)),
        ]
        if self._prior_outputs:
            sections.append(
                AgentParameterSection(
                    title="Prior Stage Outputs",
                    content=json.dumps(self._prior_outputs, indent=2, default=str),
                )
            )
        return tuple(sections)

    def augment_system_prompt(self, prompt: str) -> str:
        stage = self._current_stage
        index = self._current_index
        total = len(self._stages)
        header_lines = [f"\n\n[STAGE {index + 1}/{total}: {stage.name.upper()}]"]
        fragment = stage.build_system_prompt_fragment()
        if fragment:
            header_lines.append(fragment)
        completion_hint = stage.get_completion_hint()
        if completion_hint:
            header_lines.append(f"Done when: {completion_hint}")
        if index < len(self._stages) - 1:
            next_hint = stage.get_next_stage_hint()
            next_name = self._stages[index + 1].name
            header_lines.append(next_hint or f"Next stage: {next_name}")
        header_lines.append(
            "Call formalization.stage_complete with summary= and any required outputs= when this stage is complete."
        )
        return prompt + "\n".join(header_lines)

    def get_formalization_tools(self) -> tuple[RegisteredTool, ...]:
        return (STAGE_COMPLETE_TOOL,)

    def filter_tool_keys(self, tool_keys: Sequence[str]) -> tuple[str, ...]:
        stage = self._current_stage
        patterns = stage.allowed_tool_patterns
        if not patterns:
            return tuple(tool_keys)

        stage_tool_keys: set[str] = set()
        if self._stage_executor is not None and getattr(self._stage_executor, "_stage_registry", None) is not None:
            stage_tool_keys = set(self._stage_executor._stage_registry.keys())

        return tuple(
            tool_key
            for tool_key in tool_keys
            if tool_key == STAGE_COMPLETE_TOOL.key
            or tool_key in stage_tool_keys
            or is_tool_allowed(tool_key, patterns)
        )

    def on_agent_prepare(self, *, agent_name: str, memory_path: str) -> None:
        self._agent_name = agent_name
        self._memory_path = Path(memory_path)
        self._load_prior_outputs()
        self._restore_stage_index()
        self._install_current_stage_tools()
        self._current_stage.on_enter(self._make_context())

    def on_tool_result(self, result: ToolResult) -> ToolResult:
        if result.tool_key != STAGE_COMPLETE_TOOL.key:
            return result

        stage = self._current_stage
        payload = result.output if isinstance(result.output, dict) else {}
        outputs = dict(payload.get("outputs", {}))

        missing = [key for key in stage.required_output_keys if key not in outputs]
        if missing:
            return ToolResult(
                tool_key=result.tool_key,
                output={
                    "error": (
                        "Stage completion blocked. Missing required outputs: "
                        f"{', '.join(missing)}. Resubmit with all required outputs."
                    ),
                    "required": list(stage.required_output_keys),
                    "provided": sorted(outputs.keys()),
                    "missing": missing,
                },
            )

        try:
            is_complete = stage.is_complete(outputs)
        except Exception as exc:  # pragma: no cover - defensive runtime contract
            return ToolResult(
                tool_key=result.tool_key,
                output={
                    "error": f"Stage is_complete() raised: {exc}. Stage '{stage.name}' did not advance.",
                },
            )

        if not is_complete:
            return ToolResult(
                tool_key=result.tool_key,
                output={
                    "error": f"Stage is_complete() returned False for '{stage.name}'. Continue working.",
                    "outputs_received": outputs,
                },
            )

        stage.on_exit(outputs=outputs, context=self._make_context())
        self._completion_pending = True
        self._pending_outputs = outputs
        self._pending_summary = str(payload.get("summary", ""))
        return result

    def on_pre_reset(self) -> None:
        if self._completion_pending and self._current_stage.persist_outputs:
            self._persist_stage_outputs(self._current_stage.name, self._pending_outputs)

    def on_post_reset(self) -> None:
        self._reset_count += 1
        if not self._completion_pending:
            return

        current_stage = self._current_stage
        next_name = current_stage.get_next_stage(self._pending_outputs)
        if next_name is not None:
            if next_name not in self._stage_map:
                raise StageAdvancementError(
                    f"Stage '{current_stage.name}'.get_next_stage() returned '{next_name}', "
                    f"which is not a registered stage name. Registered stages: {list(self._stage_map)}."
                )
            self._current_index = self._index_map[next_name]
        elif not self._is_final_stage:
            self._current_index += 1

        self._completion_pending = False
        self._prior_outputs[current_stage.name] = dict(self._pending_outputs)
        self._pending_outputs = {}
        self._pending_summary = ""
        self._persist_stage_index()
        self._install_current_stage_tools()
        self._current_stage.on_enter(self._make_context())

    @property
    def current_stage(self) -> StageSpec:
        return self._current_stage

    @property
    def current_stage_index(self) -> int:
        return self._current_index

    @property
    def prior_outputs(self) -> dict[str, dict[str, Any]]:
        return dict(self._prior_outputs)

    @property
    def _current_stage(self) -> StageSpec:
        return self._stages[self._current_index]

    @property
    def _is_final_stage(self) -> bool:
        return self._current_index >= len(self._stages) - 1

    def _make_context(self) -> StageContext:
        return StageContext(
            agent_name=self._agent_name,
            memory_path=self._memory_path or Path("."),
            reset_count=self._reset_count,
            stage_index=self._current_index,
            stage_name=self._current_stage.name,
            prior_stage_outputs=dict(self._prior_outputs),
            metadata={},
        )

    def _install_current_stage_tools(self) -> None:
        if self._stage_executor is None:
            return
        memory_path = self._memory_path or Path(".")
        self._stage_executor.swap_stage_tools(self._current_stage.build_tools(memory_path))

    def _persist_stage_outputs(self, stage_name: str, outputs: dict[str, Any]) -> None:
        if self._memory_path is None:
            return
        path = self._memory_path / _STAGE_OUTPUTS_FILENAME
        existing: dict[str, Any] = {}
        if path.exists():
            existing = json.loads(path.read_text(encoding="utf-8"))
        existing[stage_name] = outputs
        path.write_text(json.dumps(existing, indent=2, default=str), encoding="utf-8")

    def _load_prior_outputs(self) -> None:
        if self._memory_path is None:
            return
        path = self._memory_path / _STAGE_OUTPUTS_FILENAME
        if path.exists():
            self._prior_outputs = json.loads(path.read_text(encoding="utf-8"))

    def _persist_stage_index(self) -> None:
        if self._memory_path is None:
            return
        path = self._memory_path / _STAGE_INDEX_FILENAME
        path.write_text(
            json.dumps(
                {
                    "current_index": self._current_index,
                    "current_stage": self._current_stage.name,
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    def _restore_stage_index(self) -> None:
        if self._memory_path is None:
            return
        path = self._memory_path / _STAGE_INDEX_FILENAME
        if not path.exists():
            return
        payload = json.loads(path.read_text(encoding="utf-8"))
        stage_name = payload.get("current_stage")
        if stage_name in self._index_map:
            self._current_index = self._index_map[stage_name]
