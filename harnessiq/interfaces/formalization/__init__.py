"""Public formalization interfaces for injectable harness structure.

The classes exported from this package define the SDK-facing abstraction layer
for formalization. A harness can depend on none of them, some of them, or many
of them. The common pattern is:

1. shared formalization records live in ``harnessiq.shared.formalization``
2. abstract behavioral contracts live here under ``harnessiq.interfaces``
3. concrete runtime implementations can later plug these layers into a harness

Each class lives in its own module so the package stays navigable as the
formalization surface grows.
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
    "BaseContractLayer",
    "BaseFormalizationLayer",
    "BaseHookLayer",
    "BaseRoleLayer",
    "BaseStageLayer",
    "BaseStateLayer",
    "BaseToolContributionLayer",
    "BudgetSpec",
    "CompletionRequirement",
    "FORMAT_EXTENSION_MAP",
    "FORMAT_TOOL_MAP",
    "FieldSpec",
    "FormalizationDescription",
    "FormalizationEnforcementType",
    "FormalizationHookName",
    "HookBehaviorSpec",
    "InjectionPolicy",
    "InputArtifactLayer",
    "InputArtifactSpec",
    "LayerRuleRecord",
    "OnOversize",
    "OutputArtifactMissingError",
    "OutputArtifactSpec",
    "RoleSpec",
    "StageSpec",
    "StateFieldSpec",
    "StateUpdateRule",
    "SupportedInputFormat",
    "SupportedOutputFormat",
    "resolve_artifact_path",
    "resolve_output_path",
    "resolve_write_tool_key",
    "validate_input_artifact_specs",
    "validate_output_artifact_specs",
]
