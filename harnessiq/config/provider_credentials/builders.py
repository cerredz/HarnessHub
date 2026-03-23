"""Builder helpers for provider credential objects."""

from __future__ import annotations

from typing import Mapping


def build_dataclass_credential_builder(cls):
    """Create a simple mapping-to-constructor adapter for one credential class."""

    def build(values: Mapping[str, str]) -> object:
        """Construct one credential object from validated string values."""
        return cls(**dict(values))

    return build


__all__ = ["build_dataclass_credential_builder"]
