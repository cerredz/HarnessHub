"""
===============================================================================
File: harnessiq/formalization/roles/__init__.py

What this file does:
- Defines the public export surface for harnessiq/formalization/roles.
- Exposes RoleSpec (persona injection spec) and RoleLayer.

Use cases:
- Import from harnessiq.formalization.roles when building agents that need
  an explicit persona injected into the system prompt.

How to use it:
  from harnessiq.formalization.roles import RoleSpec, RoleLayer

Intent:
- Keep the public interface for the roles formalization package narrow and
  explicit.
===============================================================================
"""

from .layer import RoleLayer
from .spec import RolePosition, RoleSpec

__all__ = [
    "RoleLayer",
    "RolePosition",
    "RoleSpec",
]
