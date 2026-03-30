"""
===============================================================================
File: harnessiq/interfaces/formalization/behaviors/safety/__init__.py

What this file does:
- Defines the package-level export surface for
  `harnessiq/interfaces/formalization/behaviors/safety` within the HarnessIQ
  runtime.
- Safety behavior formalization interfaces.

Use cases:
- Import BaseSafetyBehaviorLayer, GuardrailSpec,
  IrreversibleActionGateBehavior, RateLimitBehavior, ScopeGuardBehavior from
  one stable package entry point.
- Read this module to understand what
  `harnessiq/interfaces/formalization/behaviors/safety` intends to expose
  publicly.

How to use it:
- Import from `harnessiq/interfaces/formalization/behaviors/safety` when you
  want the supported facade instead of reaching through deeper internal
  modules.

Intent:
- Keep the public surface for
  `harnessiq/interfaces/formalization/behaviors/safety` explicit, discoverable,
  and easier to maintain.
===============================================================================
"""

from .base import BaseSafetyBehaviorLayer, GuardrailSpec
from .irreversible import IrreversibleActionGateBehavior
from .rate_limit import RateLimitBehavior
from .scope_guard import ScopeGuardBehavior

__all__ = [
    "BaseSafetyBehaviorLayer",
    "GuardrailSpec",
    "IrreversibleActionGateBehavior",
    "RateLimitBehavior",
    "ScopeGuardBehavior",
]
