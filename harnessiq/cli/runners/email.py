"""Email-campaign lifecycle runner for dedicated CLI commands."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

from harnessiq.cli._langsmith import seed_cli_environment
from harnessiq.cli.builders.lifecycle import HarnessCliLifecycleBuilder
from harnessiq.cli.common import (
    parse_manifest_parameter_assignments,
    resolve_agent_model,
    resolve_memory_path,
    resolve_repo_root,
)
from harnessiq.cli.runners.lifecycle import HarnessCliLifecycleRunner
from harnessiq.shared.email_campaign import EMAIL_HARNESS_MANIFEST, EmailCampaignMemoryStore


class EmailCliRunner:
    """Execute dedicated email-campaign lifecycle actions."""

    def run(
        self,
        *,
        agent_name: str,
        memory_root: str,
        model_factory: str | None,
        model: str | None,
        model_profile: str | None,
        runtime_overrides: dict[str, Any],
        custom_overrides: dict[str, Any],
        max_cycles: int | None,
        approval_policy: str | None,
        allowed_tools: Sequence[str],
        dynamic_tools: bool = False,
        dynamic_tool_candidates: Sequence[str] = (),
        dynamic_tool_top_k: int = 5,
        dynamic_tool_embedding_model: str | None = None,
    ) -> dict[str, Any]:
        from harnessiq.agents.email import EmailCampaignAgent

        store = self._load_store(agent_name=agent_name, memory_root=memory_root)
        store.prepare()
        seed_cli_environment(Path(memory_root).expanduser())
        repo_root = resolve_repo_root(Path(memory_root).expanduser())
        resend_credentials = HarnessCliLifecycleBuilder().resolve_bound_credentials(
            manifest=EMAIL_HARNESS_MANIFEST,
            agent_name=agent_name,
            repo_root=repo_root,
        ).get("resend")
        if resend_credentials is None:
            raise ValueError(
                "Email Campaign requires a 'resend' credential binding. "
                "Use `harnessiq credentials bind email ...` first."
            )
        agent = EmailCampaignAgent.from_memory(
            model=resolve_agent_model(
                model_factory=model_factory,
                model_spec=model,
                profile_name=model_profile,
            ),
            resend_credentials=resend_credentials,
            memory_path=store.memory_path,
            runtime_overrides=runtime_overrides,
            custom_overrides=custom_overrides,
            runtime_config=HarnessCliLifecycleRunner().build_runtime_config(
                sink_specs=(),
                approval_policy=approval_policy,
                allowed_tools=allowed_tools,
                dynamic_tools_enabled=dynamic_tools,
                dynamic_tool_candidates=dynamic_tool_candidates,
                dynamic_tool_top_k=dynamic_tool_top_k,
                dynamic_tool_embedding_model=dynamic_tool_embedding_model,
            ),
            instance_name=agent_name,
        )
        result = agent.run(max_cycles=max_cycles)
        return {
            "agent": agent_name,
            "delivery_count": len(agent.build_ledger_outputs()["delivery_records"]),
            "memory_path": str(store.memory_path.resolve()),
            "recipient_batch_count": len(agent.build_ledger_outputs()["recipient_batch"]),
            "result": {
                "cycles_completed": result.cycles_completed,
                "pause_reason": result.pause_reason,
                "resets": result.resets,
                "status": result.status,
            },
            "sent_count": len(store.read_sent_history()),
        }

    def parse_runtime_assignments(self, assignments: Sequence[str]) -> dict[str, Any]:
        return parse_manifest_parameter_assignments(
            assignments,
            manifest=EMAIL_HARNESS_MANIFEST,
            scope="runtime",
        )

    def parse_custom_assignments(self, assignments: Sequence[str]) -> dict[str, Any]:
        return parse_manifest_parameter_assignments(
            assignments,
            manifest=EMAIL_HARNESS_MANIFEST,
            scope="custom",
        )

    def _load_store(self, *, agent_name: str, memory_root: str) -> EmailCampaignMemoryStore:
        return EmailCampaignMemoryStore(memory_path=resolve_memory_path(agent_name, memory_root))


__all__ = ["EmailCliRunner"]
