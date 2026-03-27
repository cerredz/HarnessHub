"""Exa Outreach-specific lifecycle runners for CLI command handlers."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

from harnessiq.agents.exa_outreach import ExaOutreachAgent
from harnessiq.cli._langsmith import seed_cli_environment
from harnessiq.cli.common import load_factory, parse_manifest_parameter_assignments, resolve_agent_model, resolve_memory_path
from harnessiq.cli.runners.lifecycle import HarnessCliLifecycleRunner
from harnessiq.shared.exa_outreach import EXA_OUTREACH_HARNESS_MANIFEST, EmailTemplate, ExaOutreachMemoryStore


class ExaOutreachCliRunner:
    """Execute Exa Outreach-specific CLI lifecycle actions."""

    def run(
        self,
        *,
        agent_name: str,
        memory_root: str,
        model_factory: str | None,
        model: str | None,
        model_profile: str | None,
        exa_credentials_factory: str,
        resend_credentials_factory: str | None,
        email_data_factory: str | None,
        search_only: bool,
        runtime_assignments: Sequence[str],
        sink_specs: Sequence[str],
        max_cycles: int | None,
        approval_policy: str | None,
        allowed_tools: Sequence[str],
    ) -> dict[str, Any]:
        store = self._load_store(agent_name=agent_name, memory_root=memory_root)
        store.prepare()
        self._validate_delivery_factories(
            search_only=search_only,
            resend_credentials_factory=resend_credentials_factory,
            email_data_factory=email_data_factory,
        )
        seed_cli_environment(Path(memory_root).expanduser())

        exa_credentials = load_factory(exa_credentials_factory)()
        resend_credentials = load_factory(resend_credentials_factory)() if resend_credentials_factory and not search_only else None
        email_data = self._load_email_data(email_data_factory=email_data_factory, search_only=search_only)

        query_config = store.read_query_config()
        query_config.update(self.parse_runtime_assignments(runtime_assignments))

        search_query = str(query_config.pop("search_query", ""))
        max_tokens = int(query_config.pop("max_tokens", 80_000))
        reset_threshold = float(query_config.pop("reset_threshold", 0.9))

        agent = ExaOutreachAgent(
            model=resolve_agent_model(
                model_factory=model_factory,
                model_spec=model,
                profile_name=model_profile,
            ),
            exa_credentials=exa_credentials,
            resend_credentials=resend_credentials,
            email_data=email_data,
            search_only=search_only,
            search_query=search_query,
            memory_path=store.memory_path,
            max_tokens=max_tokens,
            reset_threshold=reset_threshold,
            runtime_config=HarnessCliLifecycleRunner().build_runtime_config(
                sink_specs=sink_specs,
                approval_policy=approval_policy,
                allowed_tools=allowed_tools,
            ),
        )
        result = agent.run(max_cycles=max_cycles)

        run_id = self._run_id(agent)
        self._print_run_summary(store, run_id)
        return {
            "agent": agent_name,
            "instance_id": self._optional_string(getattr(agent, "instance_id", None)),
            "instance_name": self._optional_string(getattr(agent, "instance_name", None)),
            "ledger_run_id": self._stringify_optional(getattr(agent, "last_run_id", None)),
            "memory_path": str(store.memory_path.resolve()),
            "run_id": run_id,
            "result": {
                "cycles_completed": result.cycles_completed,
                "pause_reason": result.pause_reason,
                "resets": result.resets,
                "status": result.status,
            },
        }

    def parse_runtime_assignments(self, assignments: Sequence[str]) -> dict[str, Any]:
        return parse_manifest_parameter_assignments(
            assignments,
            manifest=EXA_OUTREACH_HARNESS_MANIFEST,
            scope="runtime",
        )

    def _load_store(
        self,
        *,
        agent_name: str,
        memory_root: str,
    ) -> ExaOutreachMemoryStore:
        return ExaOutreachMemoryStore(memory_path=resolve_memory_path(agent_name, memory_root))

    def _validate_delivery_factories(
        self,
        *,
        search_only: bool,
        resend_credentials_factory: str | None,
        email_data_factory: str | None,
    ) -> None:
        if search_only:
            return
        if not resend_credentials_factory:
            raise ValueError("--resend-credentials-factory is required unless --search-only is set.")
        if not email_data_factory:
            raise ValueError("--email-data-factory is required unless --search-only is set.")

    def _load_email_data(
        self,
        *,
        email_data_factory: str | None,
        search_only: bool,
    ) -> list[EmailTemplate]:
        if search_only:
            return []
        raw_email_data = load_factory(str(email_data_factory))()
        if not isinstance(raw_email_data, list):
            raise TypeError("Email data factory must return a list of dicts.")
        return [EmailTemplate.from_dict(item) for item in raw_email_data]

    def _run_id(self, agent: ExaOutreachAgent) -> str:
        run_id = getattr(agent, "_current_run_id", None) or "unknown"
        return run_id if isinstance(run_id, str) else str(run_id)

    def _optional_string(self, value: Any) -> str | None:
        return value if isinstance(value, str) and value else None

    def _stringify_optional(self, value: Any) -> str | None:
        if value is None:
            return None
        return value if isinstance(value, str) else str(value)

    def _print_run_summary(self, store: ExaOutreachMemoryStore, run_id: str) -> None:
        print()
        print("=" * 64)
        try:
            run_log = store.read_run(run_id)
            print(f"  RUN {run_id.upper()}")
            print(f"  Leads found:  {len(run_log.leads_found)}")
            print(f"  Emails sent:  {len(run_log.emails_sent)}")
            if run_log.emails_sent:
                print("  " + "-" * 60)
                for record in run_log.emails_sent:
                    print(f"  -> {record.to_name} <{record.to_email}> | {record.subject}")
        except FileNotFoundError:
            print(f"  No run file found for {run_id}.")
        print()
        print(f"  Run files saved to: {store.runs_dir.resolve()}")
        print("=" * 64)
        print()


__all__ = ["ExaOutreachCliRunner"]
