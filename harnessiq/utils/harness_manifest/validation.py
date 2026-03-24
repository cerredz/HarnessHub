"""Validation helpers for harness manifest declarations."""

from __future__ import annotations

from typing import Any


def validate_unique_keys(items: tuple[Any, ...], *, label: str) -> None:
    """Reject duplicate `key` attributes so manifest declarations stay deterministic."""
    seen: set[str] = set()
    for item in items:
        key = getattr(item, "key", "").strip()
        if key in seen:
            raise ValueError(f"Duplicate {label} key '{key}'.")
        seen.add(key)


__all__ = ["validate_unique_keys"]
