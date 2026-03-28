"""Leads-specific lifecycle runners for CLI command handlers."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

from harnessiq.agents import LeadsAgent
from harnessiq.cli._langsmith import seed_cli_environment
from harnessiq.cli.builders.leads import LeadsCliBuilder
from harnessiq.cli.common import (
    load_factory,
    parse_manifest_parameter_assignments,
    resolve_agent_model,
    split_assignment,
)
from harnessiq.cli.runners.lifecycle import HarnessCliLifecycleRunner
from harnessiq.shared.leads import LEADS_HARNESS_MANIFEST, LeadRunConfig, LeadsMemoryStore, LeadsStorageBackend

_RUN_CONFIG_KEYS = frozenset({"search_summary_every", "search_tail_size", "max_leads_per_icp"})


class LeadsCliRunner:
    """Execute Leads-specific CLI lifecycle actions."""

    def run(
        self,
        *,
        agent_name: str,
        memory_root: str,
        model_factory: str | None,
        model: str | None,
        model_profile: str | None,
        provider_tools_factory: str | None,
        provider_credentials_factories: Sequence[str],
        provider_client_factories: Sequence[str],
        storage_backend_factory: str | None,
        runtime_assignments: Sequence[str],
        max_cycles: int | None,
        approval_policy: str | None,
        allowed_tools: Sequence[str],
        dynamic_tools: bool = False,
        dynamic_tool_candidates: Sequence[str] = (),
        dynamic_tool_top_k: int = 5,
        dynamic_tool_embedding_model: str | None = None,
    ) -> dict[str, Any]:
        builder = LeadsCliBuilder()
        store = builder.load_store(agent_name=agent_name, memory_root=memory_root)
        store.prepare()
        builder.ensure_runtime_parameters_file(store.memory_path)
        seed_cli_environment(Path(memory_root).expanduser())
        self._ensure_configured(store)

        run_config = store.read_run_config()
        overrides = parse_manifest_parameter_assignments(
            runtime_assignments,
            manifest=LEADS_HARNESS_MANIFEST,
            scope="runtime",
        )
        effective_run_config = self._apply_run_config_overrides(run_config, overrides)

        runtime_parameters = builder.read_runtime_parameters(store.memory_path)
        runtime_parameters.update({key: value for key, value in overrides.items() if key not in _RUN_CONFIG_KEYS})

        tools = self._load_tools(provider_tools_factory)
        provider_credentials = {
            family: load_factory(spec)()
            for family, spec in self._parse_factory_assignments(provider_credentials_factories).items()
        }
        provider_clients = {
            family: load_factory(spec)()
            for family, spec in self._parse_factory_assignments(provider_client_factories).items()
        }
        storage_backend = self._load_storage_backend(storage_backend_factory)

        agent = LeadsAgent(
            model=resolve_agent_model(
                model_factory=model_factory,
                model_spec=model,
                profile_name=model_profile,
            ),
            company_background=effective_run_config.company_background,
            icps=effective_run_config.icps,
            platforms=effective_run_config.platforms,
            memory_path=store.memory_path,
            storage_backend=storage_backend,
            tools=tools,
            provider_credentials=provider_credentials or None,
            provider_clients=provider_clients or None,
            max_tokens=int(runtime_parameters.get("max_tokens", 80_000)),
            reset_threshold=float(runtime_parameters.get("reset_threshold", 0.9)),
            prune_search_interval=(
                int(runtime_parameters["prune_search_interval"])
                if runtime_parameters.get("prune_search_interval") is not None
                else None
            ),
            prune_token_limit=(
                int(runtime_parameters["prune_token_limit"])
                if runtime_parameters.get("prune_token_limit") is not None
                else None
            ),
            search_summary_every=effective_run_config.search_summary_every,
            search_tail_size=effective_run_config.search_tail_size,
            max_leads_per_icp=effective_run_config.max_leads_per_icp,
            runtime_config=HarnessCliLifecycleRunner().build_runtime_config(
                sink_specs=(),
                approval_policy=approval_policy,
                allowed_tools=allowed_tools,
                dynamic_tools_enabled=dynamic_tools,
                dynamic_tool_candidates=dynamic_tool_candidates,
                dynamic_tool_top_k=dynamic_tool_top_k,
                dynamic_tool_embedding_model=dynamic_tool_embedding_model,
            ),
        )
        result = agent.run(max_cycles=max_cycles)
        return {
            "agent": agent_name,
            "memory_path": str(store.memory_path.resolve()),
            "result": {
                "cycles_completed": result.cycles_completed,
                "pause_reason": result.pause_reason,
                "resets": result.resets,
                "status": result.status,
            },
            "run_state": store.read_run_state().as_dict() if store.run_state_path.exists() else None,
        }

    def _load_tools(self, factory_spec: str | None) -> tuple[Any, ...] | None:
        if not factory_spec:
            return None
        created_tools = load_factory(factory_spec)()
        if created_tools is None:
            return ()
        if isinstance(created_tools, (str, bytes)):
            raise TypeError("Provider tools factory must return an iterable of tool objects, not a string.")
        return tuple(created_tools)

    def _load_storage_backend(self, factory_spec: str | None):
        if not factory_spec:
            return None
        storage_backend = load_factory(factory_spec)()
        if not isinstance(storage_backend, LeadsStorageBackend):
            raise TypeError(
                "Storage backend factory must return an object that satisfies the LeadsStorageBackend protocol."
            )
        return storage_backend

    def _parse_factory_assignments(self, assignments: Sequence[str]) -> dict[str, str]:
        parsed: dict[str, str] = {}
        for assignment in assignments:
            family, spec = split_assignment(assignment)
            parsed[family.strip().lower()] = spec
        return parsed

    def _apply_run_config_overrides(
        self,
        run_config: LeadRunConfig,
        overrides: dict[str, Any],
    ) -> LeadRunConfig:
        if not overrides:
            return run_config
        payload = run_config.as_dict()
        for key in _RUN_CONFIG_KEYS:
            if key in overrides:
                payload[key] = overrides[key]
        return LeadRunConfig.from_dict(payload)

    def _ensure_configured(self, store: LeadsMemoryStore) -> None:
        if store.run_config_path.exists():
            return
        raise ValueError("Leads configuration not found. Run `harnessiq leads configure` before `harnessiq leads run`.")


__all__ = ["LeadsCliRunner"]
