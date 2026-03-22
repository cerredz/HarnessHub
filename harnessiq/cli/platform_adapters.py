"""Built-in harness adapters for the platform-first CLI."""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from harnessiq.agents import (
    AgentModel,
    AgentRuntimeConfig,
    ExaOutreachAgent,
    GoogleMapsProspectingAgent,
    InstagramKeywordDiscoveryAgent,
    KnowtAgent,
    LeadsAgent,
    LinkedInJobApplierAgent,
)
from harnessiq.cli.common import load_factory, split_assignment
from harnessiq.config import HarnessProfile
from harnessiq.shared.harness_manifest import HarnessManifest
from harnessiq.shared.instagram import InstagramMemoryStore
from harnessiq.shared.knowt import KnowtMemoryStore
from harnessiq.shared.leads import LeadsMemoryStore, RUNTIME_PARAMETERS_FILENAME as LEADS_RUNTIME_PARAMETERS_FILENAME
from harnessiq.shared.linkedin import LinkedInMemoryStore
from harnessiq.shared.prospecting import ProspectingMemoryStore
from harnessiq.shared.exa_outreach import ExaOutreachMemoryStore, EmailTemplate

_DEFAULT_INSTAGRAM_SEARCH_BACKEND_FACTORY = "harnessiq.integrations.instagram_playwright:create_search_backend"
_DEFAULT_PROSPECTING_BROWSER_TOOLS_FACTORY = "harnessiq.integrations.google_maps_playwright:create_browser_tools"

_LEADS_RUN_CONFIG_PARAMETER_KEYS = frozenset({"search_summary_every", "search_tail_size", "max_leads_per_icp"})


@dataclass(frozen=True, slots=True)
class HarnessAdapterContext:
    """Shared execution context passed into one harness adapter."""

    manifest: HarnessManifest
    agent_name: str
    memory_path: Path
    repo_root: Path
    profile: HarnessProfile
    runtime_parameters: dict[str, Any]
    custom_parameters: dict[str, Any]
    bound_credentials: dict[str, object]


class HarnessCliAdapter(Protocol):
    """Protocol implemented by platform CLI harness adapters."""

    def register_run_arguments(self, parser: argparse.ArgumentParser) -> None:
        ...

    def prepare(self, context: HarnessAdapterContext) -> None:
        ...

    def load_native_parameters(self, context: HarnessAdapterContext) -> tuple[dict[str, Any], dict[str, Any]]:
        ...

    def synchronize_profile(self, context: HarnessAdapterContext) -> None:
        ...

    def show(self, context: HarnessAdapterContext) -> dict[str, Any]:
        ...

    def run(
        self,
        *,
        args: argparse.Namespace,
        context: HarnessAdapterContext,
        model: AgentModel,
        runtime_config: AgentRuntimeConfig,
    ) -> dict[str, Any]:
        ...


class BaseHarnessCliAdapter:
    """Default adapter behavior for platform CLI harnesses."""

    def register_run_arguments(self, parser: argparse.ArgumentParser) -> None:
        del parser

    def prepare(self, context: HarnessAdapterContext) -> None:
        del context

    def load_native_parameters(self, context: HarnessAdapterContext) -> tuple[dict[str, Any], dict[str, Any]]:
        del context
        return {}, {}

    def synchronize_profile(self, context: HarnessAdapterContext) -> None:
        del context

    def show(self, context: HarnessAdapterContext) -> dict[str, Any]:
        del context
        return {}


class LinkedInHarnessCliAdapter(BaseHarnessCliAdapter):
    def register_run_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--browser-tools-factory",
            help="Optional import path (module:callable) that returns LinkedIn browser tools.",
        )

    def prepare(self, context: HarnessAdapterContext) -> None:
        _linkedin_store(context.memory_path).prepare()

    def load_native_parameters(self, context: HarnessAdapterContext) -> tuple[dict[str, Any], dict[str, Any]]:
        store = _linkedin_store(context.memory_path)
        store.prepare()
        return store.read_runtime_parameters(), store.read_custom_parameters()

    def synchronize_profile(self, context: HarnessAdapterContext) -> None:
        store = _linkedin_store(context.memory_path)
        store.prepare()
        store.write_runtime_parameters(context.profile.runtime_parameters)
        store.write_custom_parameters(context.profile.custom_parameters)

    def show(self, context: HarnessAdapterContext) -> dict[str, Any]:
        store = _linkedin_store(context.memory_path)
        store.prepare()
        return {
            "additional_prompt": store.read_additional_prompt(),
            "agent_identity": store.read_agent_identity(),
            "custom_parameters": store.read_custom_parameters(),
            "job_preferences": store.read_job_preferences(),
            "managed_files": [record.as_dict() for record in store.read_managed_files()],
            "runtime_parameters": store.read_runtime_parameters(),
            "user_profile": store.read_user_profile(),
        }

    def run(
        self,
        *,
        args: argparse.Namespace,
        context: HarnessAdapterContext,
        model: AgentModel,
        runtime_config: AgentRuntimeConfig,
    ) -> dict[str, Any]:
        store = _linkedin_store(context.memory_path)
        store.prepare()
        browser_data_dir = store.memory_path / "browser-data"
        if browser_data_dir.exists() and "HARNESSIQ_BROWSER_SESSION_DIR" not in os.environ:
            os.environ["HARNESSIQ_BROWSER_SESSION_DIR"] = str(browser_data_dir.resolve())
        browser_tools = _load_optional_iterable_factory(args.browser_tools_factory)
        agent = LinkedInJobApplierAgent.from_memory(
            model=model,
            memory_path=context.memory_path,
            browser_tools=browser_tools,
            runtime_overrides=context.runtime_parameters,
            runtime_config=runtime_config,
        )
        result = agent.run(max_cycles=args.max_cycles)
        return {
            "applied_jobs_file": str(store.applied_jobs_path.resolve()),
            "instance_id": _optional_string(getattr(agent, "instance_id", None)),
            "instance_name": _optional_string(getattr(agent, "instance_name", None)),
            "ledger_run_id": agent.last_run_id,
            "result": _result_payload(result),
        }


class InstagramHarnessCliAdapter(BaseHarnessCliAdapter):
    def register_run_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--search-backend-factory",
            default=_DEFAULT_INSTAGRAM_SEARCH_BACKEND_FACTORY,
            help=(
                "Import path (module:callable) that returns an Instagram search backend. "
                f"Defaults to {_DEFAULT_INSTAGRAM_SEARCH_BACKEND_FACTORY}."
            ),
        )

    def prepare(self, context: HarnessAdapterContext) -> None:
        _instagram_store(context.memory_path).prepare()

    def load_native_parameters(self, context: HarnessAdapterContext) -> tuple[dict[str, Any], dict[str, Any]]:
        store = _instagram_store(context.memory_path)
        store.prepare()
        return store.read_runtime_parameters(), {}

    def synchronize_profile(self, context: HarnessAdapterContext) -> None:
        store = _instagram_store(context.memory_path)
        store.prepare()
        store.write_runtime_parameters(dict(context.profile.runtime_parameters))

    def show(self, context: HarnessAdapterContext) -> dict[str, Any]:
        store = _instagram_store(context.memory_path)
        store.prepare()
        search_history = store.read_search_history()
        lead_database = store.read_lead_database()
        return {
            "additional_prompt": store.read_additional_prompt(),
            "agent_identity": store.read_agent_identity(),
            "email_count": len(lead_database.emails),
            "icp_profiles": store.read_icp_profiles(),
            "lead_count": len(lead_database.leads),
            "recent_searches": [record.as_dict() for record in search_history[-5:]],
            "runtime_parameters": store.read_runtime_parameters(),
            "search_count": len(search_history),
        }

    def run(
        self,
        *,
        args: argparse.Namespace,
        context: HarnessAdapterContext,
        model: AgentModel,
        runtime_config: AgentRuntimeConfig,
    ) -> dict[str, Any]:
        store = _instagram_store(context.memory_path)
        store.prepare()
        browser_data_dir = store.memory_path / "browser-data"
        if "HARNESSIQ_INSTAGRAM_SESSION_DIR" not in os.environ:
            os.environ["HARNESSIQ_INSTAGRAM_SESSION_DIR"] = str(browser_data_dir.resolve())
        search_backend = load_factory(args.search_backend_factory)()
        agent = InstagramKeywordDiscoveryAgent.from_memory(
            model=model,
            search_backend=search_backend,
            memory_path=context.memory_path,
            runtime_overrides=context.runtime_parameters,
            runtime_config=runtime_config,
        )
        result = agent.run(max_cycles=args.max_cycles)
        return {
            "email_count": len(agent.get_emails()),
            "result": _result_payload(result),
        }


class ProspectingHarnessCliAdapter(BaseHarnessCliAdapter):
    def register_run_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--browser-tools-factory",
            default=_DEFAULT_PROSPECTING_BROWSER_TOOLS_FACTORY,
            help=(
                "Import path (module:callable) that returns browser tools. "
                f"Defaults to {_DEFAULT_PROSPECTING_BROWSER_TOOLS_FACTORY}."
            ),
        )

    def prepare(self, context: HarnessAdapterContext) -> None:
        _prospecting_store(context.memory_path).prepare()

    def load_native_parameters(self, context: HarnessAdapterContext) -> tuple[dict[str, Any], dict[str, Any]]:
        store = _prospecting_store(context.memory_path)
        store.prepare()
        return store.read_runtime_parameters(), store.read_custom_parameters()

    def synchronize_profile(self, context: HarnessAdapterContext) -> None:
        store = _prospecting_store(context.memory_path)
        store.prepare()
        store.write_runtime_parameters(context.profile.runtime_parameters)
        store.write_custom_parameters(context.profile.custom_parameters)

    def show(self, context: HarnessAdapterContext) -> dict[str, Any]:
        store = _prospecting_store(context.memory_path)
        store.prepare()
        state = store.read_state()
        qualified_leads = store.read_qualified_leads()
        return {
            "additional_prompt": store.read_additional_prompt(),
            "agent_identity": store.read_agent_identity(),
            "company_description": store.read_company_description(),
            "custom_parameters": store.read_custom_parameters(),
            "qualified_lead_count": len(qualified_leads),
            "recent_qualified_leads": [record.as_dict() for record in qualified_leads[-5:]],
            "run_state": state.as_dict(),
            "runtime_parameters": store.read_runtime_parameters(),
        }

    def run(
        self,
        *,
        args: argparse.Namespace,
        context: HarnessAdapterContext,
        model: AgentModel,
        runtime_config: AgentRuntimeConfig,
    ) -> dict[str, Any]:
        store = _prospecting_store(context.memory_path)
        store.prepare()
        if "HARNESSIQ_PROSPECTING_SESSION_DIR" not in os.environ:
            os.environ["HARNESSIQ_PROSPECTING_SESSION_DIR"] = str(store.browser_data_dir.resolve())
        browser_tools = _load_optional_iterable_factory(args.browser_tools_factory)
        agent = GoogleMapsProspectingAgent.from_memory(
            model=model,
            memory_path=context.memory_path,
            browser_tools=browser_tools,
            runtime_overrides=context.runtime_parameters,
            custom_overrides=context.custom_parameters,
            runtime_config=runtime_config,
        )
        result = agent.run(max_cycles=args.max_cycles)
        payload = self.show(context)
        payload.update(
            {
                "ledger_run_id": agent.last_run_id,
                "result": _result_payload(result),
            }
        )
        return payload


class LeadsHarnessCliAdapter(BaseHarnessCliAdapter):
    def register_run_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--provider-tools-factory",
            help="Optional import path (module:callable) that returns additional provider tools.",
        )
        parser.add_argument(
            "--provider-client-factory",
            action="append",
            default=[],
            metavar="FAMILY=MODULE:CALLABLE",
            help="Map a provider family to a prebuilt client factory. May be repeated.",
        )
        parser.add_argument(
            "--storage-backend-factory",
            help="Optional import path (module:callable) that returns a LeadsStorageBackend instance.",
        )

    def prepare(self, context: HarnessAdapterContext) -> None:
        _leads_store(context.memory_path).prepare()

    def load_native_parameters(self, context: HarnessAdapterContext) -> tuple[dict[str, Any], dict[str, Any]]:
        store = _leads_store(context.memory_path)
        store.prepare()
        runtime_parameters: dict[str, Any] = {}
        if store.run_config_path.exists():
            run_config = store.read_run_config()
            runtime_parameters.update(
                {
                    "max_leads_per_icp": run_config.max_leads_per_icp,
                    "search_summary_every": run_config.search_summary_every,
                    "search_tail_size": run_config.search_tail_size,
                }
            )
        runtime_parameters.update(_read_json_object(context.memory_path / LEADS_RUNTIME_PARAMETERS_FILENAME))
        return runtime_parameters, {}

    def show(self, context: HarnessAdapterContext) -> dict[str, Any]:
        store = _leads_store(context.memory_path)
        store.prepare()
        return {
            "icp_states": [state.as_dict() for state in store.list_icp_states()],
            "run_config": store.read_run_config().as_dict() if store.run_config_path.exists() else None,
            "run_state": store.read_run_state().as_dict() if store.run_state_path.exists() else None,
            "runtime_parameters": _read_json_object(context.memory_path / LEADS_RUNTIME_PARAMETERS_FILENAME),
        }

    def run(
        self,
        *,
        args: argparse.Namespace,
        context: HarnessAdapterContext,
        model: AgentModel,
        runtime_config: AgentRuntimeConfig,
    ) -> dict[str, Any]:
        store = _leads_store(context.memory_path)
        store.prepare()
        if not store.run_config_path.exists():
            raise ValueError(
                "Leads run configuration is missing. Configure company background, ICPs, and platforms first."
            )
        run_config = store.read_run_config()
        provider_tools = _load_optional_iterable_factory(args.provider_tools_factory)
        provider_clients = _load_factory_assignment_map(args.provider_client_factory)
        storage_backend = load_factory(args.storage_backend_factory)() if args.storage_backend_factory else None
        search_summary_every = int(context.runtime_parameters.get("search_summary_every", run_config.search_summary_every))
        search_tail_size = int(context.runtime_parameters.get("search_tail_size", run_config.search_tail_size))
        max_leads_per_icp = context.runtime_parameters.get("max_leads_per_icp", run_config.max_leads_per_icp)
        agent = LeadsAgent(
            model=model,
            company_background=run_config.company_background,
            icps=run_config.icps,
            platforms=run_config.platforms,
            memory_path=context.memory_path,
            storage_backend=storage_backend,
            max_tokens=int(context.runtime_parameters["max_tokens"]),
            reset_threshold=float(context.runtime_parameters["reset_threshold"]),
            prune_search_interval=(
                int(context.runtime_parameters["prune_search_interval"])
                if context.runtime_parameters.get("prune_search_interval") is not None
                else None
            ),
            prune_token_limit=(
                int(context.runtime_parameters["prune_token_limit"])
                if context.runtime_parameters.get("prune_token_limit") is not None
                else None
            ),
            search_summary_every=search_summary_every,
            search_tail_size=search_tail_size,
            max_leads_per_icp=(
                int(max_leads_per_icp) if max_leads_per_icp is not None else None
            ),
            provider_credentials=context.bound_credentials or None,
            provider_clients=provider_clients or None,
            tools=provider_tools or None,
            runtime_config=runtime_config,
        )
        result = agent.run(max_cycles=args.max_cycles)
        return {
            "result": _result_payload(result),
            "run_state": store.read_run_state().as_dict() if store.run_state_path.exists() else None,
        }


class KnowtHarnessCliAdapter(BaseHarnessCliAdapter):
    def prepare(self, context: HarnessAdapterContext) -> None:
        _knowt_store(context.memory_path).prepare()

    def show(self, context: HarnessAdapterContext) -> dict[str, Any]:
        store = _knowt_store(context.memory_path)
        store.prepare()
        creation_log = store.read_creation_log()
        return {
            "avatar_description": store.read_avatar_description(),
            "creation_log_count": len(creation_log),
            "recent_creation_log": [entry.as_dict() for entry in creation_log[-5:]],
            "script": store.read_script(),
        }

    def run(
        self,
        *,
        args: argparse.Namespace,
        context: HarnessAdapterContext,
        model: AgentModel,
        runtime_config: AgentRuntimeConfig,
    ) -> dict[str, Any]:
        _knowt_store(context.memory_path).prepare()
        agent = KnowtAgent(
            model=model,
            memory_path=context.memory_path,
            creatify_credentials=context.bound_credentials.get("creatify"),
            max_tokens=int(context.runtime_parameters["max_tokens"]),
            reset_threshold=float(context.runtime_parameters["reset_threshold"]),
            runtime_config=runtime_config,
        )
        result = agent.run(max_cycles=args.max_cycles)
        return {
            "result": _result_payload(result),
            "state": self.show(context),
        }


class ExaOutreachHarnessCliAdapter(BaseHarnessCliAdapter):
    def register_run_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--email-data-factory",
            help="Import path (module:callable) that returns a list of email template dicts.",
        )
        parser.add_argument(
            "--search-only",
            action="store_true",
            default=False,
            help="Discover and log leads only; skip email sending.",
        )

    def prepare(self, context: HarnessAdapterContext) -> None:
        _exa_store(context.memory_path).prepare()

    def load_native_parameters(self, context: HarnessAdapterContext) -> tuple[dict[str, Any], dict[str, Any]]:
        store = _exa_store(context.memory_path)
        store.prepare()
        query_config = store.read_query_config()
        runtime_parameters = {
            key: value
            for key, value in query_config.items()
            if key in set(context.manifest.runtime_parameter_names)
        }
        return runtime_parameters, {}

    def synchronize_profile(self, context: HarnessAdapterContext) -> None:
        store = _exa_store(context.memory_path)
        store.prepare()
        query_config = store.read_query_config()
        for key in context.profile.runtime_parameters:
            query_config[key] = context.profile.runtime_parameters[key]
        store.write_query_config(query_config)

    def show(self, context: HarnessAdapterContext) -> dict[str, Any]:
        store = _exa_store(context.memory_path)
        store.prepare()
        return {
            "additional_prompt": store.read_additional_prompt(),
            "agent_identity": store.read_agent_identity(),
            "query_config": store.read_query_config(),
            "run_files": [path.name for path in store.list_run_files()],
        }

    def run(
        self,
        *,
        args: argparse.Namespace,
        context: HarnessAdapterContext,
        model: AgentModel,
        runtime_config: AgentRuntimeConfig,
    ) -> dict[str, Any]:
        store = _exa_store(context.memory_path)
        store.prepare()
        search_only = bool(args.search_only)
        exa_credentials = context.bound_credentials.get("exa")
        if exa_credentials is None:
            raise ValueError("Exa Outreach requires an 'exa' credential binding. Use `harnessiq credentials bind` first.")
        resend_credentials = context.bound_credentials.get("resend")
        if not search_only and resend_credentials is None:
            raise ValueError(
                "Exa Outreach email mode requires a 'resend' credential binding. Use `harnessiq credentials bind` first."
            )
        email_data: list[EmailTemplate] = []
        if not search_only:
            if not args.email_data_factory:
                raise ValueError("--email-data-factory is required unless --search-only is set.")
            raw_email_data = load_factory(args.email_data_factory)()
            if not isinstance(raw_email_data, list):
                raise TypeError("Email data factory must return a list of template dictionaries.")
            email_data = [EmailTemplate.from_dict(dict(payload)) for payload in raw_email_data]

        query_config = store.read_query_config()
        search_query = str(query_config.get("search_query", "")).strip()
        agent = ExaOutreachAgent(
            model=model,
            exa_credentials=exa_credentials,
            resend_credentials=resend_credentials,
            email_data=email_data,
            search_only=search_only,
            search_query=search_query,
            memory_path=context.memory_path,
            max_tokens=int(context.runtime_parameters["max_tokens"]),
            reset_threshold=float(context.runtime_parameters["reset_threshold"]),
            runtime_config=runtime_config,
        )
        result = agent.run(max_cycles=args.max_cycles)
        run_id = agent._current_run_id or "unknown"
        return {
            "instance_id": _optional_string(getattr(agent, "instance_id", None)),
            "instance_name": _optional_string(getattr(agent, "instance_name", None)),
            "ledger_run_id": _optional_string(getattr(agent, "last_run_id", None)),
            "result": _result_payload(result),
            "run_id": str(run_id),
            "state": self.show(context),
        }


def _load_optional_iterable_factory(spec: str | None) -> tuple[Any, ...]:
    if not spec:
        return ()
    created = load_factory(spec)()
    if created is None:
        return ()
    if isinstance(created, (str, bytes)):
        raise TypeError("Factory must return an iterable of tool objects, not a string.")
    return tuple(created)


def _load_factory_assignment_map(assignments: list[str]) -> dict[str, Any]:
    resolved: dict[str, Any] = {}
    for assignment in assignments:
        family, spec = split_assignment(assignment)
        resolved[family.strip().lower()] = load_factory(spec)()
    return resolved


def _read_json_object(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return {}
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object in '{path.name}'.")
    return dict(payload)


def _optional_string(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def _result_payload(result: Any) -> dict[str, Any]:
    return {
        "cycles_completed": getattr(result, "cycles_completed", None),
        "pause_reason": getattr(result, "pause_reason", None),
        "resets": getattr(result, "resets", None),
        "status": getattr(result, "status", None),
    }


def _linkedin_store(memory_path: Path) -> LinkedInMemoryStore:
    return LinkedInMemoryStore(memory_path=memory_path)


def _instagram_store(memory_path: Path) -> InstagramMemoryStore:
    return InstagramMemoryStore(memory_path=memory_path)


def _prospecting_store(memory_path: Path) -> ProspectingMemoryStore:
    return ProspectingMemoryStore(memory_path=memory_path)


def _leads_store(memory_path: Path) -> LeadsMemoryStore:
    return LeadsMemoryStore(memory_path=memory_path)


def _knowt_store(memory_path: Path) -> KnowtMemoryStore:
    return KnowtMemoryStore(memory_path=memory_path)


def _exa_store(memory_path: Path) -> ExaOutreachMemoryStore:
    return ExaOutreachMemoryStore(memory_path=memory_path)


__all__ = [
    "BaseHarnessCliAdapter",
    "ExaOutreachHarnessCliAdapter",
    "HarnessAdapterContext",
    "HarnessCliAdapter",
    "InstagramHarnessCliAdapter",
    "KnowtHarnessCliAdapter",
    "LeadsHarnessCliAdapter",
    "LinkedInHarnessCliAdapter",
    "ProspectingHarnessCliAdapter",
]
