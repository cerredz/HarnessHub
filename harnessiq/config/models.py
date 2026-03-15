"""Base credential-config type for Harnessiq provider credential models."""

from __future__ import annotations

from typing import TypedDict


class ProviderCredentialConfig(TypedDict, total=False):
    """Base type for per-provider credential configuration.

    Concrete per-provider credential TypedDicts extend this base in their
    respective provider packages or in ``harnessiq/shared/credentials.py``.
    Concrete subclasses should declare all required fields explicitly and
    typically use ``total=True`` to enforce that all keys are present at
    construction time.
    """

    provider: str


__all__ = ["ProviderCredentialConfig"]
