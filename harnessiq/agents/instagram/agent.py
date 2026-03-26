"""Instagram keyword discovery agent harness."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from harnessiq.agents.base import BaseAgent
from harnessiq.shared.agents import (
    DEFAULT_AGENT_MAX_TOKENS,
    DEFAULT_AGENT_RESET_THRESHOLD,
    AgentModel,
    AgentModelResponse,
    AgentParameterSection,
    AgentPauseSignal,
    AgentRunResult,
    AgentRuntimeConfig,
    AgentTranscriptEntry,
    json_parameter_section,
    merge_agent_runtime_config,
)
from harnessiq.shared.instagram import (
    DEFAULT_AGENT_IDENTITY,
    DEFAULT_RECENT_RESULT_WINDOW,
    DEFAULT_RECENT_SEARCH_WINDOW,
    DEFAULT_SEARCH_RESULT_LIMIT,
    InstagramICP,
    InstagramKeywordAgentConfig,
    InstagramMemoryStore,
    InstagramRunState,
    InstagramSearchBackend,
    normalize_instagram_custom_parameters,
    resolve_instagram_icp_profiles,
)
from harnessiq.shared.tools import INSTAGRAM_SEARCH_KEYWORD, RegisteredTool, ToolCall, ToolResult
from harnessiq.toolset import get_tool
from harnessiq.tools.instagram import create_instagram_tools
from harnessiq.tools.registry import create_tool_registry
from harnessiq.utils.ledger import new_run_id

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
        custom_parameters: Mapping[str, Any] | None = None,
        persist_icp_descriptions: bool = True,
        tools: Sequence[RegisteredTool] | None = None,
        runtime_config: AgentRuntimeConfig | None = None,
    ) -> None:
        if search_backend is None:
            raise ValueError("InstagramKeywordDiscoveryAgent requires a search_backend.")

        self._candidate_memory_path = Path(memory_path) if memory_path is not None else None
        normalized_icps = _normalize_icp_descriptions(icp_descriptions)
        self._search_backend = search_backend
        self._initial_icp_descriptions = normalized_icps
        self._custom_parameters = dict(custom_parameters or {})
        self._persist_icp_descriptions = persist_icp_descriptions
        self._payload_max_tokens = max_tokens
        self._payload_reset_threshold = reset_threshold
        self._payload_recent_search_window = recent_search_window
        self._payload_recent_result_window = recent_result_window
        self._payload_search_result_limit = search_result_limit
        self._run_id: str | None = None
        self._active_icp_index = 0
        self._icps: tuple[InstagramICP, ...] = tuple(InstagramICP(description=value) for value in normalized_icps)

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
        self._attempted_search_keywords: list[str] = []

        bound_search_tool = create_instagram_tools(
            memory_store=self._memory_store,
            search_backend=self._search_backend,
            search_result_limit=search_result_limit,
            current_icp_key=self._current_icp_key,
        )[0]
        search_tool_definition = get_tool(INSTAGRAM_SEARCH_KEYWORD).definition
        tool_registry = create_tool_registry(
            (
                RegisteredTool(
                    definition=search_tool_definition,
                    handler=bound_search_tool.handler,
                ),
            ),
            tuple(tools or ()),
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
        custom_overrides: Mapping[str, Any] | None = None,
        tools: Sequence[RegisteredTool] | None = None,
        runtime_config: AgentRuntimeConfig | None = None,
    ) -> "InstagramKeywordDiscoveryAgent":
        resolved_path = _resolve_memory_path(memory_path)
        store = InstagramMemoryStore(memory_path=resolved_path)
        store.prepare()
        runtime_parameters = store.read_runtime_parameters()
        if runtime_overrides:
            runtime_parameters.update(runtime_overrides)
        custom_parameters = store.read_custom_parameters()
        if custom_overrides:
            custom_parameters.update(custom_overrides)
        from harnessiq.shared.instagram import normalize_instagram_runtime_parameters

        normalized = normalize_instagram_runtime_parameters(runtime_parameters)
        normalized_custom = normalize_instagram_custom_parameters(custom_parameters)
        return cls(
            model=model,
            search_backend=search_backend,
            memory_path=resolved_path,
            icp_descriptions=resolve_instagram_icp_profiles(store.read_icp_profiles(), normalized_custom),
            custom_parameters=normalized_custom,
            persist_icp_descriptions=False,
            tools=tools,
            runtime_config=runtime_config,
            **normalized,
        )

    def prepare(self) -> None:
        self._memory_store.prepare()
        if self._persist_icp_descriptions and self._initial_icp_descriptions:
            self._memory_store.write_icp_profiles(self._initial_icp_descriptions)
        self._icps = self._memory_store.initialize_icp_states(self._initial_icp_descriptions)
        if not self._icps:
            return

        existing_state = self._read_existing_run_state()
        if existing_state is not None and existing_state.status != "completed":
            self._run_id = existing_state.run_id
            self._active_icp_index = min(existing_state.active_icp_index, len(self._icps) - 1)
            self._memory_store.write_run_state(
                InstagramRunState(
                    run_id=existing_state.run_id,
                    active_icp_index=self._active_icp_index,
                    status="running",
                    started_at=existing_state.started_at or _utcnow(),
                    completed_at=None,
                )
            )
            return

        self._reset_icp_statuses_for_new_run()
        self._run_id = new_run_id()
        self._active_icp_index = 0
        self._memory_store.write_run_state(
            InstagramRunState(
                run_id=self._run_id,
                active_icp_index=0,
                status="running",
                started_at=_utcnow(),
                completed_at=None,
            )
        )

    def run(self, *, max_cycles: int | None = None) -> AgentRunResult:
        self._attempted_search_keywords.clear()
        try:
            if not self._initial_icp_descriptions:
                return super().run(max_cycles=max_cycles)
            return self._trace_run(lambda: self._run_instagram_loop(max_cycles=max_cycles))
        finally:
            self.close()

    def build_system_prompt(self) -> str:
        if not _MASTER_PROMPT_PATH.exists():
            raise FileNotFoundError(
                f"Instagram master prompt not found at '{_MASTER_PROMPT_PATH}'. "
                "Ensure the prompt file exists."
            )
        prompt = _MASTER_PROMPT_PATH.read_text(encoding="utf-8").strip()
        identity = (
            self._memory_store.read_agent_identity()
            if self._memory_store.agent_identity_path.exists()
            else DEFAULT_AGENT_IDENTITY
        ).strip()
        parts = [part for part in (identity, prompt) if part]
        additional_prompt = (
            self._memory_store.read_additional_prompt()
            if self._memory_store.additional_prompt_path.exists()
            else ""
        ).strip()
        if additional_prompt:
            parts.append(additional_prompt)
        return "\n\n".join(parts)

    def load_parameter_sections(self) -> Sequence[AgentParameterSection]:
        recent_searches = ", ".join(self._recent_search_keywords_for_context())
        sections: list[AgentParameterSection] = [
            AgentParameterSection(title="Active ICP", content=self._current_icp_description()),
            json_parameter_section(
                "Run Progress",
                {
                    "active_icp_index": self._active_icp_index,
                    "icp_count": len(self._icps),
                    "icp_position": self._active_icp_index + 1 if self._icps else 0,
                    "remaining_icps": max(len(self._icps) - self._active_icp_index - 1, 0) if self._icps else 0,
                    "run_id": self._run_id,
                },
            ),
            AgentParameterSection(title="Recent Searches", content=recent_searches),
        ]
        prompt_custom_parameters = {
            key: value for key, value in self._custom_parameters.items() if key != "icp_profiles"
        }
        if prompt_custom_parameters:
            sections.append(json_parameter_section("Custom Parameters", prompt_custom_parameters))
        return tuple(sections)

    def build_instance_payload(self) -> dict[str, Any]:
        return _build_instagram_instance_payload(
            memory_path=self._candidate_memory_path,
            icp_descriptions=self._initial_icp_descriptions,
            max_tokens=self._payload_max_tokens,
            reset_threshold=self._payload_reset_threshold,
            recent_search_window=self._payload_recent_search_window,
            recent_result_window=self._payload_recent_result_window,
            search_result_limit=self._payload_search_result_limit,
            custom_parameters=self._custom_parameters,
        )

    def get_emails(self) -> tuple[str, ...]:
        return tuple(self._memory_store.get_emails())

    def get_leads(self) -> tuple[Any, ...]:
        return tuple(self._memory_store.get_leads())

    def get_search_history(self) -> tuple[Any, ...]:
        return tuple(self._memory_store.read_search_history())

    def build_ledger_outputs(self) -> dict[str, Any]:
        return {
            "emails": list(self.get_emails()),
            "leads": [record.as_dict() for record in self.get_leads()],
            "search_history": [record.as_dict() for record in self.get_search_history()],
        }

    def close(self) -> None:
        close_backend = getattr(self._search_backend, "close", None)
        if callable(close_backend):
            close_backend()

    def _run_instagram_loop(self, *, max_cycles: int | None = None) -> AgentRunResult:
        self.prepare()
        self._reset_count = 0
        self._cycle_index = 0
        self._transcript.clear()
        self.refresh_parameters()
        self._last_run_id = new_run_id()
        started_at = datetime.now(timezone.utc)
        total_estimated_request_tokens = 0

        before_run_pause = self._apply_before_run_hooks()
        if before_run_pause is not None:
            self._persist_run_state(status="running", active_icp_index=self._active_icp_index)
            return self._complete_run(
                AgentRunResult(
                    status="paused",
                    cycles_completed=0,
                    resets=self._reset_count,
                    pause_reason=before_run_pause.reason,
                ),
                started_at=started_at,
                total_estimated_request_tokens=total_estimated_request_tokens,
            )

        cycles_completed = 0
        try:
            for icp_index in range(self._active_icp_index, len(self._icps)):
                self._activate_icp(icp_index)
                self._transcript.clear()
                self.refresh_parameters()

                while max_cycles is None or cycles_completed < max_cycles:
                    self._cycle_index = cycles_completed + 1
                    request = self.build_model_request()
                    total_estimated_request_tokens += request.estimated_tokens()
                    response = self._model.generate_turn(request)
                    cycles_completed += 1
                    self._record_assistant_response(response)

                    if response.pause_reason is not None:
                        self._persist_run_state(status="running", active_icp_index=icp_index)
                        return self._complete_run(
                            AgentRunResult(
                                status="paused",
                                cycles_completed=cycles_completed,
                                resets=self._reset_count,
                                pause_reason=response.pause_reason,
                            ),
                            started_at=started_at,
                            total_estimated_request_tokens=total_estimated_request_tokens,
                        )

                    pause_signal: AgentPauseSignal | None = None
                    for requested_tool_call in response.tool_calls:
                        tool_call, result, pause_signal = self._prepare_tool_call(requested_tool_call)
                        if pause_signal is not None:
                            break
                        assert tool_call is not None  # noqa: S101
                        if result is None:
                            result = self._execute_tool(tool_call)
                        result, hook_pause_signal = self._finalize_tool_result(tool_call, result)
                        if self._apply_compaction_result(result):
                            if hook_pause_signal is not None:
                                pause_signal = hook_pause_signal
                                break
                            continue
                        self._record_tool_result(result)
                        if hook_pause_signal is not None:
                            pause_signal = hook_pause_signal
                            break
                        if isinstance(result.output, AgentPauseSignal):
                            pause_signal = result.output
                            break

                    if pause_signal is not None:
                        self._persist_run_state(status="running", active_icp_index=icp_index)
                        return self._complete_run(
                            AgentRunResult(
                                status="paused",
                                cycles_completed=cycles_completed,
                                resets=self._reset_count,
                                pause_reason=pause_signal.reason,
                            ),
                            started_at=started_at,
                            total_estimated_request_tokens=total_estimated_request_tokens,
                        )

                    if not response.should_continue:
                        self._complete_icp(icp_index)
                        break

                    if self._should_prune_context():
                        self.reset_context()
                    if self._should_reset_context():
                        self.reset_context()
                else:
                    self._persist_run_state(status="running", active_icp_index=icp_index)
                    return self._complete_run(
                        AgentRunResult(
                            status="max_cycles_reached",
                            cycles_completed=cycles_completed,
                            resets=self._reset_count,
                        ),
                        started_at=started_at,
                        total_estimated_request_tokens=total_estimated_request_tokens,
                    )
        except Exception as exc:
            self._emit_ledger_entry(
                started_at=started_at,
                finished_at=datetime.now(timezone.utc),
                status="error",
                cycles_completed=cycles_completed,
                total_estimated_request_tokens=total_estimated_request_tokens,
                pause_reason=None,
                error=exc,
            )
            raise

        completed_at = _utcnow()
        existing_state = self._read_existing_run_state()
        self._memory_store.write_run_state(
            InstagramRunState(
                run_id=self._run_id or new_run_id(),
                active_icp_index=max(len(self._icps) - 1, 0),
                status="completed",
                started_at=existing_state.started_at if existing_state is not None else completed_at,
                completed_at=completed_at,
            )
        )
        return self._complete_run(
            AgentRunResult(
                status="completed",
                cycles_completed=cycles_completed,
                resets=self._reset_count,
            ),
            started_at=started_at,
            total_estimated_request_tokens=total_estimated_request_tokens,
        )

    def _execute_tool(self, tool_call: ToolCall) -> ToolResult:
        if tool_call.tool_key == INSTAGRAM_SEARCH_KEYWORD:
            self._remember_attempted_search_keyword(tool_call.arguments.get("keyword"))
        result = super()._execute_tool(tool_call)
        if tool_call.tool_key == INSTAGRAM_SEARCH_KEYWORD:
            self.refresh_parameters()
        return result

    def _record_assistant_response(self, response: AgentModelResponse) -> None:
        parts: list[str] = []
        if response.assistant_message.strip():
            parts.append(response.assistant_message.strip())
        if response.pause_reason:
            parts.append(f"Pause requested: {response.pause_reason}")

        if parts and (response.pause_reason is not None or not _is_search_only_response(response)):
            self._transcript.append(
                AgentTranscriptEntry(
                    entry_type="assistant",
                    content="\n".join(parts),
                    role="assistant",
                )
            )

        for tool_call in response.tool_calls:
            if tool_call.tool_key == INSTAGRAM_SEARCH_KEYWORD:
                continue
            arguments = json.dumps(tool_call.arguments, sort_keys=True)
            self._transcript.append(
                AgentTranscriptEntry(
                    entry_type="tool_call",
                    content=f"{tool_call.tool_key}\n{arguments}",
                    tool_key=tool_call.tool_key,
                    arguments=dict(tool_call.arguments),
                )
            )

    def _record_tool_result(self, result: ToolResult) -> None:
        if result.tool_key == INSTAGRAM_SEARCH_KEYWORD:
            return
        super()._record_tool_result(result)

    def _recent_search_keywords_for_context(self) -> tuple[str, ...]:
        active_icp = self._current_icp()
        durable_keywords = [
            record.keyword
            for record in self._memory_store.read_recent_searches(
                self._config.recent_search_window,
                icp_key=active_icp.key if active_icp is not None else None,
            )
            if record.keyword
        ]
        return _merge_recent_keywords(
            durable_keywords,
            self._attempted_search_keywords,
            limit=self._config.recent_search_window,
        )

    def _remember_attempted_search_keyword(self, raw_keyword: Any) -> None:
        if not isinstance(raw_keyword, str):
            return
        cleaned = raw_keyword.strip()
        if not cleaned:
            return
        if any(keyword.lower() == cleaned.lower() for keyword in self._attempted_search_keywords):
            return
        self._attempted_search_keywords.append(cleaned)
        if len(self._attempted_search_keywords) > self._config.recent_search_window:
            self._attempted_search_keywords = self._attempted_search_keywords[
                -self._config.recent_search_window :
            ]

    def _activate_icp(self, icp_index: int) -> None:
        self._active_icp_index = icp_index
        self._attempted_search_keywords.clear()
        state = self._memory_store.read_icp_state(self._icps[icp_index].key)
        state.status = "active"
        state.completed_at = None
        self._memory_store.write_icp_state(state)
        self._persist_run_state(status="running", active_icp_index=icp_index)

    def _complete_icp(self, icp_index: int) -> None:
        state = self._memory_store.read_icp_state(self._icps[icp_index].key)
        state.status = "completed"
        state.completed_at = _utcnow()
        self._memory_store.write_icp_state(state)
        self._persist_run_state(
            status="running" if icp_index < len(self._icps) - 1 else "completed",
            active_icp_index=min(icp_index + 1, len(self._icps) - 1),
        )

    def _persist_run_state(self, *, status: str, active_icp_index: int) -> None:
        existing = self._read_existing_run_state()
        self._memory_store.write_run_state(
            InstagramRunState(
                run_id=self._run_id or (existing.run_id if existing is not None else new_run_id()),
                active_icp_index=active_icp_index,
                status=status,
                started_at=existing.started_at if existing is not None else _utcnow(),
                completed_at=existing.completed_at if status == "completed" and existing is not None else None,
            )
        )

    def _reset_icp_statuses_for_new_run(self) -> None:
        for icp in self._icps:
            state = self._memory_store.read_icp_state(icp.key)
            state.status = "pending"
            state.completed_at = None
            self._memory_store.write_icp_state(state)

    def _read_existing_run_state(self) -> InstagramRunState | None:
        if not self._memory_store.run_state_path.exists():
            return None
        return self._memory_store.read_run_state()

    def _current_icp(self) -> InstagramICP | None:
        if not self._icps:
            return None
        return self._icps[self._active_icp_index]

    def _current_icp_key(self) -> str:
        icp = self._current_icp()
        return icp.key if icp is not None else ""

    def _current_icp_description(self) -> str:
        icp = self._current_icp()
        return icp.description if icp is not None else ""


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


def _is_search_only_response(response: AgentModelResponse) -> bool:
    return bool(response.tool_calls) and all(
        tool_call.tool_key == INSTAGRAM_SEARCH_KEYWORD for tool_call in response.tool_calls
    )


def _merge_recent_keywords(
    *keyword_groups: Iterable[str],
    limit: int,
) -> tuple[str, ...]:
    merged: list[str] = []
    seen: set[str] = set()
    for group in keyword_groups:
        for keyword in group:
            cleaned = str(keyword).strip()
            if not cleaned:
                continue
            normalized = cleaned.lower()
            if normalized in seen:
                continue
            seen.add(normalized)
            merged.append(cleaned)
    if limit <= 0:
        return tuple(merged)
    return tuple(merged[-limit:])


def _build_instagram_instance_payload(
    *,
    memory_path: Path | None,
    icp_descriptions: tuple[str, ...],
    max_tokens: int,
    reset_threshold: float,
    recent_search_window: int,
    recent_result_window: int,
    search_result_limit: int,
    custom_parameters: Mapping[str, Any] | None = None,
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
    if custom_parameters:
        payload["custom_parameters"] = dict(custom_parameters)
    if memory_path is not None:
        payload["memory_path"] = str(memory_path)
    if memory_path is None or not memory_path.exists():
        return payload

    store = InstagramMemoryStore(memory_path=memory_path)
    resolved_custom_parameters = (
        dict(custom_parameters) if custom_parameters is not None else store.read_custom_parameters()
    )
    payload["icp_descriptions"] = resolve_instagram_icp_profiles(
        store.read_icp_profiles(),
        resolved_custom_parameters,
    )
    payload["agent_identity"] = _read_optional_text(store.agent_identity_path)
    payload["additional_prompt"] = _read_optional_text(store.additional_prompt_path)
    if resolved_custom_parameters:
        payload["custom_parameters"] = resolved_custom_parameters
    if store.run_state_path.exists():
        payload["run_state"] = store.read_run_state().as_dict()
    icp_states = store.list_icp_states(current_only=True, custom_parameters=resolved_custom_parameters)
    if icp_states:
        payload["icp_progress"] = [
            {
                "completed_at": state.completed_at,
                "icp": state.icp.as_dict(),
                "search_count": len(state.searches),
                "status": state.status,
            }
            for state in icp_states
        ]
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


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


__all__ = [
    "InstagramKeywordAgentConfig",
    "InstagramKeywordDiscoveryAgent",
    "InstagramMemoryStore",
]
