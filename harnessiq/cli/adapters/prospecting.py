"""Prospecting platform CLI adapter."""

from __future__ import annotations

import argparse

from harnessiq.agents import AgentModel, AgentRuntimeConfig, GoogleMapsProspectingAgent
from harnessiq.shared.prospecting import ProspectingMemoryStore

from .base import StoreBackedHarnessCliAdapter
from .context import HarnessAdapterContext
from .utils import (
    load_optional_iterable_factory,
    load_prospecting_store,
    result_payload,
    set_env_path_if_missing,
)

_DEFAULT_PROSPECTING_BROWSER_TOOLS_FACTORY = "harnessiq.integrations.google_maps_playwright:create_browser_tools"


class ProspectingHarnessCliAdapter(StoreBackedHarnessCliAdapter[ProspectingMemoryStore]):
    """Adapt the prospecting harness memory layout to the platform-first CLI."""

    store_loader = staticmethod(load_prospecting_store)

    def register_run_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--browser-tools-factory",
            default=_DEFAULT_PROSPECTING_BROWSER_TOOLS_FACTORY,
            help=(
                "Import path (module:callable) that returns browser tools. "
                f"Defaults to {_DEFAULT_PROSPECTING_BROWSER_TOOLS_FACTORY}."
            ),
        )

    def read_native_runtime_parameters(
        self,
        store: ProspectingMemoryStore,
        context: HarnessAdapterContext,
    ) -> dict[str, object]:
        del context
        return store.read_runtime_parameters()

    def read_native_custom_parameters(
        self,
        store: ProspectingMemoryStore,
        context: HarnessAdapterContext,
    ) -> dict[str, object]:
        del context
        return store.read_custom_parameters()

    def write_runtime_parameters(self, store: ProspectingMemoryStore, context: HarnessAdapterContext) -> None:
        store.write_runtime_parameters(context.profile.runtime_parameters)

    def write_custom_parameters(self, store: ProspectingMemoryStore, context: HarnessAdapterContext) -> None:
        store.write_custom_parameters(context.profile.custom_parameters)

    def show(self, context: HarnessAdapterContext) -> dict[str, object]:
        store = self.load_store(context)
        state = store.read_state()
        qualified_leads = store.read_qualified_leads()
        return {
            "additional_prompt": store.read_additional_prompt(),
            "agent_identity": store.read_agent_identity(),
            "company_description": store.read_company_description(),
            "custom_parameters": store.read_custom_parameters(),
            "qualified_lead_count": len(qualified_leads),
            "recent_qualified_leads": [record.as_dict() for record in qualified_leads[-5:]],
            "run_state": state.as_dict(),
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
        set_env_path_if_missing("HARNESSIQ_PROSPECTING_SESSION_DIR", store.browser_data_dir)
        browser_tools = load_optional_iterable_factory(args.browser_tools_factory)
        agent = GoogleMapsProspectingAgent.from_memory(
            model=model,
            memory_path=context.memory_path,
            browser_tools=browser_tools,
            runtime_overrides=context.runtime_parameters,
            custom_overrides=context.custom_parameters,
            runtime_config=runtime_config,
        )
        result = agent.run(max_cycles=args.max_cycles)
        payload = self.show(context)
        payload.update(
            {
                "ledger_run_id": agent.last_run_id,
                "result": result_payload(result),
            }
        )
        return payload


__all__ = ["ProspectingHarnessCliAdapter"]
