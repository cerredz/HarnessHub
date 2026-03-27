"""Instagram-specific lifecycle builders for CLI command handlers."""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from harnessiq.shared.instagram import (
    INSTAGRAM_HARNESS_MANIFEST,
    InstagramMemoryStore,
    resolve_instagram_icp_profiles,
)
from harnessiq.cli.common import (
    parse_manifest_parameter_assignments,
    resolve_memory_path,
    resolve_text_argument,
)


class InstagramCliBuilder:
    """Build and persist Instagram CLI-managed memory state."""

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
        icp_values: Sequence[str],
        icp_file: str | None,
        agent_identity_text: str | None,
        agent_identity_file: str | None,
        additional_prompt_text: str | None,
        additional_prompt_file: str | None,
        runtime_assignments: Sequence[str],
        custom_assignments: Sequence[str],
    ) -> dict[str, Any]:
        store = self._load_store(agent_name=agent_name, memory_root=memory_root)
        store.prepare()
        updated: list[str] = []

        icp_profiles = self.resolve_icp_profiles(icp_values=icp_values, icp_file=icp_file)
        if icp_profiles is not None:
            store.write_icp_profiles(icp_profiles)
            updated.append("icp_profiles")

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
            current = store.read_runtime_parameters()
            current.update(runtime_parameters)
            store.write_runtime_parameters(current)
            updated.append("runtime_parameters")

        custom_parameters = self._parse_custom_assignments(custom_assignments)
        if custom_parameters:
            current_custom = store.read_custom_parameters()
            current_custom.update(custom_parameters)
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

    def get_emails(
        self,
        *,
        agent_name: str,
        memory_root: str,
    ) -> dict[str, Any]:
        store = self._load_store(agent_name=agent_name, memory_root=memory_root)
        store.prepare()
        emails = store.get_emails()
        return {
            "agent": agent_name,
            "count": len(emails),
            "emails": emails,
            "memory_path": str(store.memory_path.resolve()),
        }

    def build_summary(self, *, store: InstagramMemoryStore) -> dict[str, Any]:
        search_history = store.read_search_history()
        lead_database = store.read_lead_database()
        custom_parameters = store.read_custom_parameters()
        run_state = store.read_run_state().as_dict() if store.run_state_path.exists() else None
        return {
            "additional_prompt": store.read_additional_prompt(),
            "agent_identity": store.read_agent_identity(),
            "custom_parameters": custom_parameters,
            "email_count": len(lead_database.emails),
            "icp_profiles": resolve_instagram_icp_profiles(store.read_icp_profiles(), custom_parameters),
            "lead_count": len(lead_database.leads),
            "memory_path": str(store.memory_path.resolve()),
            "recent_searches": [record.as_dict() for record in search_history[-5:]],
            "recent_searches_by_icp": store.read_recent_searches_by_icp(5),
            "run_state": run_state,
            "runtime_parameters": store.read_runtime_parameters(),
            "search_count": len(search_history),
        }

    def resolve_icp_profiles(
        self,
        *,
        icp_values: Sequence[str],
        icp_file: str | None,
    ) -> list[str] | None:
        return self._resolve_icp_input(icp_values, icp_file)

    def _load_store(
        self,
        *,
        agent_name: str,
        memory_root: str,
    ) -> InstagramMemoryStore:
        return InstagramMemoryStore(memory_path=resolve_memory_path(agent_name, memory_root))

    def _resolve_icp_input(self, inline_values: Sequence[str], file_value: str | None) -> list[str] | None:
        cleaned_inline = [value.strip() for value in inline_values if value and value.strip()]
        if file_value is None:
            return cleaned_inline or None
        raw = Path(file_value).read_text(encoding="utf-8").strip()
        if not raw:
            return []
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return [line.strip() for line in raw.splitlines() if line.strip()]
        if not isinstance(payload, list):
            raise ValueError("ICP file must be a JSON array or newline-delimited text file.")
        return [str(value).strip() for value in payload if str(value).strip()]

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


__all__ = ["InstagramCliBuilder"]
