"""Interface contracts for CLI loader and factory seams."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any, Protocol, TypeVar, runtime_checkable

StoreT = TypeVar("StoreT")
ResultT = TypeVar("ResultT")


@runtime_checkable
class PreparedStoreLoader(Protocol[StoreT]):
    """Describe callables that build and prepare one harness-native store."""

    def __call__(self, memory_path: Path) -> StoreT:
        """Return the prepared store for one memory path."""


@runtime_checkable
class ZeroArgumentFactory(Protocol[ResultT]):
    """Describe zero-argument factory callables returned by dynamic loaders."""

    def __call__(self) -> ResultT:
        """Construct one runtime object."""


@runtime_checkable
class IterableFactory(Protocol[ResultT]):
    """Describe zero-argument factories that yield iterable runtime objects."""

    def __call__(self) -> Iterable[ResultT] | None:
        """Construct zero or more runtime objects."""


@runtime_checkable
class FactoryLoader(Protocol):
    """Describe dynamic factory resolvers such as CLI import-string loaders."""

    def __call__(self, spec: str) -> ZeroArgumentFactory[Any]:
        """Resolve one import spec to a zero-argument factory."""


__all__ = [
    "FactoryLoader",
    "IterableFactory",
    "PreparedStoreLoader",
    "ZeroArgumentFactory",
]
