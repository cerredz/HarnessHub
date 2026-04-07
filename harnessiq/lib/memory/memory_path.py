"""
===============================================================================
File: harnessiq/lib/memory/memory_path.py

What this file does:
- Provides `MemoryPathInput`, the canonical validated input type for memory
  path arguments across all HarnessIQ SDK functions and CLI surfaces.
- Centralizes every validation failure mode that can arise from accepting a
  raw string as a memory path so that no caller needs to re-implement these
  checks.

Use cases:
- Replace `memory_path: str | None` parameters in SDK functions and CLI
  commands with `memory_path: MemoryPathInput | None`.
- Construct once at the entry point (e.g. in a CLI handler), then pass the
  validated object downstream without re-validating.

How to use it:
- `MemoryPathInput("path/to/memory")` — validates and resolves the path.
- `MemoryPathInput.from_str(raw)` — returns `None` when `raw` is `None`,
  otherwise constructs and validates.
- `.path` — the resolved, absolute `pathlib.Path` for downstream use.

Intent:
- Eliminate an entire class of subtle runtime failures caused by passing
  invalid, empty, or non-directory strings as memory paths into agent
  constructors and file-backed stores.
===============================================================================
"""

from __future__ import annotations

from pathlib import Path


class MemoryPathInput:
    """Validated, canonical memory path input for HarnessIQ SDK functions.

    Accepts a raw string representing a filesystem path that will be used as
    an agent memory directory.  Validates all known failure modes on
    construction so that downstream code receives a clean, resolved ``Path``
    with no ambiguity.

    Raises:
        TypeError:  When the raw input is not a ``str``.
        ValueError: When the string is empty or whitespace-only, contains null
                    bytes, cannot be parsed as a filesystem path, or points to
                    an existing entry that is not a directory.
    """

    def __init__(self, raw: str) -> None:
        if not isinstance(raw, str):
            raise TypeError(
                f"memory_path must be a str, got {type(raw).__name__!r}"
            )
        stripped = raw.strip()
        if not stripped:
            raise ValueError(
                "memory_path must not be empty or consist only of whitespace"
            )
        if "\x00" in raw:
            raise ValueError("memory_path must not contain null bytes")
        try:
            resolved = Path(stripped).resolve()
        except (ValueError, OSError) as exc:
            raise ValueError(
                f"memory_path {raw!r} is not a valid filesystem path: {exc}"
            ) from exc
        if resolved.exists() and not resolved.is_dir():
            raise ValueError(
                f"memory_path {raw!r} resolves to an existing path that is not a"
                " directory; a memory path must point to a directory"
            )
        self._path = resolved

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    @property
    def path(self) -> Path:
        """Return the resolved, absolute ``Path`` for this memory location."""
        return self._path

    @classmethod
    def from_str(cls, raw: str | None) -> MemoryPathInput | None:
        """Return a validated ``MemoryPathInput`` or ``None`` when *raw* is ``None``.

        Use this factory at boundaries where an optional memory path string
        arrives (e.g. from CLI arguments) so that the rest of the call chain
        works with typed objects rather than raw strings.
        """
        if raw is None:
            return None
        return cls(raw)

    # ------------------------------------------------------------------
    # Dunder helpers
    # ------------------------------------------------------------------

    def __str__(self) -> str:
        return str(self._path)

    def __repr__(self) -> str:
        return f"MemoryPathInput({str(self._path)!r})"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, MemoryPathInput):
            return self._path == other._path
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self._path)


__all__ = ["MemoryPathInput"]
