"""Base credential configuration types for the Harnessiq config layer."""

from __future__ import annotations

from typing import TypedDict


class ProviderCredentialConfig(TypedDict, total=False):
    """Base type for per-provider credential configuration.

    Concrete per-provider credential TypedDicts extend this base in their
    respective provider packages (e.g. ``harnessiq/providers/snovio/credentials.py``).
    """


__all__ = ["ProviderCredentialConfig"]
