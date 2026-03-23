"""Factory-loading helpers shared by platform CLI adapters."""

from __future__ import annotations

from typing import Any

from harnessiq.cli.common import load_factory, split_assignment


def load_optional_iterable_factory(spec: str | None) -> tuple[Any, ...]:
    """Build an optional iterable-returning factory and normalize empty results to a tuple."""
    if not spec:
        return ()
    created = load_factory(spec)()
    if created is None:
        return ()
    if isinstance(created, (str, bytes)):
        raise TypeError("Factory must return an iterable of tool objects, not a string.")
    return tuple(created)


def load_factory_assignment_map(assignments: list[str]) -> dict[str, Any]:
    """Resolve repeated `FAMILY=MODULE:CALLABLE` assignments into constructed objects."""
    resolved: dict[str, Any] = {}
    for assignment in assignments:
        family, spec = split_assignment(assignment)
        resolved[family.strip().lower()] = load_factory(spec)()
    return resolved


__all__ = [
    "load_factory_assignment_map",
    "load_optional_iterable_factory",
]
