"""Exa Outreach platform CLI adapter."""

from __future__ import annotations

import argparse
from typing import Any

from harnessiq.agents import AgentModel, AgentRuntimeConfig, ExaOutreachAgent
from harnessiq.cli.common import load_factory
from harnessiq.shared.exa_outreach import EmailTemplate, ExaOutreachMemoryStore

from .base import StoreBackedHarnessCliAdapter
from .context import HarnessAdapterContext
from .utils import load_exa_store, optional_string, result_payload


class ExaOutreachHarnessCliAdapter(StoreBackedHarnessCliAdapter[ExaOutreachMemoryStore]):
    """Adapt the Exa Outreach harness memory layout to the platform-first CLI."""

    store_loader = staticmethod(load_exa_store)

    def register_run_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--email-data-factory",
            help="Import path (module:callable) that returns a list of email template dicts.",
        )
        parser.add_argument(
            "--search-only",
            action="store_true",
            default=False,
            help="Discover and log leads only; skip email sending.",
        )

    def read_native_runtime_parameters(
        self,
        store: ExaOutreachMemoryStore,
        context: HarnessAdapterContext,
    ) -> dict[str, Any]:
        query_config = store.read_query_config()
        return {
            key: value
            for key, value in query_config.items()
            if key in set(context.manifest.runtime_parameter_names)
        }

    def write_runtime_parameters(self, store: ExaOutreachMemoryStore, context: HarnessAdapterContext) -> None:
        query_config = store.read_query_config()
        for key, value in context.profile.runtime_parameters.items():
            query_config[key] = value
        store.write_query_config(query_config)

    def show(self, context: HarnessAdapterContext) -> dict[str, object]:
        store = self.load_store(context)
        return {
            "additional_prompt": store.read_additional_prompt(),
            "agent_identity": store.read_agent_identity(),
            "query_config": store.read_query_config(),
            "run_files": [path.name for path in store.list_run_files()],
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
        search_only = bool(args.search_only)
        exa_credentials = context.bound_credentials.get("exa")
        if exa_credentials is None:
            raise ValueError("Exa Outreach requires an 'exa' credential binding. Use `harnessiq credentials bind` first.")
        resend_credentials = context.bound_credentials.get("resend")
        if not search_only and resend_credentials is None:
            raise ValueError(
                "Exa Outreach email mode requires a 'resend' credential binding. Use `harnessiq credentials bind` first."
            )
        email_data: list[EmailTemplate] = []
        if not search_only:
            if not args.email_data_factory:
                raise ValueError("--email-data-factory is required unless --search-only is set.")
            raw_email_data = load_factory(args.email_data_factory)()
            if not isinstance(raw_email_data, list):
                raise TypeError("Email data factory must return a list of template dictionaries.")
            email_data = [EmailTemplate.from_dict(dict(payload)) for payload in raw_email_data]

        query_config = store.read_query_config()
        search_query = str(query_config.get("search_query", "")).strip()
        agent = ExaOutreachAgent(
            model=model,
            exa_credentials=exa_credentials,
            resend_credentials=resend_credentials,
            email_data=email_data,
            search_only=search_only,
            search_query=search_query,
            memory_path=context.memory_path,
            max_tokens=int(context.runtime_parameters["max_tokens"]),
            reset_threshold=float(context.runtime_parameters["reset_threshold"]),
            runtime_config=runtime_config,
        )
        result = agent.run(max_cycles=args.max_cycles)
        run_id = agent._current_run_id or "unknown"
        return {
            "instance_id": optional_string(getattr(agent, "instance_id", None)),
            "instance_name": optional_string(getattr(agent, "instance_name", None)),
            "ledger_run_id": optional_string(getattr(agent, "last_run_id", None)),
            "result": result_payload(result),
            "run_id": str(run_id),
            "state": self.show(context),
        }


__all__ = ["ExaOutreachHarnessCliAdapter"]
