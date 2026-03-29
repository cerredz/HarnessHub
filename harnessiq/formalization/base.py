"""Self-documenting formalization layer contracts for harness composition."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from fnmatch import fnmatch
from typing import Any, Literal

from harnessiq.shared.agents import (
    AgentContextMemoryUpdateRule,
    AgentParameterSection,
    json_parameter_section,
    render_json_parameter_content,
)
from harnessiq.shared.tools import ToolDefinition, ToolResult

FormalizationHookName = Literal[
    "augment_system_prompt",
    "filter_tool_keys",
    "get_parameter_sections",
    "on_agent_prepare",
    "on_post_reset",
    "on_pre_reset",
    "on_tool_result",
]
FormalizationEnforcementType = Literal[
    "advance",
    "allow",
    "block",
    "inject",
    "persist",
    "raise",
    "skip",
    "transform",
]


@dataclass(frozen=True, slots=True)
class LayerRuleRecord:
    """One auditable rule declared by a formalization layer."""

    rule_id: str
    description: str
    enforced_at: FormalizationHookName
    enforcement_type: FormalizationEnforcementType


@dataclass(frozen=True, slots=True)
class FormalizationDescription:
    """Structured self-description for one formalization layer."""

    layer_id: str
    identity: str
    contract: str
    rules: tuple[LayerRuleRecord, ...]
    configuration: Mapping[str, Any]

    def render(self) -> str:
        """Render the description for a developer or reviewer."""
        rules_block = "\n".join(
            f"  {rule.rule_id}  enforced_at={rule.enforced_at}  type={rule.enforcement_type}\n"
            f"    {rule.description}"
            for rule in self.rules
        ) or "  (none)"
        configuration = render_json_parameter_content(self.configuration)
        return (
            f"[{self.layer_id}]\n\n"
            f"IDENTITY\n{self.identity}\n\n"
            f"CONTRACT\n{self.contract}\n\n"
            f"RULES\n{rules_block}\n\n"
            f"CONFIGURATION\n{configuration}"
        ).rstrip()

    def render_for_agent(self) -> str:
        """Render the description for injection into the model context window."""
        rules_block = "\n".join(
            f"- [{rule.rule_id}] {rule.description}"
            for rule in self.rules
        ) or "- No explicit rules declared."
        return (
            f"[LAYER: {self.layer_id}]\n"
            f"{self.identity}\n\n"
            f"Behavioral contract:\n"
            f"{self.contract}\n\n"
            f"Enforced rules:\n"
            f"{rules_block}"
        ).rstrip()


@dataclass(frozen=True, slots=True)
class FieldSpec:
    """Describe one typed contract field."""

    name: str
    field_type: str
    description: str
    required: bool = False
    default: Any = None


@dataclass(frozen=True, slots=True)
class BudgetSpec:
    """Describe the execution budget for a contract layer."""

    max_tokens: int | None = None
    max_resets: int | None = None
    max_wall_seconds: float | None = None


@dataclass(frozen=True, slots=True)
class ArtifactSpec:
    """Describe one declared artifact for an artifact layer."""

    name: str
    artifact_type: str
    description: str
    required_before_complete: bool = False
    produced_by_tool: str | None = None


@dataclass(frozen=True, slots=True)
class HookBehaviorSpec:
    """Describe one hook-driven runtime behavior owned by a layer."""

    name: str
    description: str
    lifecycle_hook: FormalizationHookName
    mutates_context: bool = False


@dataclass(frozen=True, slots=True)
class StageSpec:
    """Describe one deterministic execution stage."""

    name: str
    description: str
    system_prompt_fragment: str = ""
    allowed_tool_patterns: tuple[str, ...] = ()
    required_output_keys: tuple[str, ...] = ()
    completion_hint: str | None = None


@dataclass(frozen=True, slots=True)
class RoleSpec:
    """Describe one role that can shape the active harness behavior."""

    name: str
    description: str
    system_prompt_fragment: str = ""
    allowed_tool_patterns: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class StateFieldSpec:
    """Describe one durable field managed by a state layer."""

    name: str
    field_type: str
    description: str
    update_rule: AgentContextMemoryUpdateRule = "overwrite"
    default: Any = None
    is_continuation_pointer: bool = False


class BaseFormalizationLayer(ABC):
    """Universal formalization-layer contract with self-documenting defaults."""

    @property
    def layer_id(self) -> str:
        """Return the stable public identifier for this layer instance."""
        return self.__class__.__name__

    def describe(self) -> FormalizationDescription:
        """Return the structured description for this layer."""
        return FormalizationDescription(
            layer_id=self.layer_id,
            identity=self._describe_identity(),
            contract=self._describe_contract(),
            rules=tuple(self._describe_rules()),
            configuration=dict(self._describe_configuration()),
        )

    def get_parameter_sections(self) -> tuple[AgentParameterSection, ...]:
        """Return formalization-owned context-window sections."""
        return (
            AgentParameterSection(
                title=f"Formalization: {self.layer_id}",
                content=self.describe().render_for_agent(),
            ),
        )

    def augment_system_prompt(self, system_prompt: str) -> str:
        """Return the model system prompt after this layer's augmentation."""
        return system_prompt

    def get_formalization_tools(self) -> tuple[ToolDefinition, ...]:
        """Return any tools contributed by this layer."""
        return ()

    def filter_tool_keys(self, tool_keys: Sequence[str]) -> tuple[str, ...]:
        """Return the model-visible tool keys after this layer's filtering."""
        return tuple(tool_keys)

    def on_agent_prepare(self, *, agent_name: str, memory_path: str) -> None:
        """Run deterministic setup before the agent loop starts."""
        del agent_name, memory_path

    def on_tool_result(self, result: ToolResult) -> ToolResult:
        """Inspect or transform one tool result before it is recorded."""
        return result

    def on_pre_reset(self) -> None:
        """Run deterministic work immediately before the context resets."""

    def on_post_reset(self) -> None:
        """Run deterministic work immediately after the context resets."""

    def _describe_identity(self) -> str:
        """Return the default identity prose for this formalization layer."""
        rules = tuple(self._describe_rules())
        enforced_at = sorted({rule.enforced_at for rule in rules})
        hooks_text = (
            f" It declares {len(rules)} rule(s) across: {', '.join(enforced_at)}."
            if rules
            else ""
        )
        return (
            f"You are operating inside the {self.layer_id} formalization layer.{hooks_text} "
            "All declared rules are intended to be enforced deterministically in Python code."
        )

    @abstractmethod
    def _describe_contract(self) -> str:
        """Return the behavioral contract for this layer."""

    @abstractmethod
    def _describe_rules(self) -> Sequence[LayerRuleRecord]:
        """Return the auditable rules declared by this layer."""

    @abstractmethod
    def _describe_configuration(self) -> Mapping[str, Any]:
        """Return the active configuration for this layer."""

    @staticmethod
    def _format_field(field: FieldSpec) -> str:
        required = "required" if field.required else "optional"
        default = "" if field.default is None else f" default={field.default!r}"
        return f"- {field.name} ({field.field_type}, {required}): {field.description}.{default}"

    @staticmethod
    def _format_budget(budget: BudgetSpec | None) -> str:
        if budget is None:
            return "No explicit execution budget declared."
        parts: list[str] = []
        if budget.max_tokens is not None:
            parts.append(f"{budget.max_tokens} tokens")
        if budget.max_resets is not None:
            parts.append(f"{budget.max_resets} resets")
        if budget.max_wall_seconds is not None:
            parts.append(f"{budget.max_wall_seconds:g}s wall time")
        return ", ".join(parts) if parts else "No explicit execution budget declared."

    @staticmethod
    def _filter_with_patterns(tool_keys: Sequence[str], patterns: Sequence[str]) -> tuple[str, ...]:
        if not patterns:
            return tuple(tool_keys)
        return tuple(
            tool_key
            for tool_key in tool_keys
            if any(fnmatch(tool_key, pattern) for pattern in patterns)
        )


class BaseContractLayer(BaseFormalizationLayer, ABC):
    """Typed base for execution-contract formalization layers."""

    @abstractmethod
    def get_input_spec(self) -> Sequence[FieldSpec]:
        """Return the declared input fields for this contract."""

    @abstractmethod
    def get_output_spec(self) -> Sequence[FieldSpec]:
        """Return the declared output fields for this contract."""

    @abstractmethod
    def get_budget_spec(self) -> BudgetSpec | None:
        """Return the declared execution budget for this contract."""

    def get_contract_rules(self) -> Sequence[LayerRuleRecord]:
        """Return the default rule set for this contract layer."""
        rules: list[LayerRuleRecord] = []
        required_inputs = [field.name for field in self.get_input_spec() if field.required]
        if required_inputs:
            rules.append(
                LayerRuleRecord(
                    rule_id="CONTRACT-INPUTS",
                    description=(
                        "Required inputs must exist before substantive work begins: "
                        + ", ".join(required_inputs)
                        + "."
                    ),
                    enforced_at="on_agent_prepare",
                    enforcement_type="raise",
                )
            )
        required_outputs = [field.name for field in self.get_output_spec() if field.required]
        if required_outputs:
            rules.append(
                LayerRuleRecord(
                    rule_id="CONTRACT-OUTPUTS",
                    description=(
                        "Required outputs must exist before the harness is considered complete: "
                        + ", ".join(required_outputs)
                        + "."
                    ),
                    enforced_at="on_tool_result",
                    enforcement_type="raise",
                )
            )
        budget = self.get_budget_spec()
        if budget is not None:
            rules.append(
                LayerRuleRecord(
                    rule_id="CONTRACT-BUDGET",
                    description=f"Execution must stay within the declared budget: {self._format_budget(budget)}.",
                    enforced_at="on_tool_result",
                    enforcement_type="raise",
                )
            )
        return tuple(rules)

    def _describe_identity(self) -> str:
        required_inputs = [field.name for field in self.get_input_spec() if field.required]
        required_outputs = [field.name for field in self.get_output_spec() if field.required]
        return (
            "You are operating under an execution contract. "
            f"Required inputs: {', '.join(required_inputs) or 'none'}. "
            f"Required outputs: {', '.join(required_outputs) or 'none'}. "
            f"Budget: {self._format_budget(self.get_budget_spec())}."
        )

    def _describe_contract(self) -> str:
        inputs = "\n".join(self._format_field(field) for field in self.get_input_spec()) or "- No input fields declared."
        outputs = "\n".join(self._format_field(field) for field in self.get_output_spec()) or "- No output fields declared."
        return (
            "Inputs:\n"
            f"{inputs}\n\n"
            "Outputs:\n"
            f"{outputs}\n\n"
            f"Budget: {self._format_budget(self.get_budget_spec())}"
        )

    def _describe_rules(self) -> Sequence[LayerRuleRecord]:
        return tuple(self.get_contract_rules())

    def _describe_configuration(self) -> Mapping[str, Any]:
        budget = self.get_budget_spec()
        return {
            "inputs": [asdict(field) for field in self.get_input_spec()],
            "outputs": [asdict(field) for field in self.get_output_spec()],
            "budget": None if budget is None else asdict(budget),
        }


class BaseArtifactLayer(BaseFormalizationLayer, ABC):
    """Typed base for artifact-production formalization layers."""

    @abstractmethod
    def get_artifact_specs(self) -> Sequence[ArtifactSpec]:
        """Return the declared artifacts tracked by this layer."""

    def get_artifact_rules(self) -> Sequence[LayerRuleRecord]:
        """Return the default rule set for this artifact layer."""
        required_artifacts = [
            spec.name for spec in self.get_artifact_specs() if spec.required_before_complete
        ]
        rules: list[LayerRuleRecord] = []
        if required_artifacts:
            rules.append(
                LayerRuleRecord(
                    rule_id="ARTIFACT-REQUIRED",
                    description=(
                        "The following artifacts must be produced before completion: "
                        + ", ".join(required_artifacts)
                        + "."
                    ),
                    enforced_at="on_tool_result",
                    enforcement_type="raise",
                )
            )
        return tuple(rules)

    def _describe_identity(self) -> str:
        required = [spec.name for spec in self.get_artifact_specs() if spec.required_before_complete]
        return (
            "You are operating under an artifact production contract. "
            f"This layer tracks {len(tuple(self.get_artifact_specs()))} artifact(s). "
            f"Required before completion: {', '.join(required) or 'none'}."
        )

    def _describe_contract(self) -> str:
        specs = "\n".join(
            (
                f"- {spec.name} ({spec.artifact_type}): {spec.description}."
                + (" Required before completion." if spec.required_before_complete else "")
                + (f" Produced by `{spec.produced_by_tool}`." if spec.produced_by_tool else "")
            )
            for spec in self.get_artifact_specs()
        ) or "- No artifacts declared."
        return f"Declared artifacts:\n{specs}"

    def _describe_rules(self) -> Sequence[LayerRuleRecord]:
        return tuple(self.get_artifact_rules())

    def _describe_configuration(self) -> Mapping[str, Any]:
        return {
            "artifacts": [asdict(spec) for spec in self.get_artifact_specs()],
        }


class BaseHookLayer(BaseFormalizationLayer, ABC):
    """Typed base for hook-oriented formalization layers."""

    @abstractmethod
    def get_hook_behaviors(self) -> Sequence[HookBehaviorSpec]:
        """Return the hook behaviors owned by this layer."""

    def get_hook_rules(self) -> Sequence[LayerRuleRecord]:
        """Return the default rule set for this hook layer."""
        return tuple(
            LayerRuleRecord(
                rule_id=f"HOOK-{behavior.lifecycle_hook.upper()}-{behavior.name.upper().replace(' ', '-')}",
                description=behavior.description,
                enforced_at=behavior.lifecycle_hook,
                enforcement_type="transform" if behavior.mutates_context else "allow",
            )
            for behavior in self.get_hook_behaviors()
        )

    def _describe_identity(self) -> str:
        hooks = tuple(self.get_hook_behaviors())
        phases = sorted({hook.lifecycle_hook for hook in hooks})
        return (
            "You are operating under formalization-owned hook behavior. "
            f"This layer declares {len(hooks)} hook behavior(s) across: {', '.join(phases) or 'no hooks'}."
        )

    def _describe_contract(self) -> str:
        behaviors = "\n".join(
            f"- {behavior.name} ({behavior.lifecycle_hook}): {behavior.description}."
            for behavior in self.get_hook_behaviors()
        ) or "- No hook behaviors declared."
        return f"Hook behaviors:\n{behaviors}"

    def _describe_rules(self) -> Sequence[LayerRuleRecord]:
        return tuple(self.get_hook_rules())

    def _describe_configuration(self) -> Mapping[str, Any]:
        return {
            "hook_behaviors": [asdict(behavior) for behavior in self.get_hook_behaviors()],
        }


class BaseStageLayer(BaseFormalizationLayer, ABC):
    """Typed base for deterministic staged execution layers."""

    @abstractmethod
    def get_stages(self) -> Sequence[StageSpec]:
        """Return the ordered stage specification for this layer."""

    @abstractmethod
    def get_current_stage_index(self) -> int:
        """Return the zero-based active stage index."""

    @property
    def current_stage(self) -> StageSpec:
        """Return the currently active stage."""
        stages = tuple(self.get_stages())
        return stages[self.get_current_stage_index()]

    def augment_system_prompt(self, system_prompt: str) -> str:
        fragment = self.current_stage.system_prompt_fragment.strip()
        if not fragment:
            return system_prompt
        return f"{system_prompt}\n\n{fragment}"

    def filter_tool_keys(self, tool_keys: Sequence[str]) -> tuple[str, ...]:
        return self._filter_with_patterns(tool_keys, self.current_stage.allowed_tool_patterns)

    def get_parameter_sections(self) -> tuple[AgentParameterSection, ...]:
        current_stage = self.current_stage
        stage_payload = {
            "stage_index": self.get_current_stage_index(),
            "stage_name": current_stage.name,
            "description": current_stage.description,
            "required_output_keys": list(current_stage.required_output_keys),
            "completion_hint": current_stage.completion_hint,
            "allowed_tool_patterns": list(current_stage.allowed_tool_patterns),
        }
        return (
            *super().get_parameter_sections(),
            json_parameter_section("Current Stage", stage_payload),
        )

    def _describe_identity(self) -> str:
        names = [stage.name for stage in self.get_stages()]
        return (
            f"You are executing a {len(names)}-stage harness: {' -> '.join(names) or 'no stages declared'}. "
            "Stages execute in order and the active stage shapes both prompt context and tool visibility."
        )

    def _describe_contract(self) -> str:
        stage_lines = []
        for index, stage in enumerate(self.get_stages(), start=1):
            hint = "" if stage.completion_hint is None else f" Done when: {stage.completion_hint}."
            required = (
                ""
                if not stage.required_output_keys
                else f" Required outputs: {', '.join(stage.required_output_keys)}."
            )
            stage_lines.append(f"- {index}. {stage.name}: {stage.description}.{required}{hint}")
        return "Ordered stages:\n" + ("\n".join(stage_lines) or "- No stages declared.")

    def _describe_rules(self) -> Sequence[LayerRuleRecord]:
        rules: list[LayerRuleRecord] = [
            LayerRuleRecord(
                rule_id="STAGE-TOOL-FILTER",
                description="The active stage narrows the visible tool surface to the stage's allowed tool patterns.",
                enforced_at="filter_tool_keys",
                enforcement_type="block",
            )
        ]
        for index, stage in enumerate(self.get_stages(), start=1):
            if not stage.required_output_keys:
                continue
            rules.append(
                LayerRuleRecord(
                    rule_id=f"STAGE-{index}-OUTPUTS",
                    description=(
                        f"Stage `{stage.name}` should not be considered complete until it has produced: "
                        + ", ".join(stage.required_output_keys)
                        + "."
                    ),
                    enforced_at="on_tool_result",
                    enforcement_type="transform",
                )
            )
        return tuple(rules)

    def _describe_configuration(self) -> Mapping[str, Any]:
        return {
            "current_stage_index": self.get_current_stage_index(),
            "stages": [asdict(stage) for stage in self.get_stages()],
        }


class BaseRoleLayer(BaseFormalizationLayer, ABC):
    """Typed base for multi-role formalization layers."""

    @abstractmethod
    def get_roles(self) -> Sequence[RoleSpec]:
        """Return the available roles for this layer."""

    @abstractmethod
    def get_active_role_index(self) -> int:
        """Return the zero-based active role index."""

    @property
    def active_role(self) -> RoleSpec:
        """Return the currently active role."""
        roles = tuple(self.get_roles())
        return roles[self.get_active_role_index()]

    def augment_system_prompt(self, system_prompt: str) -> str:
        fragment = self.active_role.system_prompt_fragment.strip()
        if not fragment:
            return system_prompt
        return f"{system_prompt}\n\n{fragment}"

    def filter_tool_keys(self, tool_keys: Sequence[str]) -> tuple[str, ...]:
        return self._filter_with_patterns(tool_keys, self.active_role.allowed_tool_patterns)

    def _describe_identity(self) -> str:
        return (
            f"You are operating with {len(tuple(self.get_roles()))} declared role(s). "
            f"The active role is `{self.active_role.name}`."
        )

    def _describe_contract(self) -> str:
        lines = "\n".join(
            f"- {role.name}: {role.description}."
            for role in self.get_roles()
        ) or "- No roles declared."
        return f"Role definitions:\n{lines}"

    def _describe_rules(self) -> Sequence[LayerRuleRecord]:
        return (
            LayerRuleRecord(
                rule_id="ROLE-TOOL-FILTER",
                description="The active role narrows the visible tool surface to its allowed tool patterns.",
                enforced_at="filter_tool_keys",
                enforcement_type="block",
            ),
        )

    def _describe_configuration(self) -> Mapping[str, Any]:
        return {
            "active_role_index": self.get_active_role_index(),
            "roles": [asdict(role) for role in self.get_roles()],
        }


class BaseStateLayer(BaseFormalizationLayer, ABC):
    """Typed base for durable state formalization layers."""

    @abstractmethod
    def get_state_fields(self) -> Sequence[StateFieldSpec]:
        """Return the typed state schema for this layer."""

    @abstractmethod
    def get_state_snapshot(self) -> Mapping[str, Any]:
        """Return the current durable state snapshot."""

    def get_parameter_sections(self) -> tuple[AgentParameterSection, ...]:
        return (
            *super().get_parameter_sections(),
            json_parameter_section("Formalization State", self.get_state_snapshot()),
        )

    def _describe_identity(self) -> str:
        pointer_names = [
            field.name for field in self.get_state_fields() if field.is_continuation_pointer
        ]
        pointer_text = ", ".join(pointer_names) or "none"
        return (
            "You are operating under explicit state semantics. "
            f"This layer manages {len(tuple(self.get_state_fields()))} typed field(s). "
            f"Continuation pointer: {pointer_text}."
        )

    def _describe_contract(self) -> str:
        lines = "\n".join(
            (
                f"- {field.name} ({field.field_type}, {field.update_rule}): {field.description}."
                + (" [CONTINUATION POINTER]" if field.is_continuation_pointer else "")
            )
            for field in self.get_state_fields()
        ) or "- No state fields declared."
        return f"State schema:\n{lines}"

    def _describe_rules(self) -> Sequence[LayerRuleRecord]:
        rules: list[LayerRuleRecord] = [
            LayerRuleRecord(
                rule_id="STATE-PERSIST-PRE-RESET",
                description="State should be durably persisted before the context resets.",
                enforced_at="on_pre_reset",
                enforcement_type="persist",
            ),
            LayerRuleRecord(
                rule_id="STATE-RELOAD-POST-RESET",
                description="State should be reloaded after the context resets so the next context window is synchronized.",
                enforced_at="on_post_reset",
                enforcement_type="inject",
            ),
        ]
        for field in self.get_state_fields():
            if field.update_rule != "write_once":
                continue
            rules.append(
                LayerRuleRecord(
                    rule_id=f"STATE-WRITE-ONCE-{field.name.upper().replace('-', '_')}",
                    description=f"`{field.name}` is write-once after its first durable assignment.",
                    enforced_at="on_pre_reset",
                    enforcement_type="skip",
                )
            )
        return tuple(rules)

    def _describe_configuration(self) -> Mapping[str, Any]:
        return {
            "fields": [asdict(field) for field in self.get_state_fields()],
            "snapshot": dict(self.get_state_snapshot()),
        }


class BaseToolContributionLayer(BaseFormalizationLayer, ABC):
    """Typed base for layers that contribute tools to the harness surface."""

    @abstractmethod
    def get_contributed_tools(self) -> Sequence[ToolDefinition]:
        """Return the tools contributed by this layer."""

    def get_formalization_tools(self) -> tuple[ToolDefinition, ...]:
        return tuple(self.get_contributed_tools())

    def _describe_identity(self) -> str:
        tools = tuple(self.get_contributed_tools())
        return f"You are operating with {len(tools)} tool(s) contributed by this formalization layer."

    def _describe_contract(self) -> str:
        tool_lines = "\n".join(
            f"- {tool.key}: {tool.description}"
            for tool in self.get_contributed_tools()
        ) or "- No tools contributed."
        return f"Contributed tools:\n{tool_lines}"

    def _describe_rules(self) -> Sequence[LayerRuleRecord]:
        if not tuple(self.get_contributed_tools()):
            return ()
        return (
            LayerRuleRecord(
                rule_id="TOOLS-CONTRIBUTED",
                description="This layer contributes additional tools to the harness surface.",
                enforced_at="get_parameter_sections",
                enforcement_type="inject",
            ),
        )

    def _describe_configuration(self) -> Mapping[str, Any]:
        return {
            "tool_keys": [tool.key for tool in self.get_contributed_tools()],
        }


__all__ = [
    "ArtifactSpec",
    "BaseArtifactLayer",
    "BaseContractLayer",
    "BaseFormalizationLayer",
    "BaseHookLayer",
    "BaseRoleLayer",
    "BaseStageLayer",
    "BaseStateLayer",
    "BaseToolContributionLayer",
    "BudgetSpec",
    "FieldSpec",
    "FormalizationDescription",
    "FormalizationEnforcementType",
    "FormalizationHookName",
    "HookBehaviorSpec",
    "LayerRuleRecord",
    "RoleSpec",
    "StageSpec",
    "StateFieldSpec",
]
