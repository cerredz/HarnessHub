"""Mission-driven platform CLI adapter."""

from __future__ import annotations

import argparse

from harnessiq.agents import AgentModel, AgentRuntimeConfig, MissionDrivenAgent
from harnessiq.shared.mission_driven import MissionDrivenMemoryStore

from .base import StoreBackedHarnessCliAdapter
from .context import HarnessAdapterContext
from .utils import load_mission_driven_store, result_payload


class MissionDrivenHarnessCliAdapter(StoreBackedHarnessCliAdapter[MissionDrivenMemoryStore]):
    """Adapt the mission-driven harness memory layout to the platform-first CLI."""

    store_loader = staticmethod(load_mission_driven_store)

    def read_native_runtime_parameters(
        self,
        store: MissionDrivenMemoryStore,
        context: HarnessAdapterContext,
    ) -> dict[str, object]:
        del context
        return store.read_runtime_parameters()

    def read_native_custom_parameters(
        self,
        store: MissionDrivenMemoryStore,
        context: HarnessAdapterContext,
    ) -> dict[str, object]:
        del context
        return store.read_custom_parameters()

    def write_runtime_parameters(self, store: MissionDrivenMemoryStore, context: HarnessAdapterContext) -> None:
        store.write_runtime_parameters(context.profile.runtime_parameters)

    def write_custom_parameters(self, store: MissionDrivenMemoryStore, context: HarnessAdapterContext) -> None:
        store.write_custom_parameters(context.profile.custom_parameters)

    def show(self, context: HarnessAdapterContext) -> dict[str, object]:
        store = self.load_store(context)
        return {
            "mission": store.read_mission(),
            "task_plan": store.read_task_plan().to_dict(),
            "snapshot": store.build_state_snapshot(),
            "readme": store.read_readme(),
        }

    def run(
        self,
        *,
        args: argparse.Namespace,
        context: HarnessAdapterContext,
        model: AgentModel,
        runtime_config: AgentRuntimeConfig,
    ) -> dict[str, object]:
        agent = MissionDrivenAgent.from_memory(
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


__all__ = ["MissionDrivenHarnessCliAdapter"]
