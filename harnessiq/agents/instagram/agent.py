"""Instagram keyword discovery agent harness."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from harnessiq.agents.base import BaseAgent
from harnessiq.shared.agents import (
    DEFAULT_AGENT_MAX_TOKENS,
    DEFAULT_AGENT_RESET_THRESHOLD,
    AgentModel,
    AgentParameterSection,
    AgentRuntimeConfig,
    merge_agent_runtime_config,
)
from harnessiq.shared.instagram import (
    DEFAULT_AGENT_IDENTITY,
    DEFAULT_RECENT_RESULT_WINDOW,
    DEFAULT_RECENT_SEARCH_WINDOW,
    DEFAULT_SEARCH_RESULT_LIMIT,
    InstagramKeywordAgentConfig,
    InstagramMemoryStore,
    InstagramSearchBackend,
)
from harnessiq.shared.tools import INSTAGRAM_SEARCH_KEYWORD, RegisteredTool, ToolCall, ToolResult
from harnessiq.toolset import get_tool
from harnessiq.tools.instagram import create_instagram_tools
from harnessiq.tools.registry import ToolRegistry

_PROMPTS_DIR = Path(__file__).parent / "prompts"
_MASTER_PROMPT_PATH = _PROMPTS_DIR / "master_prompt.md"
_DEFAULT_MEMORY_PATH = Path(__file__).parent / "memory"


class InstagramKeywordDiscoveryAgent(BaseAgent):
    """Concrete harness for ICP-driven Instagram keyword discovery."""

    def __init__(
        self,
        *,
        model: AgentModel,
        icp_descriptions: Iterable[str] = (),
        search_backend: InstagramSearchBackend,
        memory_path: str | Path | None = None,
        max_tokens: int = DEFAULT_AGENT_MAX_TOKENS,
        reset_threshold: float = DEFAULT_AGENT_RESET_THRESHOLD,
        recent_search_window: int = DEFAULT_RECENT_SEARCH_WINDOW,
        recent_result_window: int = DEFAULT_RECENT_RESULT_WINDOW,
        search_result_limit: int = DEFAULT_SEARCH_RESULT_LIMIT,
        runtime_config: AgentRuntimeConfig | None = None,
    ) -> None:
        if search_backend is None:
            raise ValueError("InstagramKeywordDiscoveryAgent requires a search_backend.")

        # Store all params needed by build_instance_payload() before calling super().__init__().
        self._candidate_memory_path = Path(memory_path) if memory_path is not None else None
        normalized_icps = _normalize_icp_descriptions(icp_descriptions)
        self._search_backend = search_backend
        self._initial_icp_descriptions = normalized_icps
        self._payload_max_tokens = max_tokens
        self._payload_reset_threshold = reset_threshold
        self._payload_recent_search_window = recent_search_window
        self._payload_recent_result_window = recent_result_window
        self._payload_search_result_limit = search_result_limit

        candidate_memory_path = self._candidate_memory_path
        resolved_memory_path = candidate_memory_path or _DEFAULT_MEMORY_PATH
        self._memory_store = InstagramMemoryStore(memory_path=resolved_memory_path)
        self._config = InstagramKeywordAgentConfig(
            memory_path=resolved_memory_path,
            max_tokens=max_tokens,
            reset_threshold=reset_threshold,
            recent_search_window=recent_search_window,
            recent_result_window=recent_result_window,
            search_result_limit=search_result_limit,
        )

        bound_search_tool = create_instagram_tools(
            memory_store=self._memory_store,
            search_backend=self._search_backend,
            search_result_limit=search_result_limit,
        )[0]
        search_tool_definition = get_tool(INSTAGRAM_SEARCH_KEYWORD).definition
        tool_registry = ToolRegistry(
            (
                RegisteredTool(
                    definition=search_tool_definition,
                    handler=bound_search_tool.handler,
                ),
            )
        )
        base_runtime_config = AgentRuntimeConfig(
            max_tokens=max_tokens,
            reset_threshold=reset_threshold,
        )
        super().__init__(
            name="instagram_keyword_discovery",
            model=model,
            tool_executor=tool_registry,
            runtime_config=merge_agent_runtime_config(
                runtime_config or base_runtime_config,
                max_tokens=max_tokens,
                reset_threshold=reset_threshold,
            ),
            memory_path=candidate_memory_path,
            repo_root=_find_repo_root(candidate_memory_path),
        )

    @property
    def config(self) -> InstagramKeywordAgentConfig:
        return self._config

    @property
    def memory_store(self) -> InstagramMemoryStore:
        return self._memory_store

    @classmethod
    def from_memory(
        cls,
        *,
        model: AgentModel,
        search_backend: InstagramSearchBackend,
        memory_path: str | Path | None = None,
        runtime_overrides: Mapping[str, Any] | None = None,
        runtime_config: AgentRuntimeConfig | None = None,
    ) -> "InstagramKeywordDiscoveryAgent":
        resolved_path = _resolve_memory_path(memory_path)
        store = InstagramMemoryStore(memory_path=resolved_path)
        store.prepare()
        runtime_parameters = store.read_runtime_parameters()
        if runtime_overrides:
            runtime_parameters.update(runtime_overrides)
        from harnessiq.shared.instagram import normalize_instagram_runtime_parameters

        normalized = normalize_instagram_runtime_parameters(runtime_parameters)
        return cls(
            model=model,
            search_backend=search_backend,
            memory_path=resolved_path,
            icp_descriptions=store.read_icp_profiles(),
            runtime_config=runtime_config,
            **normalized,
        )

    def prepare(self) -> None:
        self._memory_store.prepare()
        if self._initial_icp_descriptions:
            self._memory_store.write_icp_profiles(self._initial_icp_descriptions)

    def run(self, *, max_cycles: int | None = None):
        try:
            return super().run(max_cycles=max_cycles)
        finally:
            self.close()

    def build_system_prompt(self) -> str:
        if not _MASTER_PROMPT_PATH.exists():
            raise FileNotFoundError(
                f"Instagram master prompt not found at '{_MASTER_PROMPT_PATH}'. "
                "Ensure the prompt file exists."
            )
        identity = (
            self._memory_store.read_agent_identity()
            if self._memory_store.agent_identity_path.exists()
            else DEFAULT_AGENT_IDENTITY
        )
        prompt = _MASTER_PROMPT_PATH.read_text(encoding="utf-8")
        if identity and identity != DEFAULT_AGENT_IDENTITY:
            prompt = prompt.replace(
                "[IDENTITY]\nYou are InstagramKeywordDiscoveryAgent.",
                f"[IDENTITY]\n{identity}\n\n(You are InstagramKeywordDiscoveryAgent.)",
            )
        additional_prompt = (
            self._memory_store.read_additional_prompt()
            if self._memory_store.additional_prompt_path.exists()
            else ""
        )
        if additional_prompt:
            prompt = f"{prompt}\n\n[ADDITIONAL INSTRUCTIONS]\n{additional_prompt}"
        return prompt

    def load_parameter_sections(self) -> Sequence[AgentParameterSection]:
        icp_profiles = self._memory_store.read_icp_profiles()
        recent_searches = ", ".join(
            record.keyword
            for record in self._memory_store.read_recent_searches(self._config.recent_search_window)
            if record.keyword
        )
        return (
            AgentParameterSection(title="ICP Profiles", content=_json_block(icp_profiles)),
            AgentParameterSection(title="Recent Searches", content=recent_searches),
        )

    def build_instance_payload(self) -> dict[str, Any]:
        return _build_instagram_instance_payload(
            memory_path=self._candidate_memory_path,
            icp_descriptions=self._initial_icp_descriptions,
            max_tokens=self._payload_max_tokens,
            reset_threshold=self._payload_reset_threshold,
            recent_search_window=self._payload_recent_search_window,
            recent_result_window=self._payload_recent_result_window,
            search_result_limit=self._payload_search_result_limit,
        )

    def get_emails(self) -> tuple[str, ...]:
        return tuple(self._memory_store.get_emails())

    def get_leads(self):
        return tuple(self._memory_store.get_leads())

    def get_search_history(self):
        return tuple(self._memory_store.read_search_history())

    def close(self) -> None:
        close_backend = getattr(self._search_backend, "close", None)
        if callable(close_backend):
            close_backend()

    def _execute_tool(self, tool_call: ToolCall) -> ToolResult:
        result = super()._execute_tool(tool_call)
        if tool_call.tool_key == INSTAGRAM_SEARCH_KEYWORD:
            self.refresh_parameters()
        return result


def _resolve_memory_path(memory_path: str | Path | None) -> Path:
    if memory_path is None:
        return _DEFAULT_MEMORY_PATH
    return Path(memory_path)


def _normalize_icp_descriptions(icp_descriptions: Iterable[str]) -> tuple[str, ...]:
    normalized: list[str] = []
    for description in icp_descriptions:
        cleaned = str(description).strip()
        if cleaned:
            normalized.append(cleaned)
    return tuple(normalized)


def _build_instagram_instance_payload(
    *,
    memory_path: Path | None,
    icp_descriptions: tuple[str, ...],
    max_tokens: int,
    reset_threshold: float,
    recent_search_window: int,
    recent_result_window: int,
    search_result_limit: int,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "icp_descriptions": list(icp_descriptions),
        "runtime": {
            "max_tokens": max_tokens,
            "recent_result_window": recent_result_window,
            "recent_search_window": recent_search_window,
            "reset_threshold": reset_threshold,
            "search_result_limit": search_result_limit,
        },
    }
    if memory_path is not None:
        payload["memory_path"] = str(memory_path)
    if memory_path is None or not memory_path.exists():
        return payload

    store = InstagramMemoryStore(memory_path=memory_path)
    payload["icp_descriptions"] = store.read_icp_profiles()
    payload["agent_identity"] = _read_optional_text(store.agent_identity_path)
    payload["additional_prompt"] = _read_optional_text(store.additional_prompt_path)
    return payload


def _read_optional_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8").strip()


def _find_repo_root(path: Path | None) -> Path:
    if path is None:
        return Path.cwd()
    resolved = path.resolve()
    for candidate in (resolved, *resolved.parents):
        if (candidate / ".git").exists():
            return candidate
    if resolved.parent.name == "instagram" and resolved.parent.parent.name == "memory":
        return resolved.parent.parent.parent
    return Path.cwd()


def _json_block(payload: Any) -> str:
    return json.dumps(payload, indent=2, sort_keys=True)


__all__ = [
    "InstagramKeywordAgentConfig",
    "InstagramKeywordDiscoveryAgent",
    "InstagramMemoryStore",
]
