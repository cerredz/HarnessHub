"""
===============================================================================
File: harnessiq/formalization/criteria/exceptions.py

What this file does:
- Defines exception types for the stop criteria formalization module.

Intent:
- Keep exception definitions isolated from the rest of the criteria module
  so they can be imported without pulling in the full dependency tree.
===============================================================================
"""

from __future__ import annotations


class CriterionError(Exception):
    """Raised when a stop criterion encounters a configuration or evaluation error."""
