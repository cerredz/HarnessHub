"""
===============================================================================
File: harnessiq/formalization/stages/__init__.py

What this file does:
- Defines the package-level export surface for `harnessiq/formalization/stages`
  within the HarnessIQ runtime.
- Executable stage-runtime primitives for staged formalization flows.

Use cases:
- Import SimpleStageSpec, STAGE_COMPLETE_TOOL, StageAdvancementError,
  StageAwareToolExecutor, StageLayer, StageCompletionError from one stable
  package entry point.
- Read this module to understand what `harnessiq/formalization/stages` intends
  to expose publicly.

How to use it:
- Import from `harnessiq/formalization/stages` when you want the supported
  facade instead of reaching through deeper internal modules.

Intent:
- Keep the public surface for `harnessiq/formalization/stages` explicit,
  discoverable, and easier to maintain.
===============================================================================
"""

from .context import StageContext
from .exceptions import StageAdvancementError, StageCompletionError
from .executor import StageAwareToolExecutor
from .layer import StageLayer
from .prebuilt import SimpleStageSpec
from .spec import StageSpec
from .tools import STAGE_COMPLETE_TOOL

__all__ = [
    "SimpleStageSpec",
    "STAGE_COMPLETE_TOOL",
    "StageAdvancementError",
    "StageAwareToolExecutor",
    "StageLayer",
    "StageCompletionError",
    "StageContext",
    "StageSpec",
]
