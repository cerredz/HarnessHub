"""
===============================================================================
File: harnessiq/interfaces/formalization/behaviors/tool/__init__.py

What this file does:
- Defines the package-level export surface for
  `harnessiq/interfaces/formalization/behaviors/tool` within the HarnessIQ
  runtime.
- Tool-behavior formalization layers.

Use cases:
- Import BaseToolBehaviorLayer, ToolConstraintSpec, ToolCallLimitBehavior,
  ToolCooldownBehavior, ToolSequencingBehavior from one stable package entry
  point.
- Read this module to understand what
  `harnessiq/interfaces/formalization/behaviors/tool` intends to expose
  publicly.

How to use it:
- Import from `harnessiq/interfaces/formalization/behaviors/tool` when you want
  the supported facade instead of reaching through deeper internal modules.

Intent:
- Keep the public surface for
  `harnessiq/interfaces/formalization/behaviors/tool` explicit, discoverable,
  and easier to maintain.
===============================================================================
"""

from .base import BaseToolBehaviorLayer, ToolConstraintSpec
from .cooldown import ToolCooldownBehavior
from .limit import ToolCallLimitBehavior
from .sequencing import ToolSequencingBehavior

__all__ = [
    "BaseToolBehaviorLayer",
    "ToolConstraintSpec",
    "ToolCallLimitBehavior",
    "ToolCooldownBehavior",
    "ToolSequencingBehavior",
]
