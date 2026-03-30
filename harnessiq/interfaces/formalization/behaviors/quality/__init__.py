"""
===============================================================================
File: harnessiq/interfaces/formalization/behaviors/quality/__init__.py

What this file does:
- Defines the package-level export surface for
  `harnessiq/interfaces/formalization/behaviors/quality` within the HarnessIQ
  runtime.
- Quality-behavior formalization layers.

Use cases:
- Import BaseQualityBehaviorLayer, QualityCriterionSpec,
  CitationRequirementBehavior, QualityGateBehavior, ScopeEnforcementBehavior
  from one stable package entry point.
- Read this module to understand what
  `harnessiq/interfaces/formalization/behaviors/quality` intends to expose
  publicly.

How to use it:
- Import from `harnessiq/interfaces/formalization/behaviors/quality` when you
  want the supported facade instead of reaching through deeper internal
  modules.

Intent:
- Keep the public surface for
  `harnessiq/interfaces/formalization/behaviors/quality` explicit,
  discoverable, and easier to maintain.
===============================================================================
"""

from .base import BaseQualityBehaviorLayer, QualityCriterionSpec
from .citation import CitationRequirementBehavior
from .gate import QualityGateBehavior
from .scope import ScopeEnforcementBehavior

__all__ = [
    "BaseQualityBehaviorLayer",
    "QualityCriterionSpec",
    "CitationRequirementBehavior",
    "QualityGateBehavior",
    "ScopeEnforcementBehavior",
]
