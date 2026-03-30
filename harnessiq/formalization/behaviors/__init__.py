"""
===============================================================================
File: harnessiq/formalization/behaviors/__init__.py

What this file does:
- Defines the package-level export surface for
  `harnessiq/formalization/behaviors` within the HarnessIQ runtime.
- Legacy-compatible behavior formalization exports.

Use cases:
- Import BaseBehaviorLayer, BaseExecutionPaceLayer, BaseErrorRecoveryLayer,
  BaseQualityBehaviorLayer, BaseReasoningBehaviorLayer, BaseSafetyBehaviorLayer
  from one stable package entry point.
- Read this module to understand what `harnessiq/formalization/behaviors`
  intends to expose publicly.

How to use it:
- Import from `harnessiq/formalization/behaviors` when you want the supported
  facade instead of reaching through deeper internal modules.

Intent:
- Keep the public surface for `harnessiq/formalization/behaviors` explicit,
  discoverable, and easier to maintain.
===============================================================================
"""

from .base import (
    BaseBehaviorLayer,
    BehaviorConstraint,
    BehaviorEnforcementMode,
    BehaviorViolationAction,
)
from harnessiq.interfaces.formalization.behaviors import (
    BaseExecutionPaceLayer,
    BaseErrorRecoveryLayer,
    BaseQualityBehaviorLayer,
    BaseReasoningBehaviorLayer,
    BaseSafetyBehaviorLayer,
    BaseToolBehaviorLayer,
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

__all__ = [
    "BaseBehaviorLayer",
    "BaseExecutionPaceLayer",
    "BaseErrorRecoveryLayer",
    "BaseQualityBehaviorLayer",
    "BaseReasoningBehaviorLayer",
    "BaseSafetyBehaviorLayer",
    "BaseToolBehaviorLayer",
    "BehaviorConstraint",
    "BehaviorEnforcementMode",
    "BehaviorViolationAction",
    "CitationRequirementBehavior",
    "ErrorEscalationBehavior",
    "GuardrailSpec",
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
    "ScopeEnforcementBehavior",
    "ScopeGuardBehavior",
    "SelfCritiqueBehavior",
    "StuckDetectionBehavior",
    "ToolCallLimitBehavior",
    "ToolConstraintSpec",
    "ToolCooldownBehavior",
    "ToolSequencingBehavior",
    "VerificationBehavior",
]
