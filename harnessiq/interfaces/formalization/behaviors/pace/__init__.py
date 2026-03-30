"""
===============================================================================
File: harnessiq/interfaces/formalization/behaviors/pace/__init__.py

What this file does:
- Defines the package-level export surface for
  `harnessiq/interfaces/formalization/behaviors/pace` within the HarnessIQ
  runtime.
- Execution-pace formalization layers.

Use cases:
- Import BaseExecutionPaceLayer, PaceRuleSpec, ProgressCheckpointBehavior,
  ReflectionCadenceBehavior, VerificationBehavior from one stable package entry
  point.
- Read this module to understand what
  `harnessiq/interfaces/formalization/behaviors/pace` intends to expose
  publicly.

How to use it:
- Import from `harnessiq/interfaces/formalization/behaviors/pace` when you want
  the supported facade instead of reaching through deeper internal modules.

Intent:
- Keep the public surface for
  `harnessiq/interfaces/formalization/behaviors/pace` explicit, discoverable,
  and easier to maintain.
===============================================================================
"""

from .base import BaseExecutionPaceLayer, PaceRuleSpec
from .checkpoint import ProgressCheckpointBehavior
from .reflection import ReflectionCadenceBehavior
from .verification import VerificationBehavior

__all__ = [
    "BaseExecutionPaceLayer",
    "PaceRuleSpec",
    "ProgressCheckpointBehavior",
    "ReflectionCadenceBehavior",
    "VerificationBehavior",
]
