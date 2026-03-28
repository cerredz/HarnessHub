"""Reusable agent runtime abstractions and loop orchestration."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence, TypeVar

from harnessiq.interfaces.tool_selection import DynamicToolSelector
from harnessiq.integrations import create_embedding_backend_from_spec
from harnessiq.shared.agents import (
    AgentContextWindow,
    AgentModel,
    AgentModelRequest,
    AgentModelResponse,
    AgentParameterSection,
    AgentPauseSignal,
    AgentRunResult,
    AgentRunStatus,
    AgentRuntimeConfig,
    AgentToolExecutor,
    AgentTranscriptEntry,
    estimate_text_tokens,
    json_parameter_section,
    render_json_parameter_content,
)
from harnessiq.shared.tool_selection import DEFAULT_TOOL_SELECTION_EMBEDDING_MODEL, ToolSelectionResult
from harnessiq.shared.dtos import SerializableDTO
from harnessiq.shared.hooks import HookDefinition
from harnessiq.shared.tools import (
    CONTEXT_COMPACTION_TOOL_KEYS,
    HEAVY_COMPACTION,
    LOG_COMPACTION,
    REMOVE_TOOL_RESULTS,
    REMOVE_TOOLS,
    ToolDefinition,
    ToolResult,
)
from harnessiq.toolset import DefaultDynamicToolSelector, resolve_tool_definition_profiles
from harnessiq.tools.hooks.defaults import is_tool_allowed
from harnessiq.utils.agent_instances import AgentInstanceRecord, AgentInstanceStore
from .helpers import BaseAgentHelpersMixin, _resolve_repo_root, _utcnow

FileBackedStoreT = TypeVar("FileBackedStoreT")


class BaseAgent(BaseAgentHelpersMixin, ABC):
    """Shared harness for long-running tool-using agents."""

    _COMPACTION_TOOL_KEYS = frozenset(
        {
            REMOVE_TOOL_RESULTS,
            REMOVE_TOOLS,
            HEAVY_COMPACTION,
            LOG_COMPACTION,
            *CONTEXT_COMPACTION_TOOL_KEYS,
        }
    )

    def __init__(
        self,
        *,
        name: str,
        model: AgentModel,
        tool_executor: AgentToolExecutor,
        runtime_config: AgentRuntimeConfig | None = None,
        dynamic_tool_selector: DynamicToolSelector | None = None,
        memory_path: Path | None = None,
        repo_root: str | Path | None = None,
        instance_name: str | None = None,
    ) -> None:
        self._name = name
        self._model = model
        self._runtime_config = runtime_config or AgentRuntimeConfig()
        self._repo_root = _resolve_repo_root(repo_root, memory_path)
        self._instance_store = AgentInstanceStore(repo_root=self._repo_root)
        self._instance_record = self._instance_store.resolve(
            agent_name=name,
            payload=self.build_instance_payload(),
            instance_name=instance_name,
            memory_path=memory_path,
        )
        self._memory_path = self._instance_record.memory_path
        self._parameter_sections: tuple[AgentParameterSection, ...] = ()
        self._transcript: list[AgentTranscriptEntry] = []
        self._reset_count = 0
        self._cycle_index = 0
        self._last_run_id: str | None = None
        self._last_prune_progress = 0
        self._session_id: str | None = self._runtime_config.session_id
        self._run_tool_calls = 0
        self._run_tool_call_breakdown: dict[str, int] = {}
        self._context_runtime_state = self._load_context_runtime_state()
        self._tool_executor = tool_executor
        self._hook_tools = self._build_hook_tools()
        self._active_request_tool_keys: tuple[str, ...] | None = None
        self._dynamic_tool_selector = dynamic_tool_selector or self._build_dynamic_tool_selector()
        self._last_tool_selection_result: ToolSelectionResult | None = None

    @property
    def name(self) -> str:
        return self._name

    @property
    def runtime_config(self) -> AgentRuntimeConfig:
        return self._runtime_config

    @property
    def tool_executor(self) -> AgentToolExecutor:
        return self._tool_executor

    @property
    def parameter_sections(self) -> tuple[AgentParameterSection, ...]:
        return self._parameter_sections

    @property
    def transcript(self) -> tuple[AgentTranscriptEntry, ...]:
        return tuple(self._transcript)

    @property
    def reset_count(self) -> int:
        return self._reset_count

    @property
    def cycle_index(self) -> int:
        return self._cycle_index

    @property
    def memory_path(self) -> Path:
        return self._memory_path

    @property
    def repo_root(self) -> Path:
        return self._repo_root

    @property
    def instance_store(self) -> AgentInstanceStore:
        return self._instance_store

    @property
    def instance_record(self) -> AgentInstanceRecord:
        return self._instance_record

    @property
    def instance_id(self) -> str:
        return self._instance_record.instance_id

    @property
    def instance_name(self) -> str:
        return self._instance_record.instance_name

    @property
    def last_run_id(self) -> str | None:
        return self._last_run_id

    @property
    def session_id(self) -> str | None:
        return self._session_id

    @property
    def last_tool_selection_result(self) -> ToolSelectionResult | None:
        return self._last_tool_selection_result

    def build_context_window(self) -> AgentContextWindow:
        """Return the current context window including parameters and transcript entries."""
        if not self._parameter_sections:
            self.refresh_parameters()
        context_window: AgentContextWindow = [
            {"kind": "parameter", "label": section.title, "content": section.content}
            for section in self._parameter_sections
        ]
        for entry in self._transcript:
            context_window.append(self._transcript_entry_to_context_entry(entry))
        return context_window

    @abstractmethod
    def build_instance_payload(self) -> SerializableDTO:
        """Build the agent instance payload persisted to the instance registry."""

    @abstractmethod
    def build_system_prompt(self) -> str:
        """Return the agent's current system prompt."""

    @abstractmethod
    def load_parameter_sections(self) -> Sequence[AgentParameterSection]:
        """Load the durable parameter block injected into the model context."""

    def prepare(self) -> None:
        """Perform any one-time setup before the run loop starts."""

    def available_tools(self, tool_keys: Sequence[str] | None = None) -> tuple[ToolDefinition, ...]:
        """Return the currently registered runtime tools."""
        requested_keys = tool_keys if tool_keys is not None else self._active_request_tool_keys
        return tuple(self._tool_executor.definitions(requested_keys))

    def inspect_tools(self, tool_keys: Sequence[str] | None = None) -> tuple[dict[str, Any], ...]:
        """Return rich inspection metadata for all or selected tools."""
        inspector = getattr(self._tool_executor, "inspect", None)
        if callable(inspector):
            return tuple(inspector(tool_keys))
        definitions = self._tool_executor.definitions(tool_keys)
        return tuple(definition.inspect() for definition in definitions)

    def available_hooks(self) -> tuple[HookDefinition, ...]:
        """Return the resolved hook definitions in execution order."""
        return tuple(hook.definition for hook in self._resolved_hook_tools())

    def inspect_hooks(self, hook_keys: Sequence[str] | None = None) -> tuple[dict[str, Any], ...]:
        """Return inspection metadata for all or selected hooks."""
        selected_keys = set(hook_keys) if hook_keys is not None else None
        return tuple(
            hook.inspect()
            for hook in self._resolved_hook_tools()
            if selected_keys is None or hook.key in selected_keys
        )

    def refresh_parameters(self) -> tuple[AgentParameterSection, ...]:
        """Reload and cache the current durable parameter sections."""
        sections = tuple(self._compose_parameter_sections(tuple(self.load_parameter_sections())))
        self._parameter_sections = sections
        return sections

    def _create_file_backed_store(
        self,
        *,
        store_factory: Callable[[Path], FileBackedStoreT],
        runtime_parameters: Mapping[str, Any] | None = None,
        custom_parameters: Mapping[str, Any] | None = None,
        additional_prompt: str | None = None,
        sync_callback: Callable[[FileBackedStoreT], None] | None = None,
    ) -> FileBackedStoreT:
        """Create one resolved-path file-backed store and persist common config files."""
        store = store_factory(self.memory_path)
        return self._sync_file_backed_store(
            store,
            runtime_parameters=runtime_parameters,
            custom_parameters=custom_parameters,
            additional_prompt=additional_prompt,
            sync_callback=sync_callback,
        )

    def _sync_file_backed_store(
        self,
        store: FileBackedStoreT,
        *,
        runtime_parameters: Mapping[str, Any] | None = None,
        custom_parameters: Mapping[str, Any] | None = None,
        additional_prompt: str | None = None,
        sync_callback: Callable[[FileBackedStoreT], None] | None = None,
    ) -> FileBackedStoreT:
        """Prepare a resolved-path file-backed store and persist shared config files."""
        prepare = getattr(store, "prepare", None)
        if not callable(prepare):
            raise TypeError("File-backed stores used with BaseAgent must define prepare().")
        prepare()
        if runtime_parameters is not None:
            writer = getattr(store, "write_runtime_parameters", None)
            if not callable(writer):
                raise TypeError("Store is missing write_runtime_parameters().")
            writer(dict(runtime_parameters))
        if custom_parameters is not None:
            writer = getattr(store, "write_custom_parameters", None)
            if not callable(writer):
                raise TypeError("Store is missing write_custom_parameters().")
            writer(dict(custom_parameters))
        if additional_prompt is not None:
            writer = getattr(store, "write_additional_prompt", None)
            if not callable(writer):
                raise TypeError("Store is missing write_additional_prompt().")
            writer(additional_prompt)
        if sync_callback is not None:
            sync_callback(store)
        return store

    def reset_context(self) -> None:
        """Clear transcript state and rebuild durable parameters."""
        self._transcript.clear()
        self._reset_count += 1
        self._expire_context_directives()
        self.refresh_parameters()

    def build_model_request(self) -> AgentModelRequest:
        """Build the provider-agnostic model request for the next turn."""
        if not self._parameter_sections:
            self.refresh_parameters()
        active_tool_keys = self._resolve_active_tool_keys()
        self._active_request_tool_keys = active_tool_keys
        try:
            system_prompt = self._effective_system_prompt()
            tools = self.available_tools(active_tool_keys)
        finally:
            self._active_request_tool_keys = None
        return AgentModelRequest(
            agent_name=self._name,
            system_prompt=system_prompt,
            parameter_sections=self._parameter_sections,
            transcript=tuple(self._transcript),
            tools=tools,
        )

    def enable_context_tools(self) -> None:
        """Opt in to the generic context-tool family for this agent instance."""
        self._tool_executor = self._bind_context_tools(self._tool_executor)

    def pruning_progress_value(self) -> int:
        """Return the generic progress counter used by deterministic pruning.

        Concrete agents can override this to map pruning to durable domain work
        such as saved searches, queued tasks, or processed records.
        """
        return len(self._transcript)

    def run(self, *, max_cycles: int | None = None) -> AgentRunResult:
        """Execute the traced run loop for this agent instance."""
        return self._trace_run(lambda: self._run_loop(max_cycles=max_cycles))

    def _run_loop(self, *, max_cycles: int | None = None) -> AgentRunResult:
        """Run the agent loop until it pauses, completes, or hits ``max_cycles``."""
        self.prepare()
        self._reset_count = 0
        self._cycle_index = 0
        self._transcript.clear()
        self.refresh_parameters()
        started_at = self._initialize_terminal_run()
        total_estimated_request_tokens = 0
        self._last_prune_progress = self.pruning_progress_value()

        before_run_pause = self._apply_before_run_hooks()
        if before_run_pause is not None:
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
            while max_cycles is None or cycles_completed < max_cycles:
                self._cycle_index = cycles_completed + 1
                request = self.build_model_request()
                total_estimated_request_tokens += request.estimated_tokens()
                response = self._model.generate_turn(request)
                cycles_completed += 1
                self._record_assistant_response(response)

                if response.pause_reason is not None:
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
                reset_after_tool_result = False
                last_recorded_tool_result: ToolResult | None = None
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
                    last_recorded_tool_result = result
                    if isinstance(result.output, AgentPauseSignal):
                        pause_signal = result.output
                        break
                    if hook_pause_signal is not None:
                        pause_signal = hook_pause_signal
                        break
                    if not self._allow_auto_reset_after_tool_result(result):
                        continue
                    if self._should_prune_context():
                        self.reset_context()
                        self._last_prune_progress = self.pruning_progress_value()
                        reset_after_tool_result = True
                        break
                    if self._should_reset_context():
                        self.reset_context()
                        self._last_prune_progress = self.pruning_progress_value()
                        reset_after_tool_result = True
                        break

                if pause_signal is not None:
                    if self._pause_signal_marks_completion(pause_signal):
                        return self._complete_run(
                            AgentRunResult(
                                status="completed",
                                cycles_completed=cycles_completed,
                                resets=self._reset_count,
                            ),
                            started_at=started_at,
                            total_estimated_request_tokens=total_estimated_request_tokens,
                        )
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

                if reset_after_tool_result:
                    continue

                if not response.should_continue:
                    return self._complete_run(
                        AgentRunResult(
                            status="completed",
                            cycles_completed=cycles_completed,
                            resets=self._reset_count,
                        ),
                        started_at=started_at,
                        total_estimated_request_tokens=total_estimated_request_tokens,
                    )

                if (
                    last_recorded_tool_result is None
                    or self._allow_auto_reset_after_tool_result(last_recorded_tool_result)
                ) and self._should_prune_context():
                    self.reset_context()
                    self._last_prune_progress = self.pruning_progress_value()

                if (
                    last_recorded_tool_result is None
                    or self._allow_auto_reset_after_tool_result(last_recorded_tool_result)
                ) and self._should_reset_context():
                    self.reset_context()
                    self._last_prune_progress = self.pruning_progress_value()
        except Exception as exc:
            self._emit_ledger_entry(
                started_at=started_at,
                finished_at=_utcnow(),
                status="error",
                cycles_completed=cycles_completed,
                total_estimated_request_tokens=total_estimated_request_tokens,
                pause_reason=None,
                error=exc,
            )
            raise

        return self._complete_run(
            AgentRunResult(
                status="max_cycles_reached",
                cycles_completed=cycles_completed,
                resets=self._reset_count,
            ),
            started_at=started_at,
            total_estimated_request_tokens=total_estimated_request_tokens,
        )

    def build_ledger_outputs(self) -> dict[str, Any]:
        """Return structured outputs for the completed run."""
        return {}

    def build_ledger_tags(self) -> list[str]:
        """Return tags attached to the completed run."""
        return []

    def build_ledger_metadata(self) -> dict[str, Any]:
        """Return additional framework- or agent-specific metadata for the run."""
        return {}

    def _pause_signal_marks_completion(self, pause_signal: AgentPauseSignal) -> bool:
        details = pause_signal.details
        return isinstance(details, dict) and details.get("status") == "completed"

    def _build_dynamic_tool_selector(self) -> DynamicToolSelector | None:
        config = self._runtime_config.tool_selection
        if not config.enabled:
            return None
        embedding_model = config.embedding_model or DEFAULT_TOOL_SELECTION_EMBEDDING_MODEL
        backend = create_embedding_backend_from_spec(embedding_model)
        return DefaultDynamicToolSelector(
            config=config,
            embedding_backend=backend,
        )

    def _resolve_active_tool_keys(self) -> tuple[str, ...]:
        available_definitions = self.available_tools(None)
        if self._dynamic_tool_selector is None or not self._runtime_config.tool_selection.enabled:
            self._last_tool_selection_result = None
            return tuple(definition.key for definition in available_definitions)

        candidate_definitions = self._resolve_dynamic_candidate_definitions(available_definitions)
        candidate_profiles = resolve_tool_definition_profiles(candidate_definitions)
        selection = self._dynamic_tool_selector.select(
            context_window=self.build_context_window(),
            candidate_profiles=candidate_profiles,
            metadata={"agent_name": self.name},
        )
        self._last_tool_selection_result = selection
        return selection.selected_keys

    def _resolve_dynamic_candidate_definitions(
        self,
        definitions: Sequence[ToolDefinition],
    ) -> tuple[ToolDefinition, ...]:
        candidates = tuple(definitions)
        allowed_patterns = self._runtime_config.allowed_tools
        if allowed_patterns:
            candidates = tuple(
                definition
                for definition in candidates
                if is_tool_allowed(definition.key, allowed_patterns)
            )
        candidate_patterns = self._runtime_config.tool_selection.candidate_tool_keys
        if candidate_patterns:
            candidates = tuple(
                definition
                for definition in candidates
                if is_tool_allowed(definition.key, candidate_patterns)
            )
        return candidates
