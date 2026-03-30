"""
===============================================================================
File: harnessiq/interfaces/formalization.py

What this file does:
- Provides the public import facade for the formalization interface and runtime
  surface exposed by the SDK.
- Compatibility exports for formalization-layer contracts.

Use cases:
- Import formalization contracts and implementations from one stable top-level
  module.

How to use it:
- Prefer importing shared formalization symbols from
  `harnessiq.interfaces.formalization` when you want the packaged facade
  instead of deep module paths.

Intent:
- Keep the formalization surface discoverable and stable for SDK consumers.
===============================================================================
"""

from harnessiq.formalization.base import (
    ArtifactSpec,
    BaseArtifactLayer,
    BaseContractLayer,
    BaseFormalizationLayer,
    BaseHookLayer,
    BaseRoleLayer,
    BaseStageLayer,
    BaseStateLayer,
    BaseToolContributionLayer,
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
)

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
