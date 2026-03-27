"""Shared base classes for platform-first CLI adapters."""

from __future__ import annotations

import argparse
from abc import ABC, abstractmethod
from typing import Any, Generic, Protocol, TypeVar

from harnessiq.agents import AgentModel, AgentRuntimeConfig
from harnessiq.interfaces import PreparedStoreLoader

from .context import HarnessAdapterContext

StoreT = TypeVar("StoreT")


class HarnessCliAdapter(Protocol):
    """Describe the command hooks a platform-first harness adapter must implement."""

    def register_run_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Register any harness-specific CLI flags used only during `run`."""
        ...

    def prepare(self, context: HarnessAdapterContext) -> None:
        """Create or normalize any native harness state before profile resolution."""
        ...

    def load_native_parameters(self, context: HarnessAdapterContext) -> tuple[dict[str, Any], dict[str, Any]]:
        """Read runtime/custom values from the harness-native storage layout."""
        ...

    def synchronize_profile(self, context: HarnessAdapterContext) -> None:
        """Persist resolved generic profile values back into native harness storage."""
        ...

    def show(self, context: HarnessAdapterContext) -> dict[str, Any]:
        """Return a JSON-safe summary of the current harness state."""
        ...

    def run(
        self,
        *,
        args: argparse.Namespace,
        context: HarnessAdapterContext,
        model: AgentModel,
        runtime_config: AgentRuntimeConfig,
    ) -> dict[str, Any]:
        """Execute the harness and return a JSON-safe result payload."""
        ...


class BaseHarnessCliAdapter(ABC):
    """Provide default platform CLI adapter hooks when a harness needs no special logic."""

    def register_run_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Register additional `run` arguments when a harness needs them."""
        del parser

    def prepare(self, context: HarnessAdapterContext) -> None:
        """Prepare native state before the platform profile is resolved."""
        del context

    def load_native_parameters(self, context: HarnessAdapterContext) -> tuple[dict[str, Any], dict[str, Any]]:
        """Load native runtime/custom values when a harness persists them itself."""
        del context
        return {}, {}

    def synchronize_profile(self, context: HarnessAdapterContext) -> None:
        """Write resolved profile values back into native storage when needed."""
        del context

    def show(self, context: HarnessAdapterContext) -> dict[str, Any]:
        """Summarize native state for `prepare`, `show`, or `run` responses."""
        del context
        return {}

    @abstractmethod
    def run(
        self,
        *,
        args: argparse.Namespace,
        context: HarnessAdapterContext,
        model: AgentModel,
        runtime_config: AgentRuntimeConfig,
    ) -> dict[str, Any]:
        """Execute the harness and return any adapter-specific response fields."""


class StoreBackedHarnessCliAdapter(BaseHarnessCliAdapter, Generic[StoreT], ABC):
    """Factor common prepare/load/sync logic for adapters backed by memory-store objects."""

    store_loader: PreparedStoreLoader[StoreT]

    def load_store(self, context: HarnessAdapterContext) -> StoreT:
        """Build and prepare the harness-native memory store for one adapter action."""
        return self.store_loader(context.memory_path)

    def prepare(self, context: HarnessAdapterContext) -> None:
        """Ensure the underlying native store exists before profile resolution."""
        self.load_store(context)

    def load_native_parameters(self, context: HarnessAdapterContext) -> tuple[dict[str, Any], dict[str, Any]]:
        """Read native runtime/custom values from the prepared store."""
        store = self.load_store(context)
        return (
            self.read_native_runtime_parameters(store, context),
            self.read_native_custom_parameters(store, context),
        )

    def synchronize_profile(self, context: HarnessAdapterContext) -> None:
        """Push resolved generic profile values into the native store when required."""
        store = self.load_store(context)
        self.write_runtime_parameters(store, context)
        self.write_custom_parameters(store, context)

    def read_native_runtime_parameters(self, store: StoreT, context: HarnessAdapterContext) -> dict[str, Any]:
        """Read native runtime values when a harness stores them outside the generic profile."""
        del store, context
        return {}

    def read_native_custom_parameters(self, store: StoreT, context: HarnessAdapterContext) -> dict[str, Any]:
        """Read native custom values when a harness stores them outside the generic profile."""
        del store, context
        return {}

    def write_runtime_parameters(self, store: StoreT, context: HarnessAdapterContext) -> None:
        """Persist resolved runtime values when the harness expects them natively."""
        del store, context

    def write_custom_parameters(self, store: StoreT, context: HarnessAdapterContext) -> None:
        """Persist resolved custom values when the harness expects them natively."""
        del store, context


__all__ = [
    "BaseHarnessCliAdapter",
    "HarnessCliAdapter",
    "StoreBackedHarnessCliAdapter",
]
