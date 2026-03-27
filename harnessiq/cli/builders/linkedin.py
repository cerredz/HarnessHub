"""LinkedIn-specific lifecycle builders for CLI command handlers."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

from harnessiq.agents import LinkedInMemoryStore
from harnessiq.agents.linkedin import LINKEDIN_HARNESS_MANIFEST
from harnessiq.cli.common import (
    parse_generic_assignments,
    parse_manifest_parameter_assignments,
    resolve_memory_path,
    resolve_text_argument,
    split_assignment,
)


class LinkedInCliBuilder:
    """Build and persist LinkedIn CLI-managed memory state."""

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
        job_preferences_text: str | None,
        job_preferences_file: str | None,
        user_profile_text: str | None,
        user_profile_file: str | None,
        agent_identity_text: str | None,
        agent_identity_file: str | None,
        additional_prompt_text: str | None,
        additional_prompt_file: str | None,
        runtime_assignments: Sequence[str],
        custom_assignments: Sequence[str],
        import_files: Sequence[str],
        inline_files: Sequence[str],
    ) -> dict[str, Any]:
        store = self._load_store(agent_name=agent_name, memory_root=memory_root)
        store.prepare()
        updated: list[str] = []

        self._write_optional_text(
            store.write_job_preferences,
            resolve_text_argument(job_preferences_text, job_preferences_file),
            "job_preferences",
            updated,
        )
        self._write_optional_text(
            store.write_user_profile,
            resolve_text_argument(user_profile_text, user_profile_file),
            "user_profile",
            updated,
        )
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

        runtime_parameters = store.read_runtime_parameters()
        runtime_parameters.update(self._parse_runtime_assignments(runtime_assignments))
        if runtime_assignments:
            store.write_runtime_parameters(runtime_parameters)
            updated.append("runtime_parameters")

        custom_parameters = store.read_custom_parameters()
        custom_parameters.update(parse_generic_assignments(custom_assignments))
        if custom_assignments:
            store.write_custom_parameters(custom_parameters)
            updated.append("custom_parameters")

        for source_path in import_files:
            store.ingest_managed_file(source_path)
            updated.append(f"import_file:{Path(source_path).name}")

        for assignment in inline_files:
            filename, content = split_assignment(assignment)
            store.write_managed_text_file(name=filename, content=content, source_path="inline")
            updated.append(f"inline_file:{filename}")

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

    def build_summary(self, *, store: LinkedInMemoryStore) -> dict[str, Any]:
        return {
            "additional_prompt": store.read_additional_prompt(),
            "agent_identity": store.read_agent_identity(),
            "custom_parameters": store.read_custom_parameters(),
            "job_preferences": store.read_job_preferences(),
            "managed_files": [record.as_dict() for record in store.read_managed_files()],
            "memory_path": str(store.memory_path.resolve()),
            "runtime_parameters": store.read_runtime_parameters(),
            "user_profile": store.read_user_profile(),
        }

    def load_store(
        self,
        *,
        agent_name: str,
        memory_root: str,
    ) -> LinkedInMemoryStore:
        return self._load_store(agent_name=agent_name, memory_root=memory_root)

    def _load_store(
        self,
        *,
        agent_name: str,
        memory_root: str,
    ) -> LinkedInMemoryStore:
        return LinkedInMemoryStore(memory_path=resolve_memory_path(agent_name, memory_root))

    def _parse_runtime_assignments(self, assignments: Sequence[str]) -> dict[str, Any]:
        return parse_manifest_parameter_assignments(
            assignments,
            manifest=LINKEDIN_HARNESS_MANIFEST,
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


__all__ = ["LinkedInCliBuilder"]
