"""
===============================================================================
File: harnessiq/lib/memory/__init__.py

What this file does:
- Defines the package-level export surface for `harnessiq/lib/memory`, the
  canonical memory path abstraction layer within the HarnessIQ SDK.

Use cases:
- Import `MemoryPathInput` as the universal typed container for memory path
  inputs across CLI commands and SDK functions.

Intent:
- Ensure every function that accepts a memory path receives a validated,
  resolved Path rather than a raw string with undefined semantics.
===============================================================================
"""

from harnessiq.lib.memory.memory_path import MemoryPathInput

__all__ = ["MemoryPathInput"]
