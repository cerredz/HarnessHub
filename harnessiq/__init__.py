"""Harnessiq SDK package."""

from __future__ import annotations

from importlib import import_module
from typing import Any

__version__ = "0.1.0"
_EXPORTED_MODULES = frozenset({"agents", "providers", "tools"})


def __getattr__(name: str) -> Any:
    if name in _EXPORTED_MODULES:
        module = import_module(f"{__name__}.{name}")
        globals()[name] = module
        return module
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


def __dir__() -> list[str]:
    return sorted([*globals(), *_EXPORTED_MODULES])


__all__ = ["__version__", *_EXPORTED_MODULES]
