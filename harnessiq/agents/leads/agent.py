"""Multi-ICP leads discovery agent harness."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from harnessiq.agents.base import BaseAgent
from harnessiq.agents.leads.helpers import (
    build_leads_instance_payload as _build_leads_instance_payload,
    render_search_history as _render_search_history,
    timestamped_run_id as _timestamped_run_id,
    total_searches_for_state as _total_searches_for_state,
    utc_now_z as _utcnow,
)
from harnessiq.shared.agents import (
    DEFAULT_AGENT_MAX_TOKENS,
    DEFAULT_AGENT_RESET_THRESHOLD,
    AgentModel,
    AgentParameterSection,
    AgentPauseSignal,
    AgentRunResult,
    AgentRuntimeConfig,
    json_parameter_section,
    merge_agent_runtime_config,
)
from harnessiq.shared.exceptions import ResourceNotFoundError
from harnessiq.shared.leads import (
    DEFAULT_LEADS_SEARCH_SUMMARY_EVERY,
    DEFAULT_LEADS_SEARCH_TAIL_SIZE,
    LeadICP,
    LeadICPState,
    LeadsAgentConfig,
    LeadRunState,
    LeadsMemoryStore,
    LeadsStorageBackend,
)
from harnessiq.shared.tools import (
    LEADS_CHECK_SEEN,
    LEADS_COMPACT_SEARCH_HISTORY,
    LEADS_LOG_SEARCH,
    LEADS_SAVE_LEADS,
    RegisteredTool,
)
from harnessiq.tools.leads import create_leads_tools
from harnessiq.tools.registry import create_tool_registry
from harnessiq.utils.ledger import new_run_id

_PROMPTS_DIR = Path(__file__).parent / "prompts"
_MASTER_PROMPT_PATH = _PROMPTS_DIR / "master_prompt.md"
_DEFAULT_MEMORY_PATH = Path(__file__).parent / "memory"


class LeadsAgent(BaseAgent):
    """Concrete leads harness that rotates one agent instance across multiple ICPs."""

    def __init__(
        self,
        *,
        model: AgentModel,
        company_background: str,
        icps: Iterable[LeadICP | dict[str, Any] | str],
        platforms: Sequence[str],
        memory_path: str | Path | None = None,
        storage_backend: LeadsStorageBackend | None = None,
        max_tokens: int = DEFAULT_AGENT_MAX_TOKENS,
        reset_threshold: float = DEFAULT_AGENT_RESET_THRESHOLD,
        prune_search_interval: int | None = None,
        prune_token_limit: int | None = None,
        search_summary_every: int = DEFAULT_LEADS_SEARCH_SUMMARY_EVERY,
        search_tail_size: int = DEFAULT_LEADS_SEARCH_TAIL_SIZE,
        max_leads_per_icp: int | None = None,
        provider_credentials: Mapping[str, Any] | None = None,
        provider_clients: Mapping[str, Any] | None = None,
        allowed_provider_operations: Mapping[str, Sequence[str] | None] | None = None,
        tools: Sequence[RegisteredTool] | None = None,
        runtime_config: AgentRuntimeConfig | None = None,
    ) -> None:
        self._config = LeadsAgentConfig.from_inputs(
            company_background=company_background,
            icps=icps,
            platforms=platforms,
            memory_path=memory_path if memory_path is not None else _DEFAULT_MEMORY_PATH,
            storage_backend=storage_backend,
            max_tokens=max_tokens,
            reset_threshold=reset_threshold,
            prune_search_interval=prune_search_interval,
            prune_token_limit=prune_token_limit,
            search_summary_every=search_summary_every,
            search_tail_size=search_tail_size,
            max_leads_per_icp=max_leads_per_icp,
        )
        self._memory_store = LeadsMemoryStore(memory_path=self._config.memory_path)
        self._run_id: str | None = None
        self._active_icp_index = 0

        tool_registry = create_tool_registry(
            create_leads_tools(
                config=self._config,
                memory_store=self._memory_store,
                current_icp=self._current_icp,
                current_run_id=lambda: self._run_id,
                refresh_parameters=self.refresh_parameters,
                provider_tools=tools,
                provider_credentials=provider_credentials,
                provider_clients=provider_clients,
                allowed_provider_operations=allowed_provider_operations,
            )
        )
        super().__init__(
            name="leads_agent",
            model=model,
            tool_executor=tool_registry,
            runtime_config=merge_agent_runtime_config(
                runtime_config,
                max_tokens=self._config.max_tokens,
                reset_threshold=self._config.reset_threshold,
                prune_progress_interval=self._config.prune_search_interval,
                prune_token_limit=self._config.prune_token_limit,
            ),
            memory_path=self._config.memory_path,
        )

    @property
    def config(self) -> LeadsAgentConfig:
        return self._config

    @property
    def memory_store(self) -> LeadsMemoryStore:
        return self._memory_store

    def build_instance_payload(self) -> dict[str, Any]:
        return _build_leads_instance_payload(config=self._config)

    def prepare(self) -> None:
        self._memory_store.prepare()
        self._memory_store.write_run_config(self._config.run_config)
        self._memory_store.initialize_icp_states(self._config.run_config.icps)

        existing_state = self._read_existing_run_state()
        if existing_state is not None and existing_state.status != "completed":
            self._run_id = existing_state.run_id
            self._active_icp_index = min(existing_state.active_icp_index, len(self._config.run_config.icps) - 1)
            self._memory_store.write_run_state(
                LeadRunState(
                    run_id=existing_state.run_id,
                    active_icp_index=self._active_icp_index,
                    status="running",
                    started_at=existing_state.started_at or _utcnow(),
                    completed_at=None,
                )
            )
            return

        self._reset_icp_statuses_for_new_run()
        self._run_id = _timestamped_run_id()
        self._active_icp_index = 0
        self._config.storage_backend.start_run(self._run_id, self._config.run_config.as_dict())
        self._memory_store.write_run_state(
            LeadRunState(
                run_id=self._run_id,
                active_icp_index=0,
                status="running",
                started_at=_utcnow(),
                completed_at=None,
            )
        )

    def build_system_prompt(self) -> str:
        if not _MASTER_PROMPT_PATH.exists():
            raise ResourceNotFoundError(
                f"Leads master prompt not found at '{_MASTER_PROMPT_PATH}'. "
                "Ensure harnessiq/agents/leads/prompts/master_prompt.md exists."
            )
        template = _MASTER_PROMPT_PATH.read_text(encoding="utf-8")
        tool_lines = "\n".join(f"- {tool.name}: {tool.description}" for tool in self.available_tools())
        return (
            template.replace("{{TOOL_LIST}}", tool_lines)
            .replace("{{PLATFORMS}}", ", ".join(self._config.run_config.platforms))
            .replace("{{SEARCH_SUMMARY_EVERY}}", str(self._config.run_config.search_summary_every))
            .replace("{{SEARCH_TAIL_SIZE}}", str(self._config.run_config.search_tail_size))
        )

    def load_parameter_sections(self) -> Sequence[AgentParameterSection]:
        icp = self._current_icp()
        icp_state = self._current_icp_state()
        run_state = self._memory_store.read_run_state()
        summaries, recent_searches = self._memory_store.read_search_context(
            icp.key,
            tail_size=self._config.run_config.search_tail_size,
        )
        return (
            AgentParameterSection(title="Company Background", content=self._config.run_config.company_background),
            json_parameter_section("Active ICP", icp.as_dict()),
            json_parameter_section(
                "Run Progress",
                {
                    "run_id": run_state.run_id,
                    "active_icp_index": self._active_icp_index,
                    "icp_position": self._active_icp_index + 1,
                    "icp_count": len(self._config.run_config.icps),
                    "platforms": list(self._config.run_config.platforms),
                    "searches_attempted_for_icp": _total_searches_for_state(icp_state),
                    "saved_leads_for_icp": len(icp_state.saved_lead_keys),
                    "max_leads_per_icp": self._config.run_config.max_leads_per_icp,
                },
            ),
            AgentParameterSection(
                title="Search History",
                content=_render_search_history(summaries, recent_searches),
            ),
            json_parameter_section(
                "Saved Leads (Current ICP)",
                {
                    "count": len(icp_state.saved_lead_keys),
                    "dedupe_keys_tail": icp_state.saved_lead_keys[-10:],
                },
            ),
        )

    def pruning_progress_value(self) -> int:
        total = 0
        for icp in self._config.run_config.icps:
            total += _total_searches_for_state(self._memory_store.read_icp_state(icp.key))
        return total

    def run(self, *, max_cycles: int | None = None) -> AgentRunResult:
        return self._trace_run(lambda: self._run_leads_loop(max_cycles=max_cycles))

    def _run_leads_loop(self, *, max_cycles: int | None = None) -> AgentRunResult:
        self.prepare()
        self._reset_count = 0
        self._cycle_index = 0
        self._transcript.clear()
        self.refresh_parameters()
        self._last_run_id = new_run_id()
        started_at = datetime.now(timezone.utc)
        total_estimated_request_tokens = 0
        self._last_prune_progress = self.pruning_progress_value()
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
            for icp_index in range(self._active_icp_index, len(self._config.run_config.icps)):
                self._activate_icp(icp_index)
                self._transcript.clear()
                self.refresh_parameters()
                self._last_prune_progress = self.pruning_progress_value()

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
                        self._last_prune_progress = self.pruning_progress_value()

                    if self._should_reset_context():
                        self.reset_context()
                        self._last_prune_progress = self.pruning_progress_value()
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
        if self._run_id is not None:
            self._config.storage_backend.finish_run(self._run_id, completed_at)
        existing = self._read_existing_run_state()
        self._memory_store.write_run_state(
            LeadRunState(
                run_id=self._run_id or _timestamped_run_id(),
                active_icp_index=len(self._config.run_config.icps) - 1,
                status="completed",
                started_at=existing.started_at if existing is not None else completed_at,
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

    def _activate_icp(self, icp_index: int) -> None:
        self._active_icp_index = icp_index
        state = self._memory_store.read_icp_state(self._config.run_config.icps[icp_index].key)
        state.status = "active"
        state.completed_at = None
        self._memory_store.write_icp_state(state)
        self._persist_run_state(status="running", active_icp_index=icp_index)

    def _complete_icp(self, icp_index: int) -> None:
        state = self._memory_store.read_icp_state(self._config.run_config.icps[icp_index].key)
        state.status = "completed"
        state.completed_at = _utcnow()
        self._memory_store.write_icp_state(state)
        self._persist_run_state(
            status="running" if icp_index < len(self._config.run_config.icps) - 1 else "completed",
            active_icp_index=min(icp_index + 1, len(self._config.run_config.icps) - 1),
        )

    def _persist_run_state(self, *, status: str, active_icp_index: int) -> None:
        existing = self._read_existing_run_state()
        self._memory_store.write_run_state(
            LeadRunState(
                run_id=self._run_id or (existing.run_id if existing is not None else _timestamped_run_id()),
                active_icp_index=active_icp_index,
                status=status,
                started_at=existing.started_at if existing is not None else _utcnow(),
                completed_at=existing.completed_at if status == "completed" and existing is not None else None,
            )
        )

    def _reset_icp_statuses_for_new_run(self) -> None:
        for icp in self._config.run_config.icps:
            state = self._memory_store.read_icp_state(icp.key)
            state.status = "pending"
            state.completed_at = None
            self._memory_store.write_icp_state(state)

    def _read_existing_run_state(self) -> LeadRunState | None:
        if not self._memory_store.run_state_path.exists():
            return None
        return self._memory_store.read_run_state()

    def _current_icp(self) -> LeadICP:
        return self._config.run_config.icps[self._active_icp_index]

    def _current_icp_state(self) -> LeadICPState:
        return self._memory_store.read_icp_state(self._current_icp().key)
__all__ = [
    "LEADS_CHECK_SEEN",
    "LEADS_COMPACT_SEARCH_HISTORY",
    "LEADS_LOG_SEARCH",
    "LEADS_SAVE_LEADS",
    "LeadsAgent",
    "LeadsAgentConfig",
]
