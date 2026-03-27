"""LinkedIn platform CLI adapter."""

from __future__ import annotations

import argparse

from harnessiq.agents import AgentModel, AgentRuntimeConfig, LinkedInJobApplierAgent
from harnessiq.shared.dtos import HarnessAdapterResponseDTO, HarnessStatePayloadDTO
from harnessiq.shared.linkedin import LinkedInMemoryStore

from .base import StoreBackedHarnessCliAdapter
from .context import HarnessAdapterContext
from .utils import (
    load_linkedin_store,
    load_optional_iterable_factory,
    optional_string,
    result_payload,
    set_env_path_if_missing,
)


class LinkedInHarnessCliAdapter(StoreBackedHarnessCliAdapter[LinkedInMemoryStore]):
    """Adapt the LinkedIn harness memory layout to the platform-first CLI."""

    store_loader = staticmethod(load_linkedin_store)

    def register_run_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--browser-tools-factory",
            help="Optional import path (module:callable) that returns LinkedIn browser tools.",
        )

    def read_native_runtime_parameters(
        self,
        store: LinkedInMemoryStore,
        context: HarnessAdapterContext,
    ) -> dict[str, object]:
        del context
        return store.read_runtime_parameters()

    def read_native_custom_parameters(
        self,
        store: LinkedInMemoryStore,
        context: HarnessAdapterContext,
    ) -> dict[str, object]:
        del context
        return store.read_custom_parameters()

    def write_runtime_parameters(self, store: LinkedInMemoryStore, context: HarnessAdapterContext) -> None:
        store.write_runtime_parameters(context.profile.runtime_parameters)

    def write_custom_parameters(self, store: LinkedInMemoryStore, context: HarnessAdapterContext) -> None:
        store.write_custom_parameters(context.profile.custom_parameters)

    def show(self, context: HarnessAdapterContext) -> HarnessStatePayloadDTO:
        store = self.load_store(context)
        return HarnessStatePayloadDTO(
            {
            "additional_prompt": store.read_additional_prompt(),
            "agent_identity": store.read_agent_identity(),
            "custom_parameters": store.read_custom_parameters(),
            "job_preferences": store.read_job_preferences(),
            "managed_files": [record.as_dict() for record in store.read_managed_files()],
            "runtime_parameters": store.read_runtime_parameters(),
            "user_profile": store.read_user_profile(),
            }
        )

    def run(
        self,
        *,
        args: argparse.Namespace,
        context: HarnessAdapterContext,
        model: AgentModel,
        runtime_config: AgentRuntimeConfig,
    ) -> HarnessAdapterResponseDTO:
        store = self.load_store(context)
        set_env_path_if_missing(
            "HARNESSIQ_BROWSER_SESSION_DIR",
            store.memory_path / "browser-data",
            require_existing=True,
        )
        browser_tools = load_optional_iterable_factory(args.browser_tools_factory)
        agent = LinkedInJobApplierAgent.from_memory(
            model=model,
            memory_path=context.memory_path,
            browser_tools=browser_tools,
            runtime_overrides=context.runtime_parameters,
            runtime_config=runtime_config,
        )
        result = agent.run(max_cycles=args.max_cycles)
        return HarnessAdapterResponseDTO(
            result=result_payload(result),
            extra={
                "applied_jobs_file": str(store.applied_jobs_path.resolve()),
                "instance_id": optional_string(getattr(agent, "instance_id", None)),
                "instance_name": optional_string(getattr(agent, "instance_name", None)),
                "ledger_run_id": agent.last_run_id,
            },
        )


__all__ = ["LinkedInHarnessCliAdapter"]
