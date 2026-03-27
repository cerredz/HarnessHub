"""Leads-specific lifecycle builders for CLI command handlers."""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from harnessiq.cli.common import (
    parse_manifest_parameter_assignments,
    resolve_memory_path,
    resolve_text_argument,
)
from harnessiq.shared.leads import (
    LEADS_HARNESS_MANIFEST,
    RUNTIME_PARAMETERS_FILENAME,
    LeadICP,
    LeadRunConfig,
    LeadsMemoryStore,
)

_RUN_CONFIG_KEYS = frozenset({"search_summary_every", "search_tail_size", "max_leads_per_icp"})


class LeadsCliBuilder:
    """Build and persist Leads CLI-managed state."""

    def prepare(
        self,
        *,
        agent_name: str,
        memory_root: str,
    ) -> dict[str, Any]:
        store = self._load_store(agent_name=agent_name, memory_root=memory_root)
        store.prepare()
        self.ensure_runtime_parameters_file(store.memory_path)
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
        company_background_text: str | None,
        company_background_file: str | None,
        icp_texts: Sequence[str],
        icp_files: Sequence[str],
        platforms: Sequence[str],
        runtime_assignments: Sequence[str],
    ) -> dict[str, Any]:
        store = self._load_store(agent_name=agent_name, memory_root=memory_root)
        store.prepare()
        self.ensure_runtime_parameters_file(store.memory_path)
        updated: list[str] = []

        config_payload = self._read_run_config_payload(store)
        runtime_parameters = self.read_runtime_parameters(store.memory_path)

        company_background = resolve_text_argument(company_background_text, company_background_file)
        if company_background is not None:
            config_payload["company_background"] = company_background
            updated.append("company_background")

        icp_values = self._collect_icp_values(icp_texts, icp_files)
        if icp_values:
            config_payload["icps"] = [LeadICP(label=value).as_dict() for value in icp_values]
            updated.append("icps")

        if platforms:
            config_payload["platforms"] = [self._normalize_platform_name(value) for value in platforms]
            updated.append("platforms")

        normalized_parameters = parse_manifest_parameter_assignments(
            runtime_assignments,
            manifest=LEADS_HARNESS_MANIFEST,
            scope="runtime",
        )
        for key, value in normalized_parameters.items():
            if key in _RUN_CONFIG_KEYS:
                config_payload[key] = value
            else:
                runtime_parameters[key] = value
        if normalized_parameters:
            updated.append("runtime_parameters")

        if config_payload:
            missing = sorted(key for key in ("company_background", "icps", "platforms") if not config_payload.get(key))
            if missing:
                raise ValueError(f"Leads configuration is incomplete. Missing: {', '.join(missing)}.")
            run_config = LeadRunConfig.from_dict(config_payload)
            store.write_run_config(run_config)
            store.initialize_icp_states(run_config.icps)

        self.write_runtime_parameters(store.memory_path, runtime_parameters)
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
        self.ensure_runtime_parameters_file(store.memory_path)
        return self.build_summary(store=store)

    def build_summary(self, *, store: LeadsMemoryStore) -> dict[str, Any]:
        run_config = store.read_run_config().as_dict() if store.run_config_path.exists() else None
        run_state = store.read_run_state().as_dict() if store.run_state_path.exists() else None
        icp_states = [state.as_dict() for state in store.list_icp_states()]
        return {
            "memory_path": str(store.memory_path.resolve()),
            "run_config": run_config,
            "run_state": run_state,
            "runtime_parameters": self.read_runtime_parameters(store.memory_path),
            "icp_states": icp_states,
        }

    def load_store(
        self,
        *,
        agent_name: str,
        memory_root: str,
    ) -> LeadsMemoryStore:
        return self._load_store(agent_name=agent_name, memory_root=memory_root)

    def ensure_runtime_parameters_file(self, memory_path: Path) -> None:
        path = self.runtime_parameters_path(memory_path)
        if not path.exists():
            path.write_text(json.dumps({}, indent=2, sort_keys=True), encoding="utf-8")

    def read_runtime_parameters(self, memory_path: Path) -> dict[str, Any]:
        path = self.runtime_parameters_path(memory_path)
        if not path.exists():
            return {}
        raw = path.read_text(encoding="utf-8").strip()
        if not raw:
            return {}
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise ValueError(f"Expected JSON object in '{path.name}'.")
        return dict(payload)

    def write_runtime_parameters(self, memory_path: Path, payload: dict[str, Any]) -> None:
        self.runtime_parameters_path(memory_path).write_text(
            json.dumps(payload, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    def runtime_parameters_path(self, memory_path: Path) -> Path:
        return memory_path / RUNTIME_PARAMETERS_FILENAME

    def _load_store(
        self,
        *,
        agent_name: str,
        memory_root: str,
    ) -> LeadsMemoryStore:
        return LeadsMemoryStore(memory_path=resolve_memory_path(agent_name, memory_root))

    def _collect_icp_values(self, text_values: Sequence[str], file_values: Sequence[str]) -> list[str]:
        icps = [value.strip() for value in text_values if value.strip()]
        for file_value in file_values:
            for raw_line in Path(file_value).read_text(encoding="utf-8").splitlines():
                stripped = raw_line.strip()
                if stripped:
                    icps.append(stripped)
        return icps

    def _read_run_config_payload(self, store: LeadsMemoryStore) -> dict[str, Any]:
        if not store.run_config_path.exists():
            return {}
        return store.read_run_config().as_dict()

    def _normalize_platform_name(self, value: str) -> str:
        return value.strip().lower()


__all__ = ["LeadsCliBuilder"]
