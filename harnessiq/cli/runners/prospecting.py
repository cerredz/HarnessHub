"""Prospecting-specific lifecycle runners for CLI command handlers."""

from __future__ import annotations

import os
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from harnessiq.agents import GoogleMapsProspectingAgent, ProspectingMemoryStore
from harnessiq.cli._langsmith import seed_cli_environment
from harnessiq.cli.builders.prospecting import ProspectingCliBuilder
from harnessiq.cli.common import (
    load_factory,
    parse_manifest_parameter_assignments,
    resolve_agent_model,
    resolve_memory_path,
)
from harnessiq.cli.runners.lifecycle import HarnessCliLifecycleRunner
from harnessiq.shared.prospecting import PROSPECTING_HARNESS_MANIFEST, slugify_agent_name, validate_company_description_for_run

_DEFAULT_BROWSER_TOOLS_FACTORY = "harnessiq.integrations.google_maps_playwright:create_browser_tools"


class ProspectingCliRunner:
    """Execute Prospecting-specific CLI lifecycle actions."""

    def run(
        self,
        *,
        agent_name: str,
        memory_root: str,
        model_factory: str | None,
        model: str | None,
        model_profile: str | None,
        browser_tools_factory: str,
        runtime_assignments: Sequence[str],
        custom_assignments: Sequence[str],
        sink_specs: Sequence[str],
        max_cycles: int | None,
        approval_policy: str | None,
        allowed_tools: Sequence[str],
    ) -> dict[str, Any]:
        store = self._load_store(agent_name=agent_name, memory_root=memory_root)
        store.prepare()
        validate_company_description_for_run(store.read_company_description())
        seed_cli_environment(Path(memory_root).expanduser())

        if "HARNESSIQ_PROSPECTING_SESSION_DIR" not in os.environ:
            os.environ["HARNESSIQ_PROSPECTING_SESSION_DIR"] = str(store.browser_data_dir.resolve())

        agent = GoogleMapsProspectingAgent.from_memory(
            model=resolve_agent_model(
                model_factory=model_factory,
                model_spec=model,
                profile_name=model_profile,
            ),
            memory_path=store.memory_path,
            browser_tools=self._load_browser_tools(browser_tools_factory),
            runtime_overrides=self.parse_runtime_assignments(runtime_assignments),
            custom_overrides=self.parse_custom_assignments(custom_assignments),
            runtime_config=HarnessCliLifecycleRunner().build_runtime_config(
                sink_specs=sink_specs,
                approval_policy=approval_policy,
                allowed_tools=allowed_tools,
            ),
        )
        result = agent.run(max_cycles=max_cycles)
        payload = ProspectingCliBuilder().build_summary(store=store)
        payload.update(
            {
                "agent": agent_name,
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

    def init_browser(
        self,
        *,
        agent_name: str,
        memory_root: str,
        channel: str,
        headless: bool,
        wait_for_exit: Callable[[], str] | None = None,
    ) -> dict[str, Any]:
        try:
            from harnessiq.integrations.google_maps_playwright import PlaywrightGoogleMapsSession
        except ImportError as exc:
            raise RuntimeError(
                "playwright is required. Install with: pip install playwright && python -m playwright install chromium"
            ) from exc

        store = self._load_store(agent_name=agent_name, memory_root=memory_root)
        store.prepare()
        session = PlaywrightGoogleMapsSession(
            session_dir=store.browser_data_dir,
            channel=channel,
            headless=headless,
        )
        session.start()

        print(f"Browser session saved to: {store.browser_data_dir.resolve()}")
        print()
        print("Open Google Maps, sign in if needed, then press Enter to close the browser.")
        (wait_for_exit or input)()
        session.stop()
        return {
            "agent": agent_name,
            "browser_data_dir": str(store.browser_data_dir.resolve()),
            "status": "session_saved",
        }

    def parse_runtime_assignments(self, assignments: Sequence[str]) -> dict[str, Any]:
        return parse_manifest_parameter_assignments(
            assignments,
            manifest=PROSPECTING_HARNESS_MANIFEST,
            scope="runtime",
        )

    def parse_custom_assignments(self, assignments: Sequence[str]) -> dict[str, Any]:
        return parse_manifest_parameter_assignments(
            assignments,
            manifest=PROSPECTING_HARNESS_MANIFEST,
            scope="custom",
        )

    def _load_store(
        self,
        *,
        agent_name: str,
        memory_root: str,
    ) -> ProspectingMemoryStore:
        return ProspectingMemoryStore(
            memory_path=resolve_memory_path(agent_name, memory_root, slugifier=slugify_agent_name)
        )

    def _load_browser_tools(self, factory_spec: str | None) -> tuple[Any, ...]:
        if not factory_spec:
            return ()
        created_tools = load_factory(factory_spec)()
        if created_tools is None:
            return ()
        if isinstance(created_tools, (str, bytes)):
            raise TypeError("Browser tools factory must return an iterable of tool objects, not a string.")
        return tuple(created_tools)


__all__ = ["ProspectingCliRunner", "_DEFAULT_BROWSER_TOOLS_FACTORY"]
