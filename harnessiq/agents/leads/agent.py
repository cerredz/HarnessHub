"""Multi-ICP leads discovery agent harness."""

from __future__ import annotations

import importlib
import inspect
import json
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from harnessiq.agents.base import BaseAgent
from harnessiq.shared.agents import (
    DEFAULT_AGENT_MAX_TOKENS,
    DEFAULT_AGENT_RESET_THRESHOLD,
    AgentModel,
    AgentParameterSection,
    AgentPauseSignal,
    AgentRunResult,
    AgentRuntimeConfig,
    merge_agent_runtime_config,
)
from harnessiq.shared.leads import (
    FileSystemLeadsStorageBackend,
    LeadICP,
    LeadICPState,
    LeadRecord,
    LeadRunConfig,
    LeadRunState,
    LeadSearchRecord,
    LeadSearchSummary,
    LeadsMemoryStore,
    LeadsStorageBackend,
)
from harnessiq.shared.tools import RegisteredTool, ToolDefinition
from harnessiq.toolset.catalog import PROVIDER_FACTORY_MAP
from harnessiq.tools.registry import ToolRegistry

_PROMPTS_DIR = Path(__file__).parent / "prompts"
_MASTER_PROMPT_PATH = _PROMPTS_DIR / "master_prompt.md"
_DEFAULT_MEMORY_PATH = Path(__file__).parent / "memory"

LEADS_CHECK_SEEN = "leads.check_seen_lead"
LEADS_COMPACT_SEARCH_HISTORY = "leads.compact_search_history"
LEADS_LOG_SEARCH = "leads.log_search"
LEADS_SAVE_LEADS = "leads.save_leads"


@dataclass(frozen=True, slots=True)
class LeadsAgentConfig:
    """Runtime configuration for :class:`LeadsAgent`."""

    run_config: LeadRunConfig
    memory_path: Path
    storage_backend: LeadsStorageBackend
    max_tokens: int = DEFAULT_AGENT_MAX_TOKENS
    reset_threshold: float = DEFAULT_AGENT_RESET_THRESHOLD
    prune_search_interval: int | None = None
    prune_token_limit: int | None = None


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
        search_summary_every: int = 500,
        search_tail_size: int = 20,
        max_leads_per_icp: int | None = None,
        provider_credentials: Mapping[str, Any] | None = None,
        provider_clients: Mapping[str, Any] | None = None,
        allowed_provider_operations: Mapping[str, Sequence[str] | None] | None = None,
        tools: Sequence[RegisteredTool] | None = None,
        runtime_config: AgentRuntimeConfig | None = None,
    ) -> None:
        resolved_memory_path = Path(memory_path) if memory_path is not None else _DEFAULT_MEMORY_PATH
        resolved_icps = _coerce_icps(icps)
        run_config = LeadRunConfig(
            company_background=company_background,
            icps=resolved_icps,
            platforms=tuple(_normalize_platform_name(platform) for platform in platforms),
            search_summary_every=search_summary_every,
            search_tail_size=search_tail_size,
            max_leads_per_icp=max_leads_per_icp,
        )
        resolved_storage = storage_backend or FileSystemLeadsStorageBackend(resolved_memory_path)

        self._config = LeadsAgentConfig(
            run_config=run_config,
            memory_path=resolved_memory_path,
            storage_backend=resolved_storage,
            max_tokens=max_tokens,
            reset_threshold=reset_threshold,
            prune_search_interval=prune_search_interval,
            prune_token_limit=prune_token_limit,
        )
        self._memory_store = LeadsMemoryStore(memory_path=resolved_memory_path)
        self._run_id: str | None = None
        self._active_icp_index = 0

        external_tools = (
            tuple(tools)
            if tools is not None
            else self._build_provider_tools(
                platforms=self._config.run_config.platforms,
                provider_credentials=dict(provider_credentials or {}),
                provider_clients=dict(provider_clients or {}),
                allowed_provider_operations=dict(allowed_provider_operations or {}),
            )
        )
        tool_registry = ToolRegistry(_merge_tools(external_tools, self._build_internal_tools()))
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
            raise FileNotFoundError(
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
            AgentParameterSection(title="Active ICP", content=_json_block(icp.as_dict())),
            AgentParameterSection(
                title="Run Progress",
                content=_json_block(
                    {
                        "run_id": run_state.run_id,
                        "active_icp_index": self._active_icp_index,
                        "icp_position": self._active_icp_index + 1,
                        "icp_count": len(self._config.run_config.icps),
                        "platforms": list(self._config.run_config.platforms),
                        "searches_attempted_for_icp": _total_searches_for_state(icp_state),
                        "saved_leads_for_icp": len(icp_state.saved_lead_keys),
                        "max_leads_per_icp": self._config.run_config.max_leads_per_icp,
                    }
                ),
            ),
            AgentParameterSection(
                title="Search History",
                content=_render_search_history(summaries, recent_searches),
            ),
            AgentParameterSection(
                title="Saved Leads (Current ICP)",
                content=_json_block(
                    {
                        "count": len(icp_state.saved_lead_keys),
                        "dedupe_keys_tail": icp_state.saved_lead_keys[-10:],
                    }
                ),
            ),
        )

    def pruning_progress_value(self) -> int:
        total = 0
        for icp in self._config.run_config.icps:
            total += _total_searches_for_state(self._memory_store.read_icp_state(icp.key))
        return total

    def run(self, *, max_cycles: int | None = None) -> AgentRunResult:
        self.prepare()
        self._reset_count = 0
        self._transcript.clear()

        cycles_completed = 0
        for icp_index in range(self._active_icp_index, len(self._config.run_config.icps)):
            self._activate_icp(icp_index)
            self._transcript.clear()
            self.refresh_parameters()
            self._last_prune_progress = self.pruning_progress_value()

            while max_cycles is None or cycles_completed < max_cycles:
                request = self.build_model_request()
                response = self._model.generate_turn(request)
                cycles_completed += 1
                self._record_assistant_response(response)

                if response.pause_reason is not None:
                    self._persist_run_state(status="running", active_icp_index=icp_index)
                    return AgentRunResult(
                        status="paused",
                        cycles_completed=cycles_completed,
                        resets=self._reset_count,
                        pause_reason=response.pause_reason,
                    )

                pause_signal: AgentPauseSignal | None = None
                for tool_call in response.tool_calls:
                    result = self._execute_tool(tool_call)
                    if self._apply_compaction_result(result):
                        continue
                    self._record_tool_result(result)
                    if isinstance(result.output, AgentPauseSignal):
                        pause_signal = result.output
                        break

                if pause_signal is not None:
                    self._persist_run_state(status="running", active_icp_index=icp_index)
                    return AgentRunResult(
                        status="paused",
                        cycles_completed=cycles_completed,
                        resets=self._reset_count,
                        pause_reason=pause_signal.reason,
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
                return AgentRunResult(
                    status="max_cycles_reached",
                    cycles_completed=cycles_completed,
                    resets=self._reset_count,
                )

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
        return AgentRunResult(
            status="completed",
            cycles_completed=cycles_completed,
            resets=self._reset_count,
        )

    def _build_internal_tools(self) -> tuple[RegisteredTool, ...]:
        return (
            RegisteredTool(
                definition=_tool_definition(
                    key=LEADS_LOG_SEARCH,
                    name="log_search",
                    description=(
                        "Persist a search attempt for the active ICP. Call this after every provider "
                        "search or enrichment query so the harness can track durable search history."
                    ),
                    properties={
                        "platform": {"type": "string", "description": "Provider family used for the search."},
                        "query": {"type": "string", "description": "Human-readable query or search hypothesis."},
                        "filters": {"type": "object", "additionalProperties": True},
                        "result_count": {"type": "integer", "description": "Number of results returned, if known."},
                        "outcome": {"type": "string", "description": "Short verdict on search quality or next action."},
                        "new_leads": {"type": "integer", "description": "How many new leads this search produced."},
                        "metadata": {"type": "object", "additionalProperties": True},
                    },
                    required=("platform", "query"),
                ),
                handler=self._handle_log_search,
            ),
            RegisteredTool(
                definition=_tool_definition(
                    key=LEADS_COMPACT_SEARCH_HISTORY,
                    name="compact_search_history",
                    description=(
                        "Replace older search entries for the active ICP with a durable summary while keeping "
                        "the most recent tail available in prompt context."
                    ),
                    properties={
                        "summary_content": {"type": "string", "description": "Summary of what worked, what failed, and what remains."},
                        "keep_last": {"type": "integer", "description": "How many recent raw searches to preserve after compaction."},
                    },
                    required=("summary_content",),
                ),
                handler=self._handle_compact_search_history,
            ),
            RegisteredTool(
                definition=_tool_definition(
                    key=LEADS_CHECK_SEEN,
                    name="check_seen_lead",
                    description=(
                        "Check whether a prospective lead has already been saved in durable storage using the "
                        "same dedupe identity."
                    ),
                    properties=_lead_properties_schema(),
                    required=("full_name", "provider"),
                ),
                handler=self._handle_check_seen_lead,
            ),
            RegisteredTool(
                definition=_tool_definition(
                    key=LEADS_SAVE_LEADS,
                    name="save_leads",
                    description=(
                        "Persist one or more qualified leads for the active ICP through the configured storage backend."
                    ),
                    properties={
                        "leads": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": _lead_properties_schema(),
                                "required": ["full_name", "provider"],
                                "additionalProperties": False,
                            },
                        },
                        "metadata": {"type": "object", "additionalProperties": True},
                    },
                    required=("leads",),
                ),
                handler=self._handle_save_leads,
            ),
        )

    def _handle_log_search(self, arguments: dict[str, Any]) -> dict[str, Any]:
        icp = self._current_icp()
        sequence = self._memory_store.next_search_sequence(icp.key)
        search = LeadSearchRecord(
            sequence=sequence,
            icp_key=icp.key,
            platform=str(arguments["platform"]),
            query=str(arguments["query"]),
            recorded_at=_utcnow(),
            filters=dict(arguments.get("filters", {})),
            result_count=int(arguments["result_count"]) if arguments.get("result_count") is not None else None,
            outcome=str(arguments.get("outcome", "")),
            new_leads=int(arguments.get("new_leads", 0)),
            metadata=dict(arguments.get("metadata", {})),
        )
        state = self._memory_store.append_search(icp.key, search)
        auto_summary: LeadSearchSummary | None = None
        if (
            search.sequence % self._config.run_config.search_summary_every == 0
            and len(state.searches) > self._config.run_config.search_tail_size
        ):
            keep_last = self._config.run_config.search_tail_size
            replaceable = state.searches[:-keep_last] if keep_last else list(state.searches)
            auto_summary = self._memory_store.compact_searches(
                icp.key,
                summary_content=_build_auto_summary(replaceable),
                keep_last=keep_last,
                metadata={"auto_compacted": True},
            )
        self.refresh_parameters()
        return {
            "search": search.as_dict(),
            "total_searches_for_icp": self._memory_store.next_search_sequence(icp.key) - 1,
            "auto_compacted": auto_summary is not None,
            "summary": auto_summary.as_dict() if auto_summary is not None else None,
        }

    def _handle_compact_search_history(self, arguments: dict[str, Any]) -> dict[str, Any]:
        icp = self._current_icp()
        summary = self._memory_store.compact_searches(
            icp.key,
            summary_content=str(arguments["summary_content"]),
            keep_last=int(arguments.get("keep_last", self._config.run_config.search_tail_size)),
            metadata={"manual_compaction": True},
        )
        self.refresh_parameters()
        return summary.as_dict()

    def _handle_check_seen_lead(self, arguments: dict[str, Any]) -> dict[str, Any]:
        lead = self._coerce_lead(arguments)
        dedupe_key = lead.dedupe_key()
        already_seen = self._config.storage_backend.has_seen_lead(dedupe_key)
        return {"dedupe_key": dedupe_key, "already_seen": already_seen}

    def _handle_save_leads(self, arguments: dict[str, Any]) -> dict[str, Any]:
        if self._run_id is None:
            raise RuntimeError("Cannot save leads before prepare() has been called.")
        icp = self._current_icp()
        payload = arguments.get("leads")
        if not isinstance(payload, list):
            raise ValueError("The 'leads' argument must be an array.")
        leads = tuple(self._coerce_lead(item) for item in payload)
        results = self._config.storage_backend.save_leads(
            self._run_id,
            icp.key,
            leads,
            metadata=dict(arguments.get("metadata", {})),
        )
        for result in results:
            if result.saved:
                self._memory_store.record_saved_lead_key(icp.key, result.lead.dedupe_key())
        self.refresh_parameters()
        return {
            "saved_count": sum(1 for result in results if result.saved),
            "duplicate_count": sum(1 for result in results if not result.saved),
            "results": [result.as_dict() for result in results],
        }

    def _coerce_lead(self, payload: Mapping[str, Any]) -> LeadRecord:
        icp = self._current_icp()
        return LeadRecord(
            full_name=str(payload["full_name"]),
            company_name=str(payload.get("company_name", "")),
            title=str(payload.get("title", "")),
            icp_key=icp.key,
            provider=str(payload["provider"]),
            found_at=str(payload.get("found_at", _utcnow())),
            email=str(payload["email"]) if payload.get("email") else None,
            linkedin_url=str(payload["linkedin_url"]) if payload.get("linkedin_url") else None,
            phone=str(payload["phone"]) if payload.get("phone") else None,
            location=str(payload["location"]) if payload.get("location") else None,
            provider_person_id=str(payload["provider_person_id"]) if payload.get("provider_person_id") else None,
            source_search_sequence=int(payload["source_search_sequence"]) if payload.get("source_search_sequence") is not None else None,
            metadata=dict(payload.get("metadata", {})),
        )

    def _build_provider_tools(
        self,
        *,
        platforms: Sequence[str],
        provider_credentials: Mapping[str, Any],
        provider_clients: Mapping[str, Any],
        allowed_provider_operations: Mapping[str, Sequence[str] | None],
    ) -> tuple[RegisteredTool, ...]:
        resolved_tools: list[RegisteredTool] = []
        for platform in platforms:
            family = _normalize_platform_name(platform)
            if family not in PROVIDER_FACTORY_MAP:
                available = ", ".join(sorted(PROVIDER_FACTORY_MAP))
                raise ValueError(f"Unsupported leads platform '{family}'. Available: {available}.")
            module_path, function_name = PROVIDER_FACTORY_MAP[family]
            factory = getattr(importlib.import_module(module_path), function_name)
            signature = inspect.signature(factory)
            kwargs: dict[str, Any] = {}
            if "credentials" in signature.parameters and family in provider_credentials:
                kwargs["credentials"] = provider_credentials[family]
            if "client" in signature.parameters and family in provider_clients:
                kwargs["client"] = provider_clients[family]
            if "allowed_operations" in signature.parameters and family in allowed_provider_operations:
                kwargs["allowed_operations"] = allowed_provider_operations[family]
            if "credentials" in signature.parameters and "client" in signature.parameters and not (
                "credentials" in kwargs or "client" in kwargs
            ):
                raise ValueError(
                    f"Platform '{family}' requires either provider credentials or a prebuilt client."
                )
            resolved_tools.extend(factory(**kwargs))
        return tuple(resolved_tools)

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


def _coerce_icps(values: Iterable[LeadICP | dict[str, Any] | str]) -> tuple[LeadICP, ...]:
    resolved: list[LeadICP] = []
    for value in values:
        if isinstance(value, LeadICP):
            resolved.append(value)
        elif isinstance(value, dict):
            resolved.append(LeadICP.from_dict(value))
        elif isinstance(value, str):
            resolved.append(LeadICP(label=value))
        else:
            raise TypeError(f"Unsupported ICP value {value!r}.")
    return tuple(resolved)


def _normalize_platform_name(value: str) -> str:
    return value.strip().lower()


def _merge_tools(*tool_groups: Iterable[RegisteredTool]) -> tuple[RegisteredTool, ...]:
    ordered_keys: list[str] = []
    merged: dict[str, RegisteredTool] = {}
    for tool_group in tool_groups:
        for tool in tool_group:
            if tool.key not in merged:
                ordered_keys.append(tool.key)
            merged[tool.key] = tool
    return tuple(merged[key] for key in ordered_keys)


def _tool_definition(
    *,
    key: str,
    name: str,
    description: str,
    properties: dict[str, Any],
    required: Sequence[str] = (),
) -> ToolDefinition:
    return ToolDefinition(
        key=key,
        name=name,
        description=description,
        input_schema={
            "type": "object",
            "properties": properties,
            "required": list(required),
            "additionalProperties": False,
        },
    )


def _lead_properties_schema() -> dict[str, Any]:
    return {
        "full_name": {"type": "string"},
        "company_name": {"type": "string"},
        "title": {"type": "string"},
        "provider": {"type": "string"},
        "found_at": {"type": "string"},
        "email": {"type": "string"},
        "linkedin_url": {"type": "string"},
        "phone": {"type": "string"},
        "location": {"type": "string"},
        "provider_person_id": {"type": "string"},
        "source_search_sequence": {"type": "integer"},
        "metadata": {"type": "object", "additionalProperties": True},
    }


def _render_search_history(
    summaries: Sequence[LeadSearchSummary],
    recent_searches: Sequence[LeadSearchRecord],
) -> str:
    payload = {
        "summaries": [summary.as_dict() for summary in summaries],
        "recent_searches": [search.as_dict() for search in recent_searches],
    }
    if not payload["summaries"] and not payload["recent_searches"]:
        return "(no search history recorded yet)"
    return _json_block(payload)


def _json_block(payload: Any) -> str:
    return json.dumps(payload, indent=2, sort_keys=True)


def _total_searches_for_state(state: LeadICPState) -> int:
    last_search = state.searches[-1].sequence if state.searches else 0
    last_summary = state.summaries[-1].last_sequence or 0 if state.summaries else 0
    return max(last_search, last_summary)


def _build_auto_summary(entries: Sequence[LeadSearchRecord]) -> str:
    platform_counts = Counter(entry.platform for entry in entries)
    result_counts = [entry.result_count for entry in entries if entry.result_count is not None]
    outcomes = [entry.outcome.strip() for entry in entries if entry.outcome.strip()]
    lines = [
        f"Auto-compacted {len(entries)} searches covering sequences {entries[0].sequence}-{entries[-1].sequence}.",
        f"Platforms used: {', '.join(f'{platform} x{count}' for platform, count in sorted(platform_counts.items()))}.",
        f"Total new leads observed: {sum(entry.new_leads for entry in entries)}.",
    ]
    if result_counts:
        lines.append(f"Observed result counts ranged from {min(result_counts)} to {max(result_counts)}.")
    if outcomes:
        lines.append(f"Recent outcomes: {' | '.join(outcomes[-3:])}")
    return "\n".join(lines)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _timestamped_run_id() -> str:
    return f"run_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"


__all__ = [
    "LEADS_CHECK_SEEN",
    "LEADS_COMPACT_SEARCH_HISTORY",
    "LEADS_LOG_SEARCH",
    "LEADS_SAVE_LEADS",
    "LeadsAgent",
    "LeadsAgentConfig",
]
