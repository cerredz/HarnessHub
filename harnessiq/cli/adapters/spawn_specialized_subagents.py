"""Spawn-specialized-subagents platform CLI adapter."""

from __future__ import annotations

import argparse

from harnessiq.agents import AgentModel, AgentRuntimeConfig, SpawnSpecializedSubagentsAgent
from harnessiq.shared.spawn_specialized_subagents import SpawnSpecializedSubagentsMemoryStore

from .base import StoreBackedHarnessCliAdapter
from .context import HarnessAdapterContext
from .utils import load_spawn_specialized_subagents_store, result_payload


class SpawnSpecializedSubagentsHarnessCliAdapter(
    StoreBackedHarnessCliAdapter[SpawnSpecializedSubagentsMemoryStore]
):
    """Adapt the spawn-specialized-subagents harness memory layout to the platform-first CLI."""

    store_loader = staticmethod(load_spawn_specialized_subagents_store)

    def read_native_runtime_parameters(
        self,
        store: SpawnSpecializedSubagentsMemoryStore,
        context: HarnessAdapterContext,
    ) -> dict[str, object]:
        del context
        return store.read_runtime_parameters()

    def read_native_custom_parameters(
        self,
        store: SpawnSpecializedSubagentsMemoryStore,
        context: HarnessAdapterContext,
    ) -> dict[str, object]:
        del context
        return store.read_custom_parameters()

    def write_runtime_parameters(
        self,
        store: SpawnSpecializedSubagentsMemoryStore,
        context: HarnessAdapterContext,
    ) -> None:
        store.write_runtime_parameters(context.profile.runtime_parameters)

    def write_custom_parameters(
        self,
        store: SpawnSpecializedSubagentsMemoryStore,
        context: HarnessAdapterContext,
    ) -> None:
        store.write_custom_parameters(context.profile.custom_parameters)

    def show(self, context: HarnessAdapterContext) -> dict[str, object]:
        store = self.load_store(context)
        return {
            "plan": store.read_plan(),
            "worker_outputs": store.read_worker_outputs(),
            "integration_summary": store.read_integration_summary(),
            "snapshot": store.build_state_snapshot(),
        }

    def run(
        self,
        *,
        args: argparse.Namespace,
        context: HarnessAdapterContext,
        model: AgentModel,
        runtime_config: AgentRuntimeConfig,
    ) -> dict[str, object]:
        agent = SpawnSpecializedSubagentsAgent.from_memory(
            model=model,
            memory_path=context.memory_path,
            runtime_overrides=context.runtime_parameters,
            custom_overrides=context.custom_parameters,
            runtime_config=runtime_config,
            instance_name=context.agent_name,
        )
        result = agent.run(max_cycles=args.max_cycles)
        payload = self.show(context)
        payload.update(
            {
                "instance_id": getattr(agent, "instance_id", None),
                "instance_name": getattr(agent, "instance_name", None),
                "ledger_run_id": agent.last_run_id,
                "result": result_payload(result),
            }
        )
        return payload


__all__ = ["SpawnSpecializedSubagentsHarnessCliAdapter"]
