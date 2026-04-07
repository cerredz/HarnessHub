"""
===============================================================================
File: harnessiq/lib/__init__.py

What this file does:
- Defines the package-level export surface for `harnessiq/lib`, the canonical
  logic library within the HarnessIQ SDK.
- This package is the authoritative home for well-typed input abstractions and
  reusable canonical utilities shared across the SDK and CLI surfaces.

Use cases:
- Import validated input types from subpackages (e.g. `harnessiq.lib.memory`)
  instead of working with raw primitives that carry implicit validation
  expectations.

Intent:
- Centralize canonical logic so every entry point in the codebase applies the
  same validation rules rather than re-implementing them inline.
===============================================================================
"""
