from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from harnessiq.formalization.base import BaseFormalizationLayer, LayerRuleRecord
from harnessiq.shared.agents import AgentParameterSection

from .exceptions import ArtifactNotFoundError
from .format_map import resolve_artifact_path
from .input_spec import (
    InputArtifactSpec,
    InjectionPolicy,
    _FORMAT_SECTION_LABEL,
    validate_input_artifact_specs,
)


class InputArtifactLayer(BaseFormalizationLayer):
    """Inject declared input artifacts into the context window on every reset."""

    def __init__(self, artifacts: Sequence[InputArtifactSpec]) -> None:
        validated = validate_input_artifact_specs(artifacts)
        if not validated:
            raise ValueError("InputArtifactLayer requires at least one InputArtifactSpec.")
        self._specs = validated
        self._memory_path: Path | None = None
        self._reset_count = 0
        self._content_cache: dict[str, str | None] = {}

    @property
    def layer_id(self) -> str:
        return "InputArtifactLayer"

    def _describe_identity(self) -> str:
        names = ", ".join(spec.name for spec in self._specs)
        return (
            f"You have {len(self._specs)} input artifact(s) injected into your context window "
            f"on every reset: {names}. Their content appears in parameter sections, so you do "
            "not need to call tools to read these files."
        )

    def _describe_contract(self) -> str:
        lines = [
            "Input artifacts are read from disk and injected into the agent context window.",
            "",
            "Declared inputs:",
        ]
        for spec in self._specs:
            policy = spec.injection_policy
            limit = (
                f" (max {policy.max_chars:,} chars, {policy.on_oversize} if over)"
                if policy.max_chars is not None
                else ""
            )
            requirement = " [REQUIRED]" if spec.required else " [optional]"
            lines.append(
                f"  {spec.name} ({_FORMAT_SECTION_LABEL[spec.file_format]})"
                f"{limit}{requirement}: {spec.description}"
            )
        return "\n".join(lines)

    def _describe_rules(self) -> tuple[LayerRuleRecord, ...]:
        rules: list[LayerRuleRecord] = [
            LayerRuleRecord(
                rule_id="INPUT-INJECT-ON-RESET",
                description=(
                    "Input artifacts are injected into parameter sections on every context "
                    "assembly. Specs with refresh_on_reset=False use cached content from "
                    "on_agent_prepare; all others are re-read from disk."
                ),
                enforced_at="get_parameter_sections",
                enforcement_type="inject",
            ),
        ]
        for spec in self._specs:
            if spec.required:
                rules.append(
                    LayerRuleRecord(
                        rule_id=f"INPUT-REQUIRED-{spec.name.upper()}",
                        description=(
                            f"'{spec.name}' is required. ArtifactNotFoundError is raised from "
                            "on_agent_prepare if the file does not exist."
                        ),
                        enforced_at="on_agent_prepare",
                        enforcement_type="raise",
                    )
                )
            policy = spec.injection_policy
            if policy.max_chars is not None:
                rules.append(
                    LayerRuleRecord(
                        rule_id=f"INPUT-SIZE-{spec.name.upper()}",
                        description=(
                            f"'{spec.name}' content is checked against {policy.max_chars:,} chars "
                            f"and transformed with '{policy.on_oversize}' when oversized."
                        ),
                        enforced_at="get_parameter_sections",
                        enforcement_type="transform",
                    )
                )
            if policy.custom_filter is not None:
                rules.append(
                    LayerRuleRecord(
                        rule_id=f"INPUT-FILTER-{spec.name.upper()}",
                        description=(
                            f"'{spec.name}' uses a custom_filter callback. Returning False skips "
                            "injection for that reset."
                        ),
                        enforced_at="get_parameter_sections",
                        enforcement_type="skip",
                    )
                )
        return tuple(rules)

    def _describe_configuration(self) -> dict[str, Any]:
        return {
            "artifact_count": len(self._specs),
            "artifacts": [
                {
                    "name": spec.name,
                    "path": str(spec.path),
                    "description": spec.description,
                    "format": spec.file_format,
                    "required": spec.required,
                    "max_chars": spec.injection_policy.max_chars,
                    "on_oversize": spec.injection_policy.on_oversize,
                    "refresh_on_reset": spec.injection_policy.refresh_on_reset,
                    "has_custom_filter": spec.injection_policy.custom_filter is not None,
                }
                for spec in self._specs
            ],
        }

    def on_agent_prepare(self, *, agent_name: str, memory_path: str | Path) -> None:
        del agent_name
        self._memory_path = Path(memory_path)
        self._reset_count = 0
        self._content_cache.clear()
        for spec in self._specs:
            resolved = self._resolve_path(spec)
            if not resolved.exists():
                if spec.required:
                    raise ArtifactNotFoundError(
                        f"Required input artifact '{spec.name}' not found at '{resolved}'. "
                        f"Rule: INPUT-REQUIRED-{spec.name.upper()}."
                    )
                self._content_cache[spec.name] = None
                continue
            if not spec.injection_policy.refresh_on_reset:
                self._content_cache[spec.name] = self._read_file(spec)

    def on_post_reset(self) -> None:
        self._reset_count += 1

    def get_parameter_sections(self) -> tuple[AgentParameterSection, ...]:
        static_sections = super().get_parameter_sections()
        rendered_sections: list[AgentParameterSection] = []
        for spec in self._specs:
            policy = spec.injection_policy
            if policy.refresh_on_reset or spec.name not in self._content_cache:
                raw_content = self._read_file(spec)
            else:
                raw_content = self._content_cache.get(spec.name)
            section = self._render_section(spec, raw_content, policy)
            if section is not None:
                rendered_sections.append(section)
        return (*static_sections, *rendered_sections)

    def _resolve_path(self, spec: InputArtifactSpec) -> Path:
        if self._memory_path is None:
            raise RuntimeError("InputArtifactLayer memory path is not initialized.")
        return resolve_artifact_path(spec.path, memory_path=self._memory_path, name=spec.name)

    def _read_file(self, spec: InputArtifactSpec) -> str | None:
        resolved = self._resolve_path(spec)
        if not resolved.exists():
            return None
        try:
            content = resolved.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return None

        if spec.file_format == "json":
            try:
                return json.dumps(json.loads(content), indent=2, default=str)
            except (json.JSONDecodeError, TypeError, ValueError):
                return content
        if spec.file_format == "csv":
            lines = content.splitlines()
            if not lines:
                return content
            return f"[HEADER] {lines[0]}\n" + "\n".join(lines[1:])
        return content

    def _render_section(
        self,
        spec: InputArtifactSpec,
        content: str | None,
        policy: InjectionPolicy,
    ) -> AgentParameterSection | None:
        resolved = self._resolve_path(spec)
        format_label = _FORMAT_SECTION_LABEL[spec.file_format]
        title = (
            policy.section_title_template
            .replace("{name}", spec.name)
            .replace("{path}", str(resolved))
            .replace("{format}", format_label)
        )

        if content is None:
            return AgentParameterSection(
                title=title,
                content=f"[File not yet available: {resolved}]\n{spec.description}",
            )

        header_lines = [spec.description]
        if policy.include_path_in_section:
            header_lines.append(f"Path: {resolved}  ({format_label})")
        header = "\n".join(header_lines)

        rendered_content = content
        if policy.max_chars is not None and len(rendered_content) > policy.max_chars:
            if policy.on_oversize == "skip":
                return None
            if policy.on_oversize == "header_only":
                size_kb = len(rendered_content.encode("utf-8")) / 1024
                rendered_content = (
                    f"[Content omitted: {len(rendered_content):,} chars ({size_kb:.1f} KB). "
                    f"Use filesystem.read_text_file('{resolved}') to inspect it.]"
                )
            else:
                total_chars = len(rendered_content)
                rendered_content = rendered_content[: policy.max_chars]
                rendered_content += (
                    f"\n\n[TRUNCATED: {total_chars:,} total chars, "
                    f"showing first {policy.max_chars:,}]"
                )

        if policy.custom_filter is not None and not policy.custom_filter(rendered_content, self._reset_count):
            return None

        return AgentParameterSection(
            title=title,
            content=f"{header}\n\n{rendered_content}",
        )


__all__ = ["InputArtifactLayer"]
