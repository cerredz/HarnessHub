"""Instagram platform CLI adapter."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from harnessiq.agents import AgentModel, AgentRuntimeConfig, InstagramKeywordDiscoveryAgent
from harnessiq.cli.common import load_factory
from harnessiq.shared.dtos import HarnessAdapterResponseDTO, HarnessStatePayloadDTO
from harnessiq.shared.instagram import InstagramMemoryStore, resolve_instagram_icp_profiles

from .base import StoreBackedHarnessCliAdapter
from .context import HarnessAdapterContext
from .utils import load_instagram_store, result_payload, set_env_path_if_missing

_DEFAULT_INSTAGRAM_SEARCH_BACKEND_FACTORY = "harnessiq.integrations.instagram_playwright:create_search_backend"


class InstagramHarnessCliAdapter(StoreBackedHarnessCliAdapter[InstagramMemoryStore]):
    """Adapt the Instagram harness memory layout to the platform-first CLI."""

    store_loader = staticmethod(load_instagram_store)

    def register_run_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--search-backend-factory",
            default=_DEFAULT_INSTAGRAM_SEARCH_BACKEND_FACTORY,
            help=(
                "Import path (module:callable) that returns an Instagram search backend. "
                f"Defaults to {_DEFAULT_INSTAGRAM_SEARCH_BACKEND_FACTORY}."
            ),
        )
        parser.add_argument(
            "--icp",
            action="append",
            default=[],
            help="One ICP description to use for this run. Repeat the flag to provide multiple ICPs.",
        )
        parser.add_argument(
            "--icp-file",
            help="Path to a JSON array or newline-delimited UTF-8 text file containing ICP descriptions for this run.",
        )

    def read_native_runtime_parameters(
        self,
        store: InstagramMemoryStore,
        context: HarnessAdapterContext,
    ) -> dict[str, object]:
        del context
        return store.read_runtime_parameters()

    def read_native_custom_parameters(
        self,
        store: InstagramMemoryStore,
        context: HarnessAdapterContext,
    ) -> dict[str, object]:
        del context
        return store.read_custom_parameters()

    def write_runtime_parameters(self, store: InstagramMemoryStore, context: HarnessAdapterContext) -> None:
        store.write_runtime_parameters(dict(context.profile.runtime_parameters))

    def write_custom_parameters(self, store: InstagramMemoryStore, context: HarnessAdapterContext) -> None:
        store.write_custom_parameters(dict(context.profile.custom_parameters))

    def show(self, context: HarnessAdapterContext) -> HarnessStatePayloadDTO:
        store = self.load_store(context)
        search_history = store.read_search_history()
        lead_database = store.read_lead_database()
        custom_parameters = store.read_custom_parameters()
        run_state = store.read_run_state().as_dict() if store.run_state_path.exists() else None
        return HarnessStatePayloadDTO(
            {
                "additional_prompt": store.read_additional_prompt(),
                "agent_identity": store.read_agent_identity(),
                "custom_parameters": custom_parameters,
                "email_count": len(lead_database.emails),
                "icp_profiles": resolve_instagram_icp_profiles(store.read_icp_profiles(), custom_parameters),
                "lead_count": len(lead_database.leads),
                "recent_searches": [record.as_dict() for record in search_history[-5:]],
                "recent_searches_by_icp": store.read_recent_searches_by_icp(5),
                "run_state": run_state,
                "runtime_parameters": store.read_runtime_parameters(),
                "search_count": len(search_history),
            }
        )

    def run(
        self,
        *,
        args: argparse.Namespace,
        context: HarnessAdapterContext,
        model: AgentModel,
        runtime_config: AgentRuntimeConfig,
    ) -> HarnessAdapterResponseDTO:
        store = self.load_store(context)
        set_env_path_if_missing("HARNESSIQ_INSTAGRAM_SESSION_DIR", store.memory_path / "browser-data")
        search_backend = load_factory(args.search_backend_factory)()
        custom_overrides = dict(context.custom_parameters)
        icp_profiles = _resolve_icp_input(args.icp, args.icp_file)
        if icp_profiles is not None:
            custom_overrides["icp_profiles"] = icp_profiles
        agent = InstagramKeywordDiscoveryAgent.from_memory(
            model=model,
            search_backend=search_backend,
            memory_path=context.memory_path,
            runtime_overrides=context.runtime_parameters,
            custom_overrides=custom_overrides,
            runtime_config=runtime_config,
        )
        result = agent.run(max_cycles=args.max_cycles)
        return HarnessAdapterResponseDTO(
            result=result_payload(result),
            extra={"email_count": len(agent.get_emails())},
        )


def _resolve_icp_input(inline_values: list[str], file_value: str | None) -> list[str] | None:
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


__all__ = ["InstagramHarnessCliAdapter"]
