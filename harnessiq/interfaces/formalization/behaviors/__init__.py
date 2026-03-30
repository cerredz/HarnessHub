"""
===============================================================================
File: harnessiq/interfaces/formalization/behaviors/__init__.py

What this file does:
- Defines the package-level export surface for
  `harnessiq/interfaces/formalization/behaviors` within the HarnessIQ runtime.
- Behavior-layer formalization interfaces.

Use cases:
- Import BaseBehaviorLayer, BaseExecutionPaceLayer, BaseErrorRecoveryLayer,
  BaseQualityBehaviorLayer, BaseReasoningBehaviorLayer, BaseSafetyBehaviorLayer
  from one stable package entry point.
- Read this module to understand what
  `harnessiq/interfaces/formalization/behaviors` intends to expose publicly.

How to use it:
- Import from `harnessiq/interfaces/formalization/behaviors` when you want the
  supported facade instead of reaching through deeper internal modules.

Intent:
- Keep the public surface for `harnessiq/interfaces/formalization/behaviors`
  explicit, discoverable, and easier to maintain.
===============================================================================
"""

from .base import (
    BaseBehaviorLayer,
    BehaviorConstraint,
    BehaviorEnforcementMode,
    BehaviorViolationAction,
)
from .pace import (
    BaseExecutionPaceLayer,
    PaceRuleSpec,
    ProgressCheckpointBehavior,
    ReflectionCadenceBehavior,
    VerificationBehavior,
)
from .quality import (
    BaseQualityBehaviorLayer,
    CitationRequirementBehavior,
    QualityCriterionSpec,
    QualityGateBehavior,
    ScopeEnforcementBehavior,
)
from .recovery import (
    BaseErrorRecoveryLayer,
    ErrorEscalationBehavior,
    RecoveryStrategySpec,
    RetryStrategyBehavior,
    StuckDetectionBehavior,
)
from .reasoning import (
    BaseReasoningBehaviorLayer,
    HypothesisTestingBehavior,
    PreActionReasoningBehavior,
    ReasoningRequirementSpec,
    SelfCritiqueBehavior,
)
from .safety import (
    BaseSafetyBehaviorLayer,
    GuardrailSpec,
    IrreversibleActionGateBehavior,
    RateLimitBehavior,
    ScopeGuardBehavior,
)
from .tool import (
    BaseToolBehaviorLayer,
    ToolCallLimitBehavior,
    ToolConstraintSpec,
    ToolCooldownBehavior,
    ToolSequencingBehavior,
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
