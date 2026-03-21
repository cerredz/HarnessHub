"""Compatibility facade for the Harnessiq toolset catalog surface."""

from __future__ import annotations

from .catalog_builtin import BUILTIN_FAMILY_FACTORIES, BuiltinFactory
from .catalog_provider import (
    PROVIDER_ENTRIES,
    PROVIDER_ENTRY_INDEX,
    PROVIDER_FACTORY_MAP,
    ToolEntry,
)

ToolEntry.__module__ = __name__

__all__ = [
    "BUILTIN_FAMILY_FACTORIES",
    "BuiltinFactory",
    "PROVIDER_ENTRIES",
    "PROVIDER_ENTRY_INDEX",
    "PROVIDER_FACTORY_MAP",
    "ToolEntry",
]
