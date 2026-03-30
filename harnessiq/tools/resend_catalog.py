"""
===============================================================================
File: harnessiq/tools/resend_catalog.py

What this file does:
- Implements focused support logic for `harnessiq/tools`.
- Resend operation catalog helpers for tool construction.

Use cases:
- Import this module when sibling runtime code needs the behavior it
  centralizes.

How to use it:
- Use `select_resend_operations` and the other exported symbols here through
  their package-level integration points.

Intent:
- Keep related runtime behavior centralized and easier to discover during
  maintenance.
===============================================================================
"""

from __future__ import annotations

from collections import OrderedDict
from typing import Sequence

from harnessiq.shared.resend import (
    ResendOperation,
    _BATCH_VALIDATION_MODES,
    build_resend_operation_catalog,
    get_resend_operation,
)


def select_resend_operations(allowed_operations: Sequence[str] | None) -> tuple[ResendOperation, ...]:
    """Return the selected Resend operations in stable order without duplicates."""
    if allowed_operations is None:
        return build_resend_operation_catalog()
    selected: list[ResendOperation] = []
    seen: set[str] = set()
    for operation_name in allowed_operations:
        operation = get_resend_operation(operation_name)
        if operation.name in seen:
            continue
        seen.add(operation.name)
        selected.append(operation)
    return tuple(selected)


def build_resend_tool_description(operations: Sequence[ResendOperation]) -> str:
    """Render the user-facing Resend tool description from the catalog."""
    grouped: OrderedDict[str, list[str]] = OrderedDict()
    for operation in operations:
        grouped.setdefault(operation.category, []).append(operation.summary())

    lines = ["Execute authenticated Resend API operations through a single MCP-style request tool."]
    for category, summaries in grouped.items():
        lines.append(f"{category}: {', '.join(summaries)}")
    lines.append(
        "Use `path_params` for URL ids, `query` for list pagination/filtering, `payload` for JSON bodies, "
        "`idempotency_key` for supported send operations, and `batch_validation` for batch sends."
    )
    return "\n".join(lines)


__all__ = [
    "ResendOperation",
    "_BATCH_VALIDATION_MODES",
    "build_resend_operation_catalog",
    "build_resend_tool_description",
    "get_resend_operation",
    "select_resend_operations",
]
