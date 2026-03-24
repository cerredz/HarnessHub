"""Instagram platform CLI adapter."""

from __future__ import annotations

import argparse

from harnessiq.agents import AgentModel, AgentRuntimeConfig, InstagramKeywordDiscoveryAgent
from harnessiq.cli.common import load_factory
from harnessiq.shared.instagram import InstagramMemoryStore

from .base import StoreBackedHarnessCliAdapter
from .context import HarnessAdapterContext
from .utils import load_instagram_store, result_payload, set_env_path_if_missing

_DEFAULT_INSTAGRAM_SEARCH_BACKEND_FACTORY = "harnessiq.integrations.instagram_playwright:create_search_backend"


class InstagramHarnessCliAdapter(StoreBackedHarnessCliAdapter[InstagramMemoryStore]):
    """Adapt the Instagram harness memory layout to the platform-first CLI."""

    store_loader = staticmethod(load_instagram_store)

    def register_run_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--search-backend-factory",
            default=_DEFAULT_INSTAGRAM_SEARCH_BACKEND_FACTORY,
            help=(
                "Import path (module:callable) that returns an Instagram search backend. "
                f"Defaults to {_DEFAULT_INSTAGRAM_SEARCH_BACKEND_FACTORY}."
            ),
        )

    def read_native_runtime_parameters(
        self,
        store: InstagramMemoryStore,
        context: HarnessAdapterContext,
    ) -> dict[str, object]:
        del context
        return store.read_runtime_parameters()

    def write_runtime_parameters(self, store: InstagramMemoryStore, context: HarnessAdapterContext) -> None:
        store.write_runtime_parameters(dict(context.profile.runtime_parameters))

    def show(self, context: HarnessAdapterContext) -> dict[str, object]:
        store = self.load_store(context)
        search_history = store.read_search_history()
        lead_database = store.read_lead_database()
        return {
            "additional_prompt": store.read_additional_prompt(),
            "agent_identity": store.read_agent_identity(),
            "email_count": len(lead_database.emails),
            "icp_profiles": store.read_icp_profiles(),
            "lead_count": len(lead_database.leads),
            "recent_searches": [record.as_dict() for record in search_history[-5:]],
            "runtime_parameters": store.read_runtime_parameters(),
            "search_count": len(search_history),
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
        set_env_path_if_missing("HARNESSIQ_INSTAGRAM_SESSION_DIR", store.memory_path / "browser-data")
        search_backend = load_factory(args.search_backend_factory)()
        agent = InstagramKeywordDiscoveryAgent.from_memory(
            model=model,
            search_backend=search_backend,
            memory_path=context.memory_path,
            runtime_overrides=context.runtime_parameters,
            runtime_config=runtime_config,
        )
        result = agent.run(max_cycles=args.max_cycles)
        return {
            "email_count": len(agent.get_emails()),
            "result": result_payload(result),
        }


__all__ = ["InstagramHarnessCliAdapter"]
