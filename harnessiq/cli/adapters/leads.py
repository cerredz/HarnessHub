"""Leads platform CLI adapter."""

from __future__ import annotations

import argparse
from typing import Any

from harnessiq.agents import AgentModel, AgentRuntimeConfig, LeadsAgent
from harnessiq.cli.common import load_factory
from harnessiq.shared.dtos import HarnessAdapterResponseDTO, HarnessStatePayloadDTO
from harnessiq.shared.leads import (
    LeadsMemoryStore,
    RUNTIME_PARAMETERS_FILENAME as LEADS_RUNTIME_PARAMETERS_FILENAME,
)

from .base import StoreBackedHarnessCliAdapter
from .context import HarnessAdapterContext
from .utils import (
    load_factory_assignment_map,
    load_leads_store,
    load_optional_iterable_factory,
    read_json_object,
    result_payload,
)


class LeadsHarnessCliAdapter(StoreBackedHarnessCliAdapter[LeadsMemoryStore]):
    """Adapt the leads harness memory layout to the platform-first CLI."""

    store_loader = staticmethod(load_leads_store)

    def register_run_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--provider-tools-factory",
            help="Optional import path (module:callable) that returns additional provider tools.",
        )
        parser.add_argument(
            "--provider-client-factory",
            action="append",
            default=[],
            metavar="FAMILY=MODULE:CALLABLE",
            help="Map a provider family to a prebuilt client factory. May be repeated.",
        )
        parser.add_argument(
            "--storage-backend-factory",
            help="Optional import path (module:callable) that returns a LeadsStorageBackend instance.",
        )

    def read_native_runtime_parameters(
        self,
        store: LeadsMemoryStore,
        context: HarnessAdapterContext,
    ) -> dict[str, Any]:
        del context
        runtime_parameters: dict[str, Any] = {}
        if store.run_config_path.exists():
            run_config = store.read_run_config()
            runtime_parameters.update(
                {
                    "max_leads_per_icp": run_config.max_leads_per_icp,
                    "search_summary_every": run_config.search_summary_every,
                    "search_tail_size": run_config.search_tail_size,
                }
            )
        runtime_parameters.update(read_json_object(store.memory_path / LEADS_RUNTIME_PARAMETERS_FILENAME))
        return runtime_parameters

    def show(self, context: HarnessAdapterContext) -> HarnessStatePayloadDTO:
        store = self.load_store(context)
        return HarnessStatePayloadDTO(
            {
                "icp_states": [state.as_dict() for state in store.list_icp_states()],
                "run_config": store.read_run_config().as_dict() if store.run_config_path.exists() else None,
                "run_state": store.read_run_state().as_dict() if store.run_state_path.exists() else None,
                "runtime_parameters": read_json_object(store.memory_path / LEADS_RUNTIME_PARAMETERS_FILENAME),
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
        if not store.run_config_path.exists():
            raise ValueError(
                "Leads run configuration is missing. Configure company background, ICPs, and platforms first."
            )
        run_config = store.read_run_config()
        provider_tools = load_optional_iterable_factory(args.provider_tools_factory)
        provider_clients = load_factory_assignment_map(args.provider_client_factory)
        storage_backend = load_factory(args.storage_backend_factory)() if args.storage_backend_factory else None
        search_summary_every = int(context.runtime_parameters.get("search_summary_every", run_config.search_summary_every))
        search_tail_size = int(context.runtime_parameters.get("search_tail_size", run_config.search_tail_size))
        max_leads_per_icp = context.runtime_parameters.get("max_leads_per_icp", run_config.max_leads_per_icp)
        agent = LeadsAgent(
            model=model,
            company_background=run_config.company_background,
            icps=run_config.icps,
            platforms=run_config.platforms,
            memory_path=context.memory_path,
            storage_backend=storage_backend,
            max_tokens=int(context.runtime_parameters["max_tokens"]),
            reset_threshold=float(context.runtime_parameters["reset_threshold"]),
            prune_search_interval=(
                int(context.runtime_parameters["prune_search_interval"])
                if context.runtime_parameters.get("prune_search_interval") is not None
                else None
            ),
            prune_token_limit=(
                int(context.runtime_parameters["prune_token_limit"])
                if context.runtime_parameters.get("prune_token_limit") is not None
                else None
            ),
            search_summary_every=search_summary_every,
            search_tail_size=search_tail_size,
            max_leads_per_icp=(int(max_leads_per_icp) if max_leads_per_icp is not None else None),
            provider_credentials=context.bound_credentials or None,
            provider_clients=provider_clients or None,
            tools=provider_tools or None,
            runtime_config=runtime_config,
        )
        result = agent.run(max_cycles=args.max_cycles)
        return HarnessAdapterResponseDTO(
            result=result_payload(result),
            extra={"run_state": store.read_run_state().as_dict() if store.run_state_path.exists() else None},
        )


__all__ = ["LeadsHarnessCliAdapter"]
