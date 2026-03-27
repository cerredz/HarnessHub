"""Prospecting-specific lifecycle builders for CLI command handlers."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

from harnessiq.cli.common import (
    parse_manifest_parameter_assignments,
    resolve_memory_path,
    resolve_text_argument,
)
from harnessiq.shared.prospecting import ProspectingMemoryStore, PROSPECTING_HARNESS_MANIFEST, slugify_agent_name


class ProspectingCliBuilder:
    """Build and persist Prospecting CLI-managed memory state."""

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
        company_description_text: str | None,
        company_description_file: str | None,
        agent_identity_text: str | None,
        agent_identity_file: str | None,
        additional_prompt_text: str | None,
        additional_prompt_file: str | None,
        eval_system_prompt_file: str | None,
        runtime_assignments: Sequence[str],
        custom_assignments: Sequence[str],
    ) -> dict[str, Any]:
        store = self._load_store(agent_name=agent_name, memory_root=memory_root)
        store.prepare()
        updated: list[str] = []

        company_description = resolve_text_argument(company_description_text, company_description_file)
        if company_description is not None:
            store.write_company_description(company_description)
            store.ensure_state_matches_company_description()
            updated.append("company_description")

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

        runtime_parameters = self._parse_runtime_assignments(runtime_assignments)
        if runtime_parameters:
            current_runtime = store.read_runtime_parameters()
            current_runtime.update(runtime_parameters)
            store.write_runtime_parameters(current_runtime)
            updated.append("runtime_parameters")

        custom_parameters = self._parse_custom_assignments(custom_assignments)
        if custom_parameters or eval_system_prompt_file:
            current_custom = store.read_custom_parameters()
            current_custom.update(custom_parameters)
            if eval_system_prompt_file:
                current_custom["eval_system_prompt"] = Path(eval_system_prompt_file).read_text(encoding="utf-8")
                updated.append("eval_system_prompt")
            store.write_custom_parameters(current_custom)
            updated.append("custom_parameters")

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

    def build_summary(self, *, store: ProspectingMemoryStore) -> dict[str, Any]:
        state = store.read_state()
        qualified_leads = store.read_qualified_leads()
        return {
            "additional_prompt": store.read_additional_prompt(),
            "agent_identity": store.read_agent_identity(),
            "company_description": store.read_company_description(),
            "custom_parameters": store.read_custom_parameters(),
            "memory_path": str(store.memory_path.resolve()),
            "qualified_lead_count": len(qualified_leads),
            "recent_qualified_leads": [record.as_dict() for record in qualified_leads[-5:]],
            "run_state": state.as_dict(),
            "runtime_parameters": store.read_runtime_parameters(),
        }

    def _load_store(
        self,
        *,
        agent_name: str,
        memory_root: str,
    ) -> ProspectingMemoryStore:
        return ProspectingMemoryStore(
            memory_path=resolve_memory_path(agent_name, memory_root, slugifier=slugify_agent_name)
        )

    def _parse_runtime_assignments(self, assignments: Sequence[str]) -> dict[str, Any]:
        return parse_manifest_parameter_assignments(
            assignments,
            manifest=PROSPECTING_HARNESS_MANIFEST,
            scope="runtime",
        )

    def _parse_custom_assignments(self, assignments: Sequence[str]) -> dict[str, Any]:
        return parse_manifest_parameter_assignments(
            assignments,
            manifest=PROSPECTING_HARNESS_MANIFEST,
            scope="custom",
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


__all__ = ["ProspectingCliBuilder"]
