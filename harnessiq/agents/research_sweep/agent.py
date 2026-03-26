"""Deterministic academic research sweep harness."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import TYPE_CHECKING, Any, Mapping, Sequence

from harnessiq.agents.base import BaseAgent
from harnessiq.agents.research_sweep.helpers import (
    append_transcript_entry as _append_transcript_entry,
    utc_today as _utc_today,
)
from harnessiq.shared.agents import (
    DEFAULT_AGENT_CONTEXT_MEMORY_FIELD_RULES,
    AgentContextRuntimeState,
    AgentModel,
    AgentParameterSection,
    AgentRuntimeConfig,
    json_parameter_section,
    merge_agent_runtime_config,
)
from harnessiq.shared.research_sweep import (
    CANONICAL_RESEARCH_SWEEP_SITES,
    DEFAULT_RESEARCH_SWEEP_RESET_THRESHOLD,
    DEFAULT_ALLOWED_SERPER_OPERATIONS,
    RESEARCH_SWEEP_HARNESS_MANIFEST,
    RESEARCH_SWEEP_MEMORY_FIELD_ORDER,
    RESEARCH_SWEEP_MEMORY_FIELD_RULES,
    ResearchSweepAgentConfig,
    ResearchSweepMemoryStore,
    build_research_sweep_configuration_payload,
    normalize_allowed_serper_operations,
    normalize_research_sweep_custom_parameters,
    normalize_research_sweep_runtime_parameters,
    validate_query_for_run,
)
from harnessiq.shared.tools import (
    CONTEXT_INJECT_HANDOFF_BRIEF,
    CONTEXT_INJECT_TASK_REMINDER,
    CONTEXT_PARAM_APPEND_MEMORY_FIELD,
    CONTEXT_PARAM_BULK_WRITE_MEMORY,
    CONTEXT_PARAM_OVERWRITE_MEMORY_FIELD,
    CONTEXT_PARAM_WRITE_ONCE_MEMORY_FIELD,
    CONTEXT_SUMMARIZE_STATE_SNAPSHOT,
    RegisteredTool,
    SERPER_REQUEST,
    ToolResult,
)
from harnessiq.tools.context import (
    BoundContextToolExecutor,
    build_tool_definition,
    create_context_tools,
)
from harnessiq.tools.registry import create_tool_registry
from harnessiq.tools.serper import create_serper_tools

if TYPE_CHECKING:
    from harnessiq.providers.serper.client import SerperClient, SerperCredentials

_PROMPTS_DIR = Path(__file__).parent / "prompts"
_MASTER_PROMPT_PATH = _PROMPTS_DIR / "master_prompt.md"


class ResearchSweepAgent(BaseAgent):
    """Run a fixed-order nine-site academic research sweep with durable reset-safe memory."""

    _allowed_context_tool_keys = frozenset(
        {
            CONTEXT_PARAM_WRITE_ONCE_MEMORY_FIELD,
            CONTEXT_PARAM_OVERWRITE_MEMORY_FIELD,
            CONTEXT_PARAM_APPEND_MEMORY_FIELD,
            CONTEXT_PARAM_BULK_WRITE_MEMORY,
            CONTEXT_INJECT_HANDOFF_BRIEF,
            CONTEXT_INJECT_TASK_REMINDER,
            CONTEXT_SUMMARIZE_STATE_SNAPSHOT,
        }
    )

    def __init__(
        self,
        *,
        model: AgentModel,
        query: str,
        memory_path: str | Path | None = None,
        serper_client: "SerperClient | None" = None,
        serper_credentials: "SerperCredentials | None" = None,
        allowed_serper_operations: str | Sequence[str] | None = None,
        additional_prompt: str = "",
        max_tokens: int = 80_000,
        reset_threshold: float = DEFAULT_RESEARCH_SWEEP_RESET_THRESHOLD,
        runtime_config: AgentRuntimeConfig | None = None,
        tools: Sequence[RegisteredTool] | None = None,
        instance_name: str | None = None,
    ) -> None:
        candidate_memory_path = (
            Path(memory_path)
            if memory_path is not None
            else Path(RESEARCH_SWEEP_HARNESS_MANIFEST.resolved_default_memory_root)
        )
        self._payload_query = validate_query_for_run(query)
        self._payload_additional_prompt = additional_prompt.strip()
        self._payload_allowed_serper_operations = normalize_allowed_serper_operations(
            allowed_serper_operations or DEFAULT_ALLOWED_SERPER_OPERATIONS
        )
        self._payload_max_tokens = max_tokens
        self._payload_reset_threshold = reset_threshold
        self._memory_store = ResearchSweepMemoryStore(memory_path=candidate_memory_path)
        self._memory_store.prepare()
        self._write_native_config_files(
            memory_store=self._memory_store,
            query=self._payload_query,
            additional_prompt=self._payload_additional_prompt,
            runtime_parameters={
                "max_tokens": max_tokens,
                "reset_threshold": reset_threshold,
            },
            custom_parameters={
                "query": self._payload_query,
                "allowed_serper_operations": ",".join(self._payload_allowed_serper_operations),
            },
        )
        delegate_registry = create_tool_registry(
            create_serper_tools(
                client=serper_client,
                credentials=serper_credentials,
                allowed_operations=self._payload_allowed_serper_operations,
            ),
            tuple(tools or ()),
        )
        super().__init__(
            name="research_sweep_agent",
            model=model,
            tool_executor=delegate_registry,
            runtime_config=merge_agent_runtime_config(
                runtime_config,
                max_tokens=max_tokens,
                reset_threshold=reset_threshold,
            ),
            memory_path=candidate_memory_path,
            instance_name=instance_name,
        )
        self._config = ResearchSweepAgentConfig(
            memory_path=self.memory_path,
            query=self._payload_query,
            allowed_serper_operations=self._payload_allowed_serper_operations,
            additional_prompt=self._payload_additional_prompt,
            max_tokens=max_tokens,
            reset_threshold=reset_threshold,
        )
        self._memory_store = ResearchSweepMemoryStore(memory_path=self.memory_path)
        self._memory_store.prepare()
        self._write_native_config_files(
            memory_store=self._memory_store,
            query=self._config.query,
            additional_prompt=self._config.additional_prompt,
            runtime_parameters={
                "max_tokens": self._config.max_tokens,
                "reset_threshold": self._config.reset_threshold,
            },
            custom_parameters={
                "query": self._config.query,
                "allowed_serper_operations": ",".join(self._config.allowed_serper_operations),
            },
        )
        self._reset_state_if_query_changed()
        self._prime_context_memory_rules()
        self._tool_executor = BoundContextToolExecutor(
            delegate=self._tool_executor,
            context_tools=self._build_context_tools(),
        )

    @property
    def config(self) -> ResearchSweepAgentConfig:
        return self._config

    @property
    def memory_store(self) -> ResearchSweepMemoryStore:
        return self._memory_store

    @classmethod
    def from_memory(
        cls,
        *,
        model: AgentModel,
        memory_path: str | Path | None = None,
        serper_client: "SerperClient | None" = None,
        serper_credentials: "SerperCredentials | None" = None,
        runtime_overrides: Mapping[str, Any] | None = None,
        custom_overrides: Mapping[str, Any] | None = None,
        runtime_config: AgentRuntimeConfig | None = None,
        tools: Sequence[RegisteredTool] | None = None,
        instance_name: str | None = None,
    ) -> "ResearchSweepAgent":
        resolved_memory_path = (
            Path(memory_path)
            if memory_path is not None
            else Path(RESEARCH_SWEEP_HARNESS_MANIFEST.resolved_default_memory_root)
        )
        store = ResearchSweepMemoryStore(memory_path=resolved_memory_path)
        store.prepare()
        runtime_parameters = store.read_runtime_parameters()
        if runtime_overrides:
            runtime_parameters.update(runtime_overrides)
        custom_parameters = store.read_custom_parameters()
        if custom_overrides:
            custom_parameters.update(custom_overrides)
        normalized_runtime = normalize_research_sweep_runtime_parameters(runtime_parameters)
        normalized_custom = normalize_research_sweep_custom_parameters(custom_parameters)
        query = str(normalized_custom.get("query") or store.read_query()).strip()
        return cls(
            model=model,
            query=validate_query_for_run(query),
            memory_path=resolved_memory_path,
            serper_client=serper_client,
            serper_credentials=serper_credentials,
            allowed_serper_operations=normalized_custom.get(
                "allowed_serper_operations",
                ",".join(DEFAULT_ALLOWED_SERPER_OPERATIONS),
            ),
            additional_prompt=store.read_additional_prompt(),
            max_tokens=int(normalized_runtime.get("max_tokens", 80_000)),
            reset_threshold=float(
                normalized_runtime.get("reset_threshold", DEFAULT_RESEARCH_SWEEP_RESET_THRESHOLD)
            ),
            runtime_config=runtime_config,
            tools=tools,
            instance_name=instance_name,
        )

    def build_instance_payload(self) -> dict[str, Any]:
        return {
            "config": {
                "additional_prompt": self._payload_additional_prompt,
                "allowed_serper_operations": list(self._payload_allowed_serper_operations),
                "query": self._payload_query,
            },
            "memory_path": str(self._memory_store.memory_path),
            "runtime": {
                "max_tokens": self._payload_max_tokens,
                "reset_threshold": self._payload_reset_threshold,
            },
        }

    def prepare(self) -> None:
        self._memory_store.prepare()
        self._write_native_config_files(
            memory_store=self._memory_store,
            query=self._config.query,
            additional_prompt=self._config.additional_prompt,
            runtime_parameters={
                "max_tokens": self._config.max_tokens,
                "reset_threshold": self._config.reset_threshold,
            },
            custom_parameters={
                "query": self._config.query,
                "allowed_serper_operations": ",".join(self._config.allowed_serper_operations),
            },
        )
        if "original_objective" not in self._context_runtime_state.memory_fields:
            self._context_runtime_state.memory_fields["original_objective"] = (
                f"Complete the research sweep for query: {self._config.query}"
            )
            self._save_context_runtime_state()

    def build_system_prompt(self) -> str:
        return (
            "You are ResearchSweepAgent. "
            "Treat the Master Prompt, Research Sweep Configuration, and Research Sweep Memory sections "
            "as the complete source of truth for this run."
        )

    def load_parameter_sections(self) -> Sequence[AgentParameterSection]:
        sections: list[AgentParameterSection] = [
            AgentParameterSection(title="Master Prompt", content=self._load_master_prompt()),
            json_parameter_section(
                "Research Sweep Configuration",
                build_research_sweep_configuration_payload(
                    query=self._config.query,
                    allowed_serper_operations=self._config.allowed_serper_operations,
                    search_date=_utc_today(),
                ),
            ),
            json_parameter_section("Research Sweep Memory", self._render_research_memory_payload()),
        ]
        if self._config.additional_prompt:
            sections.append(
                AgentParameterSection(
                    title="Additional Prompt",
                    content=self._config.additional_prompt,
                )
            )
        return tuple(sections)

    def build_ledger_outputs(self) -> dict[str, Any]:
        memory = self._memory_store.read_research_memory()
        site_results = memory.get("site_results", [])
        return {
            "all_sites_empty": memory.get("all_sites_empty"),
            "continuation_pointer": memory.get("continuation_pointer"),
            "final_report": memory.get("final_report"),
            "query": self._config.query,
            "site_results": site_results if isinstance(site_results, list) else [],
        }

    def build_ledger_tags(self) -> list[str]:
        return ["research", "academic", "serper"]

    def build_ledger_metadata(self) -> dict[str, Any]:
        summary = self._memory_store.read_research_memory_summary()
        return {
            "allowed_serper_operations": list(self._config.allowed_serper_operations),
            "completed_sites": summary["completed_sites"],
            "site_count": len(CANONICAL_RESEARCH_SWEEP_SITES),
        }

    def _build_context_memory_payload(self) -> dict[str, Any] | None:
        return None

    def _allow_auto_reset_after_tool_result(self, result: ToolResult) -> bool:
        if result.tool_key == SERPER_REQUEST:
            return False
        if result.tool_key == CONTEXT_PARAM_APPEND_MEMORY_FIELD:
            return False
        if result.tool_key == CONTEXT_PARAM_BULK_WRITE_MEMORY:
            return True
        if result.tool_key == CONTEXT_SUMMARIZE_STATE_SNAPSHOT:
            return True
        if result.tool_key in {CONTEXT_INJECT_HANDOFF_BRIEF, CONTEXT_INJECT_TASK_REMINDER}:
            return True
        if result.tool_key == CONTEXT_PARAM_WRITE_ONCE_MEMORY_FIELD:
            payload = result.output
            return isinstance(payload, dict) and payload.get("field_name") == "query"
        if result.tool_key == CONTEXT_PARAM_OVERWRITE_MEMORY_FIELD:
            payload = result.output
            if not isinstance(payload, dict):
                return False
            return payload.get("field_name") in {"continuation_pointer", "final_report"}
        return False

    def _build_context_tools(self) -> tuple[RegisteredTool, ...]:
        context_tools = create_context_tools(
            get_context_window=self.build_context_window,
            get_runtime_state=lambda: self._context_runtime_state,
            save_runtime_state=self._save_context_runtime_state,
            refresh_parameters=self.refresh_parameters,
            get_reset_count=lambda: self._reset_count,
            get_cycle_index=lambda: self._cycle_index,
            get_system_prompt=self.build_system_prompt,
            run_model_subcall=self._run_context_model_subcall,
        )
        filtered = [
            tool
            for tool in context_tools
            if tool.key in self._allowed_context_tool_keys and tool.key != CONTEXT_INJECT_HANDOFF_BRIEF
        ]
        filtered.append(self._build_handoff_brief_tool())
        return tuple(filtered)

    def _build_handoff_brief_tool(self) -> RegisteredTool:
        definition = build_tool_definition(
            key=CONTEXT_INJECT_HANDOFF_BRIEF,
            name="handoff_brief",
            description=(
                "Inject a research-sweep-specific post-reset orientation brief. "
                "Use it after a reset to restate the query, how many sites have already been completed, "
                "and which site should be searched next."
            ),
            properties={
                "query": {"type": "string"},
                "completed_sites": {"type": "integer"},
                "next_site": {"type": "string"},
            },
        )

        def handler(arguments: dict[str, Any]) -> dict[str, Any]:
            memory = self._render_research_memory_payload()
            sites_remaining = memory.get("sites_remaining", [])
            completed_sites = arguments.get("completed_sites")
            if isinstance(completed_sites, bool) or (
                completed_sites is not None and not isinstance(completed_sites, int)
            ):
                raise ValueError("The 'completed_sites' argument must be an integer when provided.")
            if completed_sites is None:
                if isinstance(sites_remaining, list):
                    completed_sites = max(0, len(CANONICAL_RESEARCH_SWEEP_SITES) - len(sites_remaining))
                else:
                    site_results = memory.get("site_results", [])
                    completed_sites = len(site_results) if isinstance(site_results, list) else 0
            query = arguments.get("query")
            if query is None:
                query = memory.get("query") or self._config.query
            if not isinstance(query, str) or not query.strip():
                raise ValueError("The 'query' argument must resolve to a non-empty string.")
            next_site = arguments.get("next_site")
            if next_site is None:
                next_site = memory.get("continuation_pointer") or "(not set)"
            if not isinstance(next_site, str) or not next_site.strip():
                raise ValueError("The 'next_site' argument must resolve to a non-empty string.")
            entry = {
                "kind": "context",
                "label": "HANDOFF BRIEF",
                "content": (
                    f"Query: {query.strip()}\n"
                    f"Completed Sites: {completed_sites}/{len(CANONICAL_RESEARCH_SWEEP_SITES)}\n"
                    f"Next Site: {next_site.strip()}"
                ),
            }
            return {"context_window": _append_transcript_entry(self, entry)}

        return RegisteredTool(definition=definition, handler=handler)

    def _load_master_prompt(self) -> str:
        if not _MASTER_PROMPT_PATH.exists():
            raise FileNotFoundError(
                f"Research sweep master prompt not found at '{_MASTER_PROMPT_PATH}'."
            )
        return _MASTER_PROMPT_PATH.read_text(encoding="utf-8")

    def _render_research_memory_payload(self) -> dict[str, Any]:
        raw_memory_fields = self._context_runtime_state.memory_fields
        return {
            field_name: deepcopy(raw_memory_fields[field_name])
            for field_name in RESEARCH_SWEEP_MEMORY_FIELD_ORDER
            if field_name in raw_memory_fields
        }

    def _prime_context_memory_rules(self) -> None:
        changed = False
        for field_name, update_rule in RESEARCH_SWEEP_MEMORY_FIELD_RULES.items():
            if self._context_runtime_state.memory_field_rules.get(field_name) == update_rule:
                continue
            self._context_runtime_state.memory_field_rules[field_name] = update_rule  # type: ignore[assignment]
            changed = True
        for field_name, update_rule in DEFAULT_AGENT_CONTEXT_MEMORY_FIELD_RULES.items():
            if field_name not in self._context_runtime_state.memory_field_rules:
                self._context_runtime_state.memory_field_rules[field_name] = update_rule  # type: ignore[assignment]
                changed = True
        if changed:
            self._save_context_runtime_state()

    def _reset_state_if_query_changed(self) -> None:
        existing_query = self._context_runtime_state.memory_fields.get("query")
        if existing_query is None:
            return
        if str(existing_query).strip() == self._config.query:
            return
        self._context_runtime_state = AgentContextRuntimeState(
            memory_field_rules=dict(DEFAULT_AGENT_CONTEXT_MEMORY_FIELD_RULES)
        )
        self._save_context_runtime_state()

    def _write_native_config_files(
        self,
        *,
        memory_store: ResearchSweepMemoryStore,
        query: str,
        additional_prompt: str,
        runtime_parameters: Mapping[str, Any],
        custom_parameters: Mapping[str, Any],
    ) -> None:
        memory_store.prepare()
        memory_store.write_query(query)
        memory_store.write_additional_prompt(additional_prompt)
        memory_store.write_runtime_parameters(runtime_parameters)
        memory_store.write_custom_parameters(custom_parameters)
__all__ = ["ResearchSweepAgent"]
