"""
===============================================================================
File: harnessiq/interfaces/formalization/behaviors/recovery/__init__.py

What this file does:
- Defines the package-level export surface for
  `harnessiq/interfaces/formalization/behaviors/recovery` within the HarnessIQ
  runtime.
- Recovery behavior formalization interfaces.

Use cases:
- Import BaseErrorRecoveryLayer, ErrorEscalationBehavior, RecoveryStrategySpec,
  RetryStrategyBehavior, StuckDetectionBehavior from one stable package entry
  point.
- Read this module to understand what
  `harnessiq/interfaces/formalization/behaviors/recovery` intends to expose
  publicly.

How to use it:
- Import from `harnessiq/interfaces/formalization/behaviors/recovery` when you
  want the supported facade instead of reaching through deeper internal
  modules.

Intent:
- Keep the public surface for
  `harnessiq/interfaces/formalization/behaviors/recovery` explicit,
  discoverable, and easier to maintain.
===============================================================================
"""

from .base import BaseErrorRecoveryLayer, RecoveryStrategySpec
from .escalation import ErrorEscalationBehavior
from .retry import RetryStrategyBehavior
from .stuck import StuckDetectionBehavior

__all__ = [
    "BaseErrorRecoveryLayer",
    "ErrorEscalationBehavior",
    "RecoveryStrategySpec",
    "RetryStrategyBehavior",
    "StuckDetectionBehavior",
]
