"""Secret-redaction helpers for provider credential metadata."""

from __future__ import annotations


def mask_secret(value: str) -> str:
    """Redact one secret string while preserving enough shape for debugging output."""
    stripped = value.strip()
    if len(stripped) <= 4:
        return "*" * len(stripped)
    return f"{stripped[:2]}{'*' * max(1, len(stripped) - 4)}{stripped[-2:]}"


__all__ = ["mask_secret"]
