"""Research Sweep-specific lifecycle runners for CLI command handlers."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

from harnessiq.agents import ResearchSweepAgent
from harnessiq.cli._langsmith import seed_cli_environment
from harnessiq.cli.builders.research_sweep import ResearchSweepCliBuilder
from harnessiq.cli.common import parse_manifest_parameter_assignments, resolve_agent_model, resolve_memory_path, resolve_repo_root, load_factory
from harnessiq.cli.runners.lifecycle import HarnessCliLifecycleRunner
from harnessiq.config import (
    AgentCredentialsNotConfiguredError,
    CredentialsConfigStore,
    HarnessProfile,
    get_provider_credential_spec,
)
from harnessiq.shared.research_sweep import RESEARCH_SWEEP_HARNESS_MANIFEST, ResearchSweepMemoryStore, validate_query_for_run


class ResearchSweepCliRunner:
    """Execute Research Sweep-specific CLI lifecycle actions."""

    def run(
        self,
        *,
        agent_name: str,
        memory_root: str,
        model_factory: str,
        serper_credentials_factory: str | None,
        runtime_assignments: Sequence[str],
        custom_assignments: Sequence[str],
        sink_specs: Sequence[str],
        max_cycles: int | None,
    ) -> dict[str, Any]:
        store = self._load_store(agent_name=agent_name, memory_root=memory_root)
        store.prepare()
        query = validate_query_for_run(store.read_query())
        seed_cli_environment(Path(memory_root).expanduser())

        model = resolve_agent_model(model_factory=model_factory)
        serper_credentials = self._resolve_serper_credentials(
            agent_name=agent_name,
            memory_root=memory_root,
            serper_credentials_factory=serper_credentials_factory,
        )
        runtime_overrides = self.parse_runtime_assignments(runtime_assignments)
        custom_overrides = self.parse_custom_assignments(custom_assignments)
        custom_overrides["query"] = str(custom_overrides.get("query") or query)

        agent = ResearchSweepAgent.from_memory(
            model=model,
            memory_path=store.memory_path,
            serper_credentials=serper_credentials,
            runtime_overrides=runtime_overrides,
            custom_overrides=custom_overrides,
            runtime_config=HarnessCliLifecycleRunner().build_runtime_config(
                sink_specs=sink_specs,
                approval_policy=None,
                allowed_tools=(),
            ),
            instance_name=agent_name,
        )
        result = agent.run(max_cycles=max_cycles)
        payload = ResearchSweepCliBuilder().build_summary(store=store)
        payload.update(
            {
                "agent": agent_name,
                "instance_id": getattr(agent, "instance_id", None),
                "instance_name": getattr(agent, "instance_name", None),
                "ledger_run_id": agent.last_run_id,
                "result": {
                    "cycles_completed": result.cycles_completed,
                    "pause_reason": result.pause_reason,
                    "resets": result.resets,
                    "status": result.status,
                },
            }
        )
        return payload

    def parse_runtime_assignments(self, assignments: Sequence[str]) -> dict[str, Any]:
        return parse_manifest_parameter_assignments(
            assignments,
            manifest=RESEARCH_SWEEP_HARNESS_MANIFEST,
            scope="runtime",
        )

    def parse_custom_assignments(self, assignments: Sequence[str]) -> dict[str, Any]:
        return parse_manifest_parameter_assignments(
            assignments,
            manifest=RESEARCH_SWEEP_HARNESS_MANIFEST,
            scope="custom",
        )

    def _load_store(
        self,
        *,
        agent_name: str,
        memory_root: str,
    ) -> ResearchSweepMemoryStore:
        return ResearchSweepMemoryStore(memory_path=resolve_memory_path(agent_name, memory_root))

    def _resolve_serper_credentials(
        self,
        *,
        agent_name: str,
        memory_root: str,
        serper_credentials_factory: str | None,
    ):
        if serper_credentials_factory:
            return load_factory(serper_credentials_factory)()

        repo_root = resolve_repo_root(memory_root)
        store = CredentialsConfigStore(repo_root=repo_root)
        binding_name = HarnessProfile(
            manifest_id=RESEARCH_SWEEP_HARNESS_MANIFEST.manifest_id,
            agent_name=agent_name,
        ).credential_binding_name
        try:
            binding = store.load().binding_for(binding_name)
        except AgentCredentialsNotConfiguredError as exc:
            raise ValueError(
                "--serper-credentials-factory is required unless you have already bound Serper credentials with "
                "`harnessiq credentials bind research_sweep ...`."
            ) from exc
        resolved = store.resolve_binding(binding)
        family_values = {
            field_name.partition(".")[2]: value
            for field_name, value in resolved.as_dict().items()
            if field_name.startswith("serper.")
        }
        return get_provider_credential_spec("serper").build_credentials(family_values)


__all__ = ["ResearchSweepCliRunner"]
