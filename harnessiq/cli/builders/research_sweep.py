"""Research Sweep-specific lifecycle builders for CLI command handlers."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from harnessiq.cli.common import (
    parse_manifest_parameter_assignments,
    resolve_memory_path,
    resolve_text_argument,
)
from harnessiq.shared.research_sweep import RESEARCH_SWEEP_HARNESS_MANIFEST, ResearchSweepMemoryStore, validate_query_for_run


class ResearchSweepCliBuilder:
    """Build and persist Research Sweep CLI-managed memory state."""

    def prepare(
        self,
        *,
        agent_name: str,
        memory_root: str,
    ) -> dict[str, Any]:
        store = self._load_store(agent_name=agent_name, memory_root=memory_root)
        store.prepare()
        return {
            "agent": agent_name,
            "memory_path": str(store.memory_path.resolve()),
            "status": "prepared",
        }

    def configure(
        self,
        *,
        agent_name: str,
        memory_root: str,
        query_text: str | None,
        query_file: str | None,
        additional_prompt_text: str | None,
        additional_prompt_file: str | None,
        runtime_assignments: Sequence[str],
        custom_assignments: Sequence[str],
    ) -> dict[str, Any]:
        store = self._load_store(agent_name=agent_name, memory_root=memory_root)
        store.prepare()
        updated: list[str] = []
        reset_required = False

        custom_parameters = store.read_custom_parameters()
        runtime_parameters = store.read_runtime_parameters()

        query = resolve_text_argument(query_text, query_file)
        if query is not None:
            normalized_query = validate_query_for_run(query)
            store.write_query(normalized_query)
            custom_parameters["query"] = normalized_query
            updated.append("query")
            reset_required = True

        additional_prompt = resolve_text_argument(additional_prompt_text, additional_prompt_file)
        if additional_prompt is not None:
            store.write_additional_prompt(additional_prompt)
            updated.append("additional_prompt")
            reset_required = True

        parsed_runtime = self._parse_runtime_assignments(runtime_assignments)
        if parsed_runtime:
            runtime_parameters.update(parsed_runtime)
            store.write_runtime_parameters(runtime_parameters)
            updated.append("runtime_parameters")

        parsed_custom = self._parse_custom_assignments(custom_assignments)
        if parsed_custom:
            custom_parameters.update(parsed_custom)
            if "query" in parsed_custom:
                normalized_query = validate_query_for_run(str(parsed_custom["query"]))
                custom_parameters["query"] = normalized_query
                store.write_query(normalized_query)
                reset_required = True
            if "allowed_serper_operations" in parsed_custom:
                reset_required = True
            store.write_custom_parameters(custom_parameters)
            updated.append("custom_parameters")
        else:
            store.write_custom_parameters(custom_parameters)

        if reset_required:
            store.clear_context_runtime_state()
            updated.append("progress_reset")

        payload = self.build_summary(store=store)
        payload["status"] = "configured"
        payload["updated"] = updated
        return payload

    def show(
        self,
        *,
        agent_name: str,
        memory_root: str,
    ) -> dict[str, Any]:
        store = self._load_store(agent_name=agent_name, memory_root=memory_root)
        store.prepare()
        return self.build_summary(store=store)

    def build_summary(self, *, store: ResearchSweepMemoryStore) -> dict[str, Any]:
        return {
            "additional_prompt": store.read_additional_prompt(),
            "custom_parameters": store.read_custom_parameters(),
            "final_report": store.read_final_report(),
            "memory_path": str(store.memory_path.resolve()),
            "query": store.read_query(),
            "research_memory": store.read_research_memory(),
            "research_memory_summary": store.read_research_memory_summary(),
            "runtime_parameters": store.read_runtime_parameters(),
        }

    def _load_store(
        self,
        *,
        agent_name: str,
        memory_root: str,
    ) -> ResearchSweepMemoryStore:
        return ResearchSweepMemoryStore(memory_path=resolve_memory_path(agent_name, memory_root))

    def _parse_runtime_assignments(self, assignments: Sequence[str]) -> dict[str, Any]:
        return parse_manifest_parameter_assignments(
            assignments,
            manifest=RESEARCH_SWEEP_HARNESS_MANIFEST,
            scope="runtime",
        )

    def _parse_custom_assignments(self, assignments: Sequence[str]) -> dict[str, Any]:
        return parse_manifest_parameter_assignments(
            assignments,
            manifest=RESEARCH_SWEEP_HARNESS_MANIFEST,
            scope="custom",
        )


__all__ = ["ResearchSweepCliBuilder"]
