"""
===============================================================================
File: harnessiq/interfaces/formalization/__init__.py

What this file does:
- Defines the package-level export surface for
  `harnessiq/interfaces/formalization` within the HarnessIQ runtime.
- Public formalization interfaces for injectable harness structure. The classes
  exported from this package define the SDK-facing abstraction layer for
  formalization. A harness can depend on none of them, some of them, or many of
  them. The common pattern is: 1. shared formalization records live in
  ``harnessiq.shared.formalization`` 2. abstract behavioral contracts live here
  under ``harnessiq.interfaces`` 3. concrete runtime implementations can later
  plug these layers into a harness Each class lives in its own module so the
  package stays navigable as the formalization surface grows.

Use cases:
- Import ArtifactSpec, ArtifactNotFoundError, BaseArtifactLayer,
  BaseBehaviorLayer, BaseExecutionPaceLayer, BaseErrorRecoveryLayer from one
  stable package entry point.
- Read this module to understand what `harnessiq/interfaces/formalization`
  intends to expose publicly.

How to use it:
- Import from `harnessiq/interfaces/formalization` when you want the supported
  facade instead of reaching through deeper internal modules.

Intent:
- Keep the public surface for `harnessiq/interfaces/formalization` explicit,
  discoverable, and easier to maintain.
===============================================================================
"""

from __future__ import annotations

from harnessiq.shared.formalization import (
    ArtifactSpec,
    BudgetSpec,
    FieldSpec,
    FormalizationDescription,
    FormalizationEnforcementType,
    FormalizationHookName,
    HookBehaviorSpec,
    LayerRuleRecord,
    RoleSpec,
    StageSpec,
    StateFieldSpec,
    StateUpdateRule,
)

from .artifacts import (
    ArtifactNotFoundError,
    CompletionRequirement,
    FORMAT_EXTENSION_MAP,
    FORMAT_TOOL_MAP,
    InjectionPolicy,
    InputArtifactLayer,
    InputArtifactSpec,
    OnOversize,
    OutputArtifactMissingError,
    OutputArtifactLayer,
    OutputArtifactSpec,
    SupportedInputFormat,
    SupportedOutputFormat,
    resolve_artifact_path,
    resolve_output_path,
    resolve_write_tool_key,
    validate_input_artifact_specs,
    validate_output_artifact_specs,
)
from .artifact import BaseArtifactLayer
from .base import BaseFormalizationLayer
from .behaviors import (
    BaseBehaviorLayer,
    BaseExecutionPaceLayer,
    BaseErrorRecoveryLayer,
    BaseQualityBehaviorLayer,
    BaseReasoningBehaviorLayer,
    BaseSafetyBehaviorLayer,
    BaseToolBehaviorLayer,
    BehaviorConstraint,
    BehaviorEnforcementMode,
    BehaviorViolationAction,
    CitationRequirementBehavior,
    ErrorEscalationBehavior,
    GuardrailSpec,
    HypothesisTestingBehavior,
    IrreversibleActionGateBehavior,
    PaceRuleSpec,
    PreActionReasoningBehavior,
    ProgressCheckpointBehavior,
    QualityCriterionSpec,
    QualityGateBehavior,
    RateLimitBehavior,
    RecoveryStrategySpec,
    ReflectionCadenceBehavior,
    ReasoningRequirementSpec,
    RetryStrategyBehavior,
    ScopeEnforcementBehavior,
    ScopeGuardBehavior,
    SelfCritiqueBehavior,
    StuckDetectionBehavior,
    ToolCallLimitBehavior,
    ToolConstraintSpec,
    ToolCooldownBehavior,
    ToolSequencingBehavior,
    VerificationBehavior,
)
from .contract import BaseContractLayer
from .hook_layer import BaseHookLayer
from .role import BaseRoleLayer
from .stage import BaseStageLayer
from .state import BaseStateLayer
from .tool_contribution import BaseToolContributionLayer

__all__ = [
    "ArtifactSpec",
    "ArtifactNotFoundError",
    "BaseArtifactLayer",
    "BaseBehaviorLayer",
    "BaseExecutionPaceLayer",
    "BaseErrorRecoveryLayer",
    "BaseQualityBehaviorLayer",
    "BaseReasoningBehaviorLayer",
    "BaseSafetyBehaviorLayer",
    "BaseContractLayer",
    "BaseFormalizationLayer",
    "BaseHookLayer",
    "BaseRoleLayer",
    "BaseStageLayer",
    "BaseStateLayer",
    "BaseToolBehaviorLayer",
    "BaseToolContributionLayer",
    "BudgetSpec",
    "CompletionRequirement",
    "BehaviorConstraint",
    "BehaviorEnforcementMode",
    "BehaviorViolationAction",
    "CitationRequirementBehavior",
    "ErrorEscalationBehavior",
    "FORMAT_EXTENSION_MAP",
    "FORMAT_TOOL_MAP",
    "FieldSpec",
    "FormalizationDescription",
    "FormalizationEnforcementType",
    "FormalizationHookName",
    "GuardrailSpec",
    "HookBehaviorSpec",
    "InjectionPolicy",
    "InputArtifactLayer",
    "InputArtifactSpec",
    "LayerRuleRecord",
    "OnOversize",
    "OutputArtifactMissingError",
    "OutputArtifactLayer",
    "OutputArtifactSpec",
    "HypothesisTestingBehavior",
    "IrreversibleActionGateBehavior",
    "PaceRuleSpec",
    "PreActionReasoningBehavior",
    "ProgressCheckpointBehavior",
    "QualityCriterionSpec",
    "QualityGateBehavior",
    "RateLimitBehavior",
    "RecoveryStrategySpec",
    "ReflectionCadenceBehavior",
    "ReasoningRequirementSpec",
    "RetryStrategyBehavior",
    "RoleSpec",
    "ScopeEnforcementBehavior",
    "ScopeGuardBehavior",
    "SelfCritiqueBehavior",
    "StageSpec",
    "StateFieldSpec",
    "StuckDetectionBehavior",
    "StateUpdateRule",
    "SupportedInputFormat",
    "SupportedOutputFormat",
    "ToolCallLimitBehavior",
    "ToolConstraintSpec",
    "ToolCooldownBehavior",
    "ToolSequencingBehavior",
    "VerificationBehavior",
    "resolve_artifact_path",
    "resolve_output_path",
    "resolve_write_tool_key",
    "validate_input_artifact_specs",
    "validate_output_artifact_specs",
]
