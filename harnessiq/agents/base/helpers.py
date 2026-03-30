"""
===============================================================================
File: harnessiq/agents/base/helpers.py

What this file does:
- Collects shared helper functions for the `base` package.
- Compatibility wrapper for base-agent helper utilities.

Use cases:
- Use these helpers when sibling runtime modules need the same normalization,
  path resolution, or payload-shaping logic.

How to use it:
- Import the narrow helper you need from `harnessiq/agents/base` rather than
  duplicating package-specific support code.

Intent:
- Keep reusable `base` support logic centralized so business modules stay
  focused on orchestration.
===============================================================================
"""

from .agent_helpers import BaseAgentHelpersMixin, _resolve_repo_root, _utcnow

__all__ = ["BaseAgentHelpersMixin", "_resolve_repo_root", "_utcnow"]
