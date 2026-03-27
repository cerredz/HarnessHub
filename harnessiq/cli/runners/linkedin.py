"""LinkedIn-specific lifecycle runners for CLI command handlers."""

from __future__ import annotations

import os
import sys
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

from harnessiq.agents import LinkedInJobApplierAgent, LinkedInMemoryStore
from harnessiq.agents.linkedin import JobApplicationRecord, LINKEDIN_HARNESS_MANIFEST
from harnessiq.cli._langsmith import seed_cli_environment
from harnessiq.cli.common import (
    load_factory,
    parse_manifest_parameter_assignments,
    resolve_agent_model,
    resolve_memory_path,
)
from harnessiq.cli.runners.lifecycle import HarnessCliLifecycleRunner


class LinkedInCliRunner:
    """Execute LinkedIn-specific CLI lifecycle actions."""

    def run(
        self,
        *,
        agent_name: str,
        memory_root: str,
        model_factory: str | None,
        model: str | None,
        model_profile: str | None,
        browser_tools_factory: str | None,
        runtime_assignments: Sequence[str],
        sink_specs: Sequence[str],
        max_cycles: int | None,
        approval_policy: str | None,
        allowed_tools: Sequence[str],
    ) -> dict[str, Any]:
        store = self._load_store(agent_name=agent_name, memory_root=memory_root)
        store.prepare()
        seed_cli_environment(Path(memory_root).expanduser())

        browser_data_dir = store.memory_path / "browser-data"
        if browser_data_dir.exists() and "HARNESSIQ_BROWSER_SESSION_DIR" not in os.environ:
            os.environ["HARNESSIQ_BROWSER_SESSION_DIR"] = str(browser_data_dir.resolve())

        agent = LinkedInJobApplierAgent.from_memory(
            model=resolve_agent_model(
                model_factory=model_factory,
                model_spec=model,
                profile_name=model_profile,
            ),
            memory_path=store.memory_path,
            browser_tools=self._load_browser_tools(browser_tools_factory),
            runtime_overrides=self._parse_runtime_assignments(runtime_assignments),
            runtime_config=HarnessCliLifecycleRunner().build_runtime_config(
                sink_specs=sink_specs,
                approval_policy=approval_policy,
                allowed_tools=allowed_tools,
            ),
        )
        result = agent.run(max_cycles=max_cycles)
        self._print_applied_jobs_summary(store.read_applied_jobs(), store.applied_jobs_path)
        return {
            "agent": agent_name,
            "instance_id": self._optional_string(getattr(agent, "instance_id", None)),
            "instance_name": self._optional_string(getattr(agent, "instance_name", None)),
            "ledger_run_id": agent.last_run_id,
            "memory_path": str(store.memory_path.resolve()),
            "applied_jobs_file": str(store.applied_jobs_path.resolve()),
            "result": {
                "cycles_completed": result.cycles_completed,
                "pause_reason": result.pause_reason,
                "resets": result.resets,
                "status": result.status,
            },
        }

    def init_browser(
        self,
        *,
        agent_name: str,
        memory_root: str,
        wait_for_exit=input,
    ) -> dict[str, Any]:
        store = self._load_store(agent_name=agent_name, memory_root=memory_root)
        store.prepare()
        browser_data_dir = store.memory_path / "browser-data"

        try:
            from harnessiq.integrations.linkedin_playwright import PlaywrightLinkedInSession
        except ImportError as exc:
            raise RuntimeError(
                "playwright is required. Install with: pip install playwright && python -m playwright install chromium"
            ) from exc

        session = PlaywrightLinkedInSession(session_dir=browser_data_dir)
        session.start()
        print(f"Browser session saved to: {browser_data_dir.resolve()}")
        print()
        print("Session saved. You can now run the agent with:")
        print("  harnessiq linkedin run \\")
        print(f"    --agent {agent_name} \\")
        print("    --model grok:grok-4-1-fast-reasoning \\")
        print("    --browser-tools-factory harnessiq.integrations.linkedin_playwright:create_browser_tools \\")
        print("    --max-cycles 20")
        print()
        print("The browser session in the above directory will be reused automatically.")
        print("Press Enter to close the browser and exit.")
        wait_for_exit()
        session.stop()
        return {
            "agent": agent_name,
            "browser_data_dir": str(browser_data_dir.resolve()),
            "status": "session_saved",
        }

    def _load_store(
        self,
        *,
        agent_name: str,
        memory_root: str,
    ) -> LinkedInMemoryStore:
        return LinkedInMemoryStore(memory_path=resolve_memory_path(agent_name, memory_root))

    def _load_browser_tools(self, factory_spec: str | None) -> tuple[Any, ...]:
        if not factory_spec:
            return ()
        created_tools = load_factory(factory_spec)()
        if created_tools is None:
            return ()
        if isinstance(created_tools, (str, bytes)):
            raise TypeError("Browser tools factory must return an iterable of tool objects, not a string.")
        return tuple(created_tools)

    def _parse_runtime_assignments(self, assignments: Sequence[str]) -> dict[str, Any]:
        return parse_manifest_parameter_assignments(
            assignments,
            manifest=LINKEDIN_HARNESS_MANIFEST,
            scope="runtime",
        )

    def _optional_string(self, value: Any) -> str | None:
        return value if isinstance(value, str) and value else None

    def _print_applied_jobs_summary(
        self,
        jobs: list[JobApplicationRecord],
        applied_jobs_path: Path,
    ) -> None:
        stream = sys.stderr
        print(file=stream)
        print("=" * 64, file=stream)
        if not jobs:
            print("  NO DURABLE LINKEDIN APPLICATION RECORDS FOUND", file=stream)
        else:
            print(f"  DURABLE LINKEDIN APPLICATION RECORDS ({len(jobs)} total)", file=stream)
            print("  " + "-" * 60, file=stream)
            for job in jobs:
                status_label = job.status.upper() if job.status else "?"
                print(f"  [{status_label}] {job.title} @ {job.company}", file=stream)
                print(f"           {job.url}", file=stream)
                if job.notes:
                    print(f"           Note: {job.notes}", file=stream)
        print(file=stream)
        print("  Full records saved to:", file=stream)
        print(f"  {applied_jobs_path.resolve()}", file=stream)
        print("=" * 64, file=stream)
        print(file=stream)


__all__ = ["LinkedInCliRunner"]
