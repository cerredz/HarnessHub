"""
===============================================================================
File: harnessiq/interfaces/formalization/behaviors/reasoning/__init__.py

What this file does:
- Defines the package-level export surface for
  `harnessiq/interfaces/formalization/behaviors/reasoning` within the HarnessIQ
  runtime.
- Reasoning-behavior formalization layers.

Use cases:
- Import BaseReasoningBehaviorLayer, ReasoningRequirementSpec,
  PreActionReasoningBehavior, SelfCritiqueBehavior, HypothesisTestingBehavior
  from one stable package entry point.
- Read this module to understand what
  `harnessiq/interfaces/formalization/behaviors/reasoning` intends to expose
  publicly.

How to use it:
- Import from `harnessiq/interfaces/formalization/behaviors/reasoning` when you
  want the supported facade instead of reaching through deeper internal
  modules.

Intent:
- Keep the public surface for
  `harnessiq/interfaces/formalization/behaviors/reasoning` explicit,
  discoverable, and easier to maintain.
===============================================================================
"""

from .base import BaseReasoningBehaviorLayer, ReasoningRequirementSpec
from .hypothesis import HypothesisTestingBehavior
from .pre_action import PreActionReasoningBehavior
from .self_critique import SelfCritiqueBehavior

__all__ = [
    "BaseReasoningBehaviorLayer",
    "ReasoningRequirementSpec",
    "PreActionReasoningBehavior",
    "SelfCritiqueBehavior",
    "HypothesisTestingBehavior",
]
