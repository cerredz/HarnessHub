"""Exa Outreach-specific lifecycle builders for CLI command handlers."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from harnessiq.cli.common import (
    parse_manifest_parameter_assignments,
    resolve_memory_path,
    resolve_text_argument,
)
from harnessiq.shared.exa_outreach import EXA_OUTREACH_HARNESS_MANIFEST, ExaOutreachMemoryStore


class ExaOutreachCliBuilder:
    """Build and persist Exa Outreach CLI-managed memory state."""

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
        agent_identity_text: str | None,
        agent_identity_file: str | None,
        additional_prompt_text: str | None,
        additional_prompt_file: str | None,
        runtime_assignments: Sequence[str],
    ) -> dict[str, Any]:
        store = self._load_store(agent_name=agent_name, memory_root=memory_root)
        store.prepare()
        updated: list[str] = []

        query = resolve_text_argument(query_text, query_file)
        if query is not None:
            config = store.read_query_config()
            config["search_query"] = query
            store.write_query_config(config)
            updated.append("search_query")

        self._write_optional_text(
            store.write_agent_identity,
            resolve_text_argument(agent_identity_text, agent_identity_file),
            "agent_identity",
            updated,
        )
        self._write_optional_text(
            store.write_additional_prompt,
            resolve_text_argument(additional_prompt_text, additional_prompt_file),
            "additional_prompt",
            updated,
        )

        runtime_params = self._parse_runtime_assignments(runtime_assignments)
        if runtime_params:
            config = store.read_query_config()
            config.update(runtime_params)
            store.write_query_config(config)
            updated.append("runtime_parameters")

        payload = self.build_summary(store=store)
        payload["updated"] = updated
        payload["status"] = "configured"
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

    def build_summary(self, *, store: ExaOutreachMemoryStore) -> dict[str, Any]:
        return {
            "agent_identity": store.read_agent_identity(),
            "additional_prompt": store.read_additional_prompt(),
            "memory_path": str(store.memory_path.resolve()),
            "query_config": store.read_query_config(),
            "run_files": [str(path.name) for path in store.list_run_files()],
        }

    def _load_store(
        self,
        *,
        agent_name: str,
        memory_root: str,
    ) -> ExaOutreachMemoryStore:
        return ExaOutreachMemoryStore(memory_path=resolve_memory_path(agent_name, memory_root))

    def _parse_runtime_assignments(self, assignments: Sequence[str]) -> dict[str, Any]:
        return parse_manifest_parameter_assignments(
            assignments,
            manifest=EXA_OUTREACH_HARNESS_MANIFEST,
            scope="runtime",
        )

    def _write_optional_text(
        self,
        writer,
        content: str | None,
        key: str,
        updated: list[str],
    ) -> None:
        if content is None:
            return
        writer(content)
        updated.append(key)


__all__ = ["ExaOutreachCliBuilder"]
