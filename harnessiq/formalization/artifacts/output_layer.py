from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

from harnessiq.formalization.base import BaseFormalizationLayer, LayerRuleRecord
from harnessiq.shared.agents import AgentParameterSection
from harnessiq.shared.tools import (
    ARTIFACT_APPEND_RUN_LOG,
    ARTIFACT_WRITE_CSV,
    ARTIFACT_WRITE_JSON,
    ARTIFACT_WRITE_MARKDOWN,
    CONTROL_MARK_COMPLETE,
    FILESYSTEM_REPLACE_TEXT_FILE,
    RegisteredTool,
    ToolResult,
)

from .format_map import resolve_output_path, resolve_write_tool_key
from .output_spec import (
    CompletionRequirement,
    OutputArtifactSpec,
    validate_output_artifact_specs,
)

_ARTIFACT_WRITE_KEYS = frozenset(
    {
        ARTIFACT_WRITE_MARKDOWN,
        ARTIFACT_WRITE_JSON,
        ARTIFACT_WRITE_CSV,
        ARTIFACT_APPEND_RUN_LOG,
    }
)


class OutputArtifactLayer(BaseFormalizationLayer):
    """Track required outputs, contribute write tools, and gate completion."""

    def __init__(
        self,
        artifacts: Sequence[OutputArtifactSpec],
        *,
        completion_requirement: CompletionRequirement = "all",
        required_names: Sequence[str] = (),
    ) -> None:
        validated = validate_output_artifact_specs(artifacts)
        if not validated:
            raise ValueError("OutputArtifactLayer requires at least one OutputArtifactSpec.")

        if completion_requirement not in {"all", "specific", "none"}:
            raise ValueError(f"Unsupported completion requirement '{completion_requirement}'.")

        if completion_requirement != "specific" and required_names:
            raise ValueError(
                "required_names may only be provided when completion_requirement='specific'."
            )

        seen = {spec.name for spec in validated}
        if completion_requirement == "specific":
            if not required_names:
                raise ValueError(
                    "completion_requirement='specific' requires at least one name in required_names."
                )
            unknown = sorted(name for name in required_names if name not in seen)
            if unknown:
                raise ValueError(
                    f"required_names contains unknown artifact names: {unknown}."
                )
            required = frozenset(required_names)
        elif completion_requirement == "all":
            required = frozenset(spec.name for spec in validated)
        else:
            required = frozenset()

        self._specs: tuple[OutputArtifactSpec, ...] = validated
        self._spec_map: dict[str, OutputArtifactSpec] = {spec.name: spec for spec in validated}
        self._completion_requirement = completion_requirement
        self._required_names = required
        self._memory_path: Path | None = None
        self._written: set[str] = set()
        self._completion_pending = False
        self._run_completed = False

    @property
    def layer_id(self) -> str:
        return "OutputArtifactLayer"

    def _describe_identity(self) -> str:
        names = ", ".join(spec.name for spec in self._specs)
        gate = {
            "all": "All declared outputs must be written before the run completes.",
            "specific": (
                "These outputs must be written before completion: "
                f"{', '.join(sorted(self._required_names))}."
            ),
            "none": "No completion gate is enforced.",
        }[self._completion_requirement]
        return (
            f"You are expected to produce {len(self._specs)} output artifact(s): {names}. "
            "The exact write tool and target path for each is shown in the Output Artifacts section. "
            f"{gate}"
        )

    def _describe_contract(self) -> str:
        lines = [
            "Use the write tools shown for each output. Do not write outputs to arbitrary paths.",
            "Use the specified tools so the harness can track which outputs have been produced.",
            "",
            "Declared outputs:",
        ]
        for spec in self._specs:
            gate_note = " [required for completion]" if spec.name in self._required_names else ""
            lines.append(
                f"  {spec.name} ({spec.file_format}){gate_note}: {spec.description}"
            )
            lines.append(f"    Write with: {self._render_write_guidance(spec)}")
        return "\n".join(lines)

    def _describe_rules(self) -> tuple[LayerRuleRecord, ...]:
        rules: list[LayerRuleRecord] = [
            LayerRuleRecord(
                rule_id="OUTPUT-TRACK-WRITES",
                description=(
                    "Every artifact.write_* and filesystem.replace_text_file result is "
                    "observed in on_tool_result. Matching declared outputs are marked as written "
                    "for the duration of the run."
                ),
                enforced_at="on_tool_result",
                enforcement_type="observe",
            )
        ]
        if self._completion_requirement != "none":
            names = ", ".join(sorted(self._required_names))
            rules.append(
                LayerRuleRecord(
                    rule_id="OUTPUT-GATE-COMPLETION",
                    description=(
                        "control.mark_complete is intercepted in on_tool_result. "
                        f"If [{names}] have not all been written, the result is replaced with "
                        "an error payload and the run does not complete."
                    ),
                    enforced_at="on_tool_result",
                    enforcement_type="transform",
                )
            )
        return tuple(rules)

    def _describe_configuration(self) -> dict[str, Any]:
        memory_path = self._memory_path or Path(".")
        return {
            "artifact_count": len(self._specs),
            "completion_requirement": self._completion_requirement,
            "required_names": sorted(self._required_names),
            "artifacts": [
                {
                    "name": spec.name,
                    "description": spec.description,
                    "format": spec.file_format,
                    "write_tool": resolve_write_tool_key(spec),
                    "contributes_write_tool": spec.contributes_write_tool,
                    "path": str(resolve_output_path(spec, memory_path)),
                }
                for spec in self._specs
            ],
        }

    def get_parameter_sections(self) -> Sequence[AgentParameterSection]:
        static_sections = super().get_parameter_sections()
        memory_path = self._memory_path or Path("memory")

        lines = [f"Expected outputs ({len(self._specs)} artifact(s)):", ""]
        for spec in self._specs:
            status = "written" if spec.name in self._written else "not yet written"
            gate = " [required]" if spec.name in self._required_names else ""
            lines.extend(
                [
                    f"{spec.name}{gate}  [{status}]",
                    f"  {spec.description}",
                    f"  Format: {spec.file_format}",
                    f"  Write with: {self._render_write_guidance(spec, memory_path=memory_path)}",
                    f"  Output path: {resolve_output_path(spec, memory_path)}",
                    "",
                ]
            )

        return (
            *static_sections,
            AgentParameterSection(
                title="Output Artifacts",
                content="\n".join(lines).rstrip(),
            ),
        )

    def augment_system_prompt(self, prompt: str) -> str:
        doc = self.describe()
        return (
            f"{prompt}\n\n"
            "[OUTPUT ARTIFACTS]\n"
            f"{doc.identity}\n\n"
            f"{doc.contract}"
        )

    def get_formalization_tools(self) -> Sequence[RegisteredTool]:
        if self._memory_path is None:
            return ()
        return self._build_write_tools()

    def on_agent_prepare(self, *, agent_name: str, memory_path: str) -> None:
        del agent_name
        self._memory_path = Path(memory_path)
        self._written = set()
        self._completion_pending = False
        self._run_completed = False
        for spec in self._specs:
            resolve_output_path(spec, self._memory_path).parent.mkdir(parents=True, exist_ok=True)

    def on_tool_result(self, result: ToolResult) -> ToolResult:
        self._run_completed = False
        self._track_write_result(result)

        if result.tool_key != CONTROL_MARK_COMPLETE:
            return result

        if self._completion_requirement != "none":
            missing = self._missing_required_outputs()
            if missing:
                self._completion_pending = False
                return ToolResult(
                    tool_key=result.tool_key,
                    output={
                        "error": (
                            "Completion blocked. Required output artifact(s) not yet written: "
                            f"{', '.join(missing)}. Rule: OUTPUT-GATE-COMPLETION. "
                            "Write all required outputs before calling mark_complete."
                        ),
                        "required": sorted(self._required_names),
                        "written": sorted(self._written),
                        "missing": missing,
                    },
                )

        self._completion_pending = True
        return result

    def on_post_reset(self) -> None:
        self._run_completed = bool(self._completion_pending)
        self._completion_pending = False

    @property
    def completion_pending(self) -> bool:
        return self._completion_pending

    @property
    def run_completed(self) -> bool:
        return self._run_completed

    def _build_write_tools(self) -> tuple[RegisteredTool, ...]:
        from harnessiq.tools.artifact import ArtifactToolRuntime, create_artifact_tools
        from harnessiq.tools.filesystem import create_filesystem_tools

        needed_artifact_keys: set[str] = set()
        needs_replace_text = False
        for spec in self._specs:
            if not spec.contributes_write_tool:
                continue
            tool_key = resolve_write_tool_key(spec)
            if tool_key == FILESYSTEM_REPLACE_TEXT_FILE:
                needs_replace_text = True
            elif tool_key in _ARTIFACT_WRITE_KEYS:
                needed_artifact_keys.add(tool_key)

        tools: list[RegisteredTool] = []
        if needed_artifact_keys:
            artifact_tools = create_artifact_tools(runtime=ArtifactToolRuntime(root=self._memory_path))
            tools.extend(tool for tool in artifact_tools if tool.key in needed_artifact_keys)
        if needs_replace_text:
            filesystem_tools = create_filesystem_tools()
            tools.extend(tool for tool in filesystem_tools if tool.key == FILESYSTEM_REPLACE_TEXT_FILE)
        return tuple(tools)

    def _track_write_result(self, result: ToolResult) -> None:
        if result.tool_key in _ARTIFACT_WRITE_KEYS:
            payload = result.output if isinstance(result.output, dict) else {}
            written_name = str(payload.get("name", "")).strip()
            if written_name in self._spec_map:
                self._written.add(written_name)
            return

        if result.tool_key != FILESYSTEM_REPLACE_TEXT_FILE or self._memory_path is None:
            return

        payload = result.output if isinstance(result.output, dict) else {}
        written_path = str(payload.get("path", "")).strip()
        if not written_path:
            return

        normalized_written_path = str(Path(written_path))
        for spec in self._specs:
            if normalized_written_path == str(resolve_output_path(spec, self._memory_path)):
                self._written.add(spec.name)

    def _missing_required_outputs(self) -> list[str]:
        return sorted(self._required_names - self._written)

    def _render_write_guidance(
        self,
        spec: OutputArtifactSpec,
        *,
        memory_path: Path | None = None,
    ) -> str:
        tool_key = resolve_write_tool_key(spec)
        if tool_key == FILESYSTEM_REPLACE_TEXT_FILE:
            target_path = resolve_output_path(spec, memory_path or self._memory_path or Path("memory"))
            return f'{tool_key}(path="{target_path}", ...)'
        return f'{tool_key}(name="{spec.name}", ...)'


__all__ = ["OutputArtifactLayer"]
