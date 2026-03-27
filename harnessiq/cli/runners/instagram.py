"""Instagram-specific lifecycle runners for CLI command handlers."""

from __future__ import annotations

import os
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from harnessiq.cli._langsmith import seed_cli_environment
from harnessiq.cli.common import (
    load_factory,
    parse_manifest_parameter_assignments,
    resolve_agent_model,
    resolve_memory_path,
)
from harnessiq.cli.runners.lifecycle import HarnessCliLifecycleRunner
from harnessiq.shared.instagram import INSTAGRAM_HARNESS_MANIFEST, InstagramMemoryStore


class InstagramCliRunner:
    """Execute Instagram-specific CLI lifecycle actions."""

    def run(
        self,
        *,
        agent_name: str,
        memory_root: str,
        model_factory: str | None,
        model: str | None,
        model_profile: str | None,
        search_backend_factory: str,
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
        from harnessiq.agents.instagram import InstagramKeywordDiscoveryAgent

        store = self._load_store(agent_name=agent_name, memory_root=memory_root)
        store.prepare()
        seed_cli_environment(Path(memory_root).expanduser())

        browser_data_dir = store.memory_path / "browser-data"
        if "HARNESSIQ_INSTAGRAM_SESSION_DIR" not in os.environ:
            os.environ["HARNESSIQ_INSTAGRAM_SESSION_DIR"] = str(browser_data_dir.resolve())

        agent = InstagramKeywordDiscoveryAgent.from_memory(
            model=resolve_agent_model(
                model_factory=model_factory,
                model_spec=model,
                profile_name=model_profile,
            ),
            search_backend=load_factory(search_backend_factory)(),
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
        )
        result = agent.run(max_cycles=max_cycles)
        return {
            "agent": agent_name,
            "email_count": len(agent.get_emails()),
            "memory_path": str(store.memory_path.resolve()),
            "result": {
                "cycles_completed": result.cycles_completed,
                "pause_reason": result.pause_reason,
                "resets": result.resets,
                "status": result.status,
            },
        }

    def parse_runtime_assignments(self, assignments: Sequence[str]) -> dict[str, Any]:
        return self._parse_runtime_assignments(assignments)

    def parse_custom_assignments(self, assignments: Sequence[str]) -> dict[str, Any]:
        return self._parse_custom_assignments(assignments)

    def _load_store(
        self,
        *,
        agent_name: str,
        memory_root: str,
    ) -> InstagramMemoryStore:
        return InstagramMemoryStore(memory_path=resolve_memory_path(agent_name, memory_root))

    def _parse_runtime_assignments(self, assignments: Sequence[str]) -> dict[str, Any]:
        return parse_manifest_parameter_assignments(
            assignments,
            manifest=INSTAGRAM_HARNESS_MANIFEST,
            scope="runtime",
        )

    def _parse_custom_assignments(self, assignments: Sequence[str]) -> dict[str, Any]:
        return parse_manifest_parameter_assignments(
            assignments,
            manifest=INSTAGRAM_HARNESS_MANIFEST,
            scope="custom",
        )


__all__ = ["InstagramCliRunner"]
