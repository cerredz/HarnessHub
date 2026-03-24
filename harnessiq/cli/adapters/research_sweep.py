"""Research sweep platform CLI adapter."""

from __future__ import annotations

import argparse

from harnessiq.agents import AgentModel, AgentRuntimeConfig, ResearchSweepAgent
from harnessiq.shared.research_sweep import ResearchSweepMemoryStore, validate_query_for_run

from .base import StoreBackedHarnessCliAdapter
from .context import HarnessAdapterContext
from .utils import load_research_sweep_store, result_payload


class ResearchSweepHarnessCliAdapter(StoreBackedHarnessCliAdapter[ResearchSweepMemoryStore]):
    """Adapt the research sweep harness memory layout to the platform-first CLI."""

    store_loader = staticmethod(load_research_sweep_store)

    def read_native_runtime_parameters(
        self,
        store: ResearchSweepMemoryStore,
        context: HarnessAdapterContext,
    ) -> dict[str, object]:
        del context
        return store.read_runtime_parameters()

    def read_native_custom_parameters(
        self,
        store: ResearchSweepMemoryStore,
        context: HarnessAdapterContext,
    ) -> dict[str, object]:
        del context
        payload = store.read_custom_parameters()
        query = store.read_query()
        if query:
            payload["query"] = query
        return payload

    def write_runtime_parameters(self, store: ResearchSweepMemoryStore, context: HarnessAdapterContext) -> None:
        store.write_runtime_parameters(context.profile.runtime_parameters)

    def write_custom_parameters(self, store: ResearchSweepMemoryStore, context: HarnessAdapterContext) -> None:
        payload = dict(context.profile.custom_parameters)
        if "query" in payload:
            store.write_query(str(payload["query"]))
        store.write_custom_parameters(payload)

    def show(self, context: HarnessAdapterContext) -> dict[str, object]:
        store = self.load_store(context)
        return {
            "additional_prompt": store.read_additional_prompt(),
            "custom_parameters": store.read_custom_parameters(),
            "final_report": store.read_final_report(),
            "query": store.read_query(),
            "research_memory": store.read_research_memory(),
            "research_memory_summary": store.read_research_memory_summary(),
            "runtime_parameters": store.read_runtime_parameters(),
        }

    def run(
        self,
        *,
        args: argparse.Namespace,
        context: HarnessAdapterContext,
        model: AgentModel,
        runtime_config: AgentRuntimeConfig,
    ) -> dict[str, object]:
        store = self.load_store(context)
        serper_credentials = context.bound_credentials.get("serper")
        if serper_credentials is None:
            raise ValueError(
                "Research Sweep requires a 'serper' credential binding. "
                "Use `harnessiq credentials bind research_sweep ...` first."
            )
        query = validate_query_for_run(store.read_query())
        agent = ResearchSweepAgent.from_memory(
            model=model,
            memory_path=context.memory_path,
            serper_credentials=serper_credentials,
            runtime_overrides=context.runtime_parameters,
            custom_overrides={**context.custom_parameters, "query": query},
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


__all__ = ["ResearchSweepHarnessCliAdapter"]
