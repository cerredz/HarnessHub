"""Google Maps prospecting agent harness."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

from harnessiq.agents.base import BaseAgent
from harnessiq.agents.helpers import (
    find_repo_root as _find_repo_root,
    resolve_memory_path as _resolve_memory_path,
)
from harnessiq.agents.prospecting.helpers import (
    build_instance_payload as _build_instance_payload,
    create_browser_stub_tools as _create_browser_stub_tools,
    parse_json_object as _parse_json_object,
    tool as _tool,
)
from harnessiq.shared.agents import (
    DEFAULT_AGENT_MAX_TOKENS,
    DEFAULT_AGENT_RESET_THRESHOLD,
    AgentModel,
    AgentModelRequest,
    AgentParameterSection,
    AgentRuntimeConfig,
    json_parameter_section,
    merge_agent_runtime_config,
)
from harnessiq.shared.exceptions import ResourceNotFoundError, StateError, ValidationError
from harnessiq.shared.prospecting import (
    DEFAULT_AGENT_IDENTITY,
    DEFAULT_COMPANY_DESCRIPTION,
    DEFAULT_EVAL_SYSTEM_PROMPT,
    DEFAULT_GOOGLE_MAPS_SEARCH_BASE_URL,
    DEFAULT_MAX_LISTINGS_PER_SEARCH,
    DEFAULT_MAX_SEARCHES_PER_RUN,
    DEFAULT_QUALIFICATION_THRESHOLD,
    DEFAULT_SINK_RECORD_TYPE,
    DEFAULT_SUMMARIZE_AT_X,
    DEFAULT_WEBSITE_INSPECT_ENABLED,
    NEXT_QUERY_SYSTEM_PROMPT,
    ProspectingAgentConfig,
    ProspectingMemoryStore,
    ProspectingState,
    QualifiedLeadRecord,
    RUN_STATUS_COMPLETE,
    RUN_STATUS_ERROR,
    RUN_STATUS_IN_PROGRESS,
    SEARCH_SUMMARY_SYSTEM_PROMPT,
    SearchRecord,
    normalize_prospecting_custom_parameters,
    normalize_prospecting_runtime_parameters,
    utcnow,
)
from harnessiq.shared.tools import RegisteredTool, SEARCH_OR_SUMMARIZE, ToolResult
from harnessiq.tools import create_evaluate_company_tool, create_search_or_summarize_tool
from harnessiq.tools.registry import create_tool_registry

_PROMPTS_DIR = Path(__file__).parent / "prompts"
_MASTER_PROMPT_PATH = _PROMPTS_DIR / "master_prompt.md"
_DEFAULT_MEMORY_PATH = Path(__file__).parent / "memory"

JsonSubcallRunner = Callable[[str, Sequence[AgentParameterSection], str], dict[str, Any]]


class GoogleMapsProspectingAgent(BaseAgent):
    """Concrete harness for Google Maps prospecting."""

    _RESET_SAFE_TOOL_KEYS = frozenset(
        {
            SEARCH_OR_SUMMARIZE,
            "prospecting.start_search",
            "prospecting.record_listing_result",
            "prospecting.save_qualified_lead",
            "prospecting.complete_search",
        }
    )

    def __init__(
        self,
        *,
        model: AgentModel,
        memory_path: str | Path | None = None,
        browser_tools: Iterable[RegisteredTool] = (),
        company_description: str | None = None,
        max_tokens: int = DEFAULT_AGENT_MAX_TOKENS,
        reset_threshold: float = DEFAULT_AGENT_RESET_THRESHOLD,
        qualification_threshold: int = DEFAULT_QUALIFICATION_THRESHOLD,
        summarize_at_x: int = DEFAULT_SUMMARIZE_AT_X,
        max_searches_per_run: int = DEFAULT_MAX_SEARCHES_PER_RUN,
        max_listings_per_search: int = DEFAULT_MAX_LISTINGS_PER_SEARCH,
        website_inspect_enabled: bool = DEFAULT_WEBSITE_INSPECT_ENABLED,
        sink_record_type: str = DEFAULT_SINK_RECORD_TYPE,
        eval_system_prompt: str = DEFAULT_EVAL_SYSTEM_PROMPT,
        tools: Sequence[RegisteredTool] | None = None,
        runtime_config: AgentRuntimeConfig | None = None,
        json_subcall_runner: JsonSubcallRunner | None = None,
    ) -> None:
        # Store all params needed by build_instance_payload() before calling super().__init__().
        self._candidate_memory_path = Path(memory_path) if memory_path is not None else None
        self._payload_company_description = company_description
        self._payload_max_tokens = max_tokens
        self._payload_reset_threshold = reset_threshold
        self._payload_qualification_threshold = qualification_threshold
        self._payload_summarize_at_x = summarize_at_x
        self._payload_max_searches_per_run = max_searches_per_run
        self._payload_max_listings_per_search = max_listings_per_search
        self._payload_website_inspect_enabled = website_inspect_enabled
        self._payload_sink_record_type = sink_record_type
        self._payload_eval_system_prompt = eval_system_prompt

        self._config = ProspectingAgentConfig(
            memory_path=Path("."),
            max_tokens=max_tokens,
            reset_threshold=reset_threshold,
            qualification_threshold=qualification_threshold,
            summarize_at_x=summarize_at_x,
            max_searches_per_run=max_searches_per_run,
            max_listings_per_search=max_listings_per_search,
            website_inspect_enabled=website_inspect_enabled,
            sink_record_type=sink_record_type,
            eval_system_prompt=eval_system_prompt,
        )
        self._initial_company_description = company_description.strip() if company_description else ""
        self._json_subcall_runner = json_subcall_runner

        tool_registry = create_tool_registry(
            _create_browser_stub_tools(),
            tuple(browser_tools),
            self._build_public_tools(),
            self._build_internal_tools(),
            tuple(tools or ()),
        )
        super().__init__(
            name="google_maps_prospecting",
            model=model,
            tool_executor=tool_registry,
            runtime_config=merge_agent_runtime_config(
                runtime_config,
                max_tokens=max_tokens,
                reset_threshold=reset_threshold,
            ),
            memory_path=self._candidate_memory_path,
            repo_root=_find_repo_root(self._candidate_memory_path),
        )
        resolved_memory_path = self.memory_path or _DEFAULT_MEMORY_PATH
        self._memory_store = ProspectingMemoryStore(memory_path=resolved_memory_path)
        self._config = ProspectingAgentConfig(
            memory_path=resolved_memory_path,
            max_tokens=max_tokens,
            reset_threshold=reset_threshold,
            qualification_threshold=qualification_threshold,
            summarize_at_x=summarize_at_x,
            max_searches_per_run=max_searches_per_run,
            max_listings_per_search=max_listings_per_search,
            website_inspect_enabled=website_inspect_enabled,
            sink_record_type=sink_record_type,
            eval_system_prompt=eval_system_prompt,
        )

    @property
    def config(self) -> ProspectingAgentConfig:
        return self._config

    @property
    def memory_store(self) -> ProspectingMemoryStore:
        return self._memory_store

    @classmethod
    def from_memory(
        cls,
        *,
        model: AgentModel,
        memory_path: str | Path | None = None,
        browser_tools: Iterable[RegisteredTool] = (),
        runtime_overrides: Mapping[str, Any] | None = None,
        custom_overrides: Mapping[str, Any] | None = None,
        tools: Sequence[RegisteredTool] | None = None,
        runtime_config: AgentRuntimeConfig | None = None,
        json_subcall_runner: JsonSubcallRunner | None = None,
    ) -> "GoogleMapsProspectingAgent":
        resolved_path = _resolve_memory_path(memory_path, default_path=_DEFAULT_MEMORY_PATH)
        store = ProspectingMemoryStore(memory_path=resolved_path)
        store.prepare()
        runtime_parameters = store.read_runtime_parameters()
        if runtime_overrides:
            runtime_parameters.update(runtime_overrides)
        custom_parameters = store.read_custom_parameters()
        if custom_overrides:
            custom_parameters.update(custom_overrides)
        normalized_runtime = normalize_prospecting_runtime_parameters(runtime_parameters)
        normalized_custom = normalize_prospecting_custom_parameters(custom_parameters)
        return cls(
            model=model,
            memory_path=resolved_path,
            browser_tools=browser_tools,
            company_description=store.read_company_description(),
            tools=tools,
            runtime_config=runtime_config,
            json_subcall_runner=json_subcall_runner,
            **normalized_runtime,
            **normalized_custom,
        )

    def prepare(self) -> None:
        self._memory_store.prepare()
        if self._initial_company_description:
            self._memory_store.write_company_description(self._initial_company_description)
        state = self._memory_store.ensure_state_matches_company_description()
        if state.run_status == RUN_STATUS_COMPLETE:
            self._memory_store.write_state(
                ProspectingState(
                    run_id=state.run_id,
                    company_description=state.company_description,
                    searches_completed=state.searches_completed,
                    searches_summarized_through=state.searches_summarized_through,
                    search_history_summary=state.search_history_summary,
                    last_completed_search_index=state.last_completed_search_index,
                    current_search_in_progress=state.current_search_in_progress,
                    qualified_leads_posted=state.qualified_leads_posted,
                    disqualified_leads_count=state.disqualified_leads_count,
                    session_reset_count=self.reset_count,
                    run_status=RUN_STATUS_IN_PROGRESS,
                    error_log=state.error_log,
                )
            )
        else:
            self._memory_store.update_state(run_status=RUN_STATUS_IN_PROGRESS)

    def run(self, *, max_cycles: int | None = None):  # type: ignore[override]
        try:
            result = super().run(max_cycles=max_cycles)
        except Exception:
            self._memory_store.update_state(run_status=RUN_STATUS_ERROR)
            raise
        final_state = self._memory_store.read_state()
        final_status = RUN_STATUS_IN_PROGRESS
        if result.status == "completed" and final_state.current_search_in_progress is None:
            final_status = RUN_STATUS_COMPLETE
        elif result.status == "completed":
            self._memory_store.append_error(
                "Agent loop ended while a search was still marked in progress; preserving resumable state."
            )
        self._memory_store.update_state(run_status=final_status)
        return result

    def reset_context(self) -> None:
        self._transcript.clear()
        self._reset_count += 1
        self._expire_context_directives()
        self._memory_store.update_state(session_reset_count=self.reset_count)
        self.refresh_parameters()

    def build_system_prompt(self) -> str:
        if not _MASTER_PROMPT_PATH.exists():
            raise ResourceNotFoundError(f"Prospecting master prompt not found at '{_MASTER_PROMPT_PATH}'.")
        prompt = _MASTER_PROMPT_PATH.read_text(encoding="utf-8")
        company_description = self._memory_store.read_company_description() or DEFAULT_COMPANY_DESCRIPTION
        identity = self._memory_store.read_agent_identity() or DEFAULT_AGENT_IDENTITY
        tool_lines = "\n".join(f"- {tool.key}: {tool.description}" for tool in self.available_tools())
        replacements = {
            "{{identity}}": identity,
            "{{company_description}}": company_description,
            "{{qualification_threshold}}": str(self._config.qualification_threshold),
            "{{summarize_at_x}}": str(self._config.summarize_at_x),
            "{{max_searches_per_run}}": str(self._config.max_searches_per_run),
            "{{max_listings_per_search}}": str(self._config.max_listings_per_search),
            "{{website_inspect_enabled}}": str(self._config.website_inspect_enabled).lower(),
            "{{google_maps_search_base_url}}": DEFAULT_GOOGLE_MAPS_SEARCH_BASE_URL,
            "{{tool_lines}}": tool_lines,
        }
        for placeholder, value in replacements.items():
            prompt = prompt.replace(placeholder, value)
        additional_prompt = self._memory_store.read_additional_prompt()
        if additional_prompt:
            prompt = f"{prompt}\n\n[ADDITIONAL INSTRUCTIONS]\n{additional_prompt}"
        return prompt

    def load_parameter_sections(self) -> Sequence[AgentParameterSection]:
        state = self._memory_store.read_state()
        searches_completed_count = max(0, state.last_completed_search_index + 1)
        recent_searches = [
            {
                "index": record.index,
                "query": record.query,
                "location": record.location,
                "listings_found": record.listings_found,
                "listings_evaluated": record.listings_evaluated,
                "qualified_count": record.qualified_count,
            }
            for record in state.searches_completed[-10:]
        ]
        recent_leads = [
            {
                "business_name": record.business_name,
                "maps_url": record.maps_url,
                "website_url": record.website_url,
                "score": record.score,
                "search_index": record.search_index,
                "search_query": record.search_query,
            }
            for record in self._memory_store.read_qualified_leads()[-10:]
        ]
        return (
            AgentParameterSection(
                title="Company Description",
                content=self._memory_store.read_company_description() or DEFAULT_COMPANY_DESCRIPTION,
            ),
            json_parameter_section(
                "Run State",
                {
                    "last_completed_search_index": state.last_completed_search_index,
                    "searches_completed_count": searches_completed_count,
                    "current_search_in_progress": (
                        state.current_search_in_progress.as_dict()
                        if state.current_search_in_progress is not None
                        else None
                    ),
                    "searches_summarized_through": state.searches_summarized_through,
                    "search_history_summary": state.search_history_summary,
                    "qualified_leads_posted": state.qualified_leads_posted,
                    "disqualified_leads_count": state.disqualified_leads_count,
                    "session_reset_count": state.session_reset_count,
                    "run_status": state.run_status,
                    "error_log": list(state.error_log),
                },
            ),
            json_parameter_section("Recent Completed Searches", recent_searches),
            json_parameter_section("Recent Qualified Leads", recent_leads),
        )

    def build_ledger_outputs(self) -> dict[str, Any]:
        state = self._memory_store.read_state()
        return {
            "company_description": state.company_description,
            "qualified_leads": [record.as_dict() for record in self._memory_store.read_qualified_leads()],
            "searches_completed": [record.as_dict() for record in state.searches_completed],
            "summary": state.search_history_summary,
            "counts": {
                "qualified_leads_posted": state.qualified_leads_posted,
                "disqualified_leads_count": state.disqualified_leads_count,
            },
        }

    def build_ledger_tags(self) -> list[str]:
        return ["prospecting", "google-maps", "sales"]

    def build_ledger_metadata(self) -> dict[str, Any]:
        return {
            "qualification_threshold": self._config.qualification_threshold,
            "summarize_at_x": self._config.summarize_at_x,
            "max_searches_per_run": self._config.max_searches_per_run,
            "max_listings_per_search": self._config.max_listings_per_search,
            "website_inspect_enabled": self._config.website_inspect_enabled,
            "sink_record_type": self._config.sink_record_type,
        }

    def build_instance_payload(self) -> dict[str, Any]:
        return _build_instance_payload(
            memory_path=self._candidate_memory_path,
            company_description=self._payload_company_description,
            max_tokens=self._payload_max_tokens,
            reset_threshold=self._payload_reset_threshold,
            qualification_threshold=self._payload_qualification_threshold,
            summarize_at_x=self._payload_summarize_at_x,
            max_searches_per_run=self._payload_max_searches_per_run,
            max_listings_per_search=self._payload_max_listings_per_search,
            website_inspect_enabled=self._payload_website_inspect_enabled,
            sink_record_type=self._payload_sink_record_type,
            eval_system_prompt=self._payload_eval_system_prompt,
        )

    def _build_public_tools(self) -> tuple[RegisteredTool, ...]:
        return (
            create_evaluate_company_tool(handler=self._handle_evaluate_company),
            create_search_or_summarize_tool(handler=self._handle_search_or_summarize),
        )

    def _build_internal_tools(self) -> tuple[RegisteredTool, ...]:
        return (
            _tool(
                key="prospecting.start_search",
                name="start_search",
                description="Persist the start of a Google Maps search so the run can resume after a reset.",
                properties={
                    "index": {"type": "integer", "description": "Search index."},
                    "query": {"type": "string", "description": "Search query."},
                    "location": {"type": "string", "description": "Search location."},
                },
                required=("index", "query", "location"),
                handler=self._handle_start_search,
            ),
            _tool(
                key="prospecting.record_listing_result",
                name="record_listing_result",
                description="Persist progress for one evaluated listing within the active search.",
                properties={
                    "search_index": {"type": "integer", "description": "Active search index."},
                    "listing_position": {"type": "integer", "description": "Zero-based listing position."},
                    "verdict": {
                        "type": "string",
                        "enum": ["QUALIFIED", "DISQUALIFIED", "SKIP"],
                        "description": "Evaluation verdict.",
                    },
                },
                required=("search_index", "listing_position", "verdict"),
                handler=self._handle_record_listing_result,
            ),
            _tool(
                key="prospecting.save_qualified_lead",
                name="save_qualified_lead",
                description="Persist one qualified lead record into durable memory for ledger export.",
                properties={
                    "record": {
                        "type": "object",
                        "description": "Qualified lead record payload derived from evaluation output.",
                        "additionalProperties": True,
                    }
                },
                required=("record",),
                handler=self._handle_save_qualified_lead,
            ),
            _tool(
                key="prospecting.complete_search",
                name="complete_search",
                description="Persist completion metadata for a Google Maps search and clear the in-progress pointer.",
                properties={
                    "search_index": {"type": "integer", "description": "Completed search index."},
                    "query": {"type": "string", "description": "Search query."},
                    "location": {"type": "string", "description": "Search location."},
                    "listings_found": {
                        "type": "integer",
                        "description": "Number of listings seen for the search.",
                    },
                },
                required=("search_index", "query", "location", "listings_found"),
                handler=self._handle_complete_search,
            ),
        )

    def _execute_tool(self, tool_call):  # type: ignore[override]
        result = super()._execute_tool(tool_call)
        if tool_call.tool_key in {
            SEARCH_OR_SUMMARIZE,
            "prospecting.start_search",
            "prospecting.record_listing_result",
            "prospecting.save_qualified_lead",
            "prospecting.complete_search",
        }:
            self.refresh_parameters()
        return result

    def _allow_auto_reset_after_tool_result(self, result: ToolResult) -> bool:
        return result.tool_key in self._RESET_SAFE_TOOL_KEYS

    def _handle_evaluate_company(self, arguments: dict[str, Any]) -> dict[str, Any]:
        payload = self._run_json_subcall(
            system_prompt=self._config.eval_system_prompt.replace(
                "{{qualification_threshold}}",
                str(self._config.qualification_threshold),
            ),
            sections=(
                AgentParameterSection(
                    title="Company Description",
                    content=self._memory_store.read_company_description() or DEFAULT_COMPANY_DESCRIPTION,
                ),
                AgentParameterSection(
                    title="Listing Data",
                    content=json.dumps(arguments["listing_data"], indent=2, sort_keys=True),
                ),
            ),
            label="evaluate_company",
        )
        if not isinstance(payload, dict):
            raise ValidationError("EVALUATE_COMPANY must return a JSON object.")
        return payload

    def _handle_search_or_summarize(self, arguments: dict[str, Any]) -> dict[str, Any]:
        del arguments
        state = self._memory_store.read_state()
        next_index = state.last_completed_search_index + 1
        if next_index >= self._config.max_searches_per_run:
            return {"action": "no_next_query", "reason": "max_searches_per_run_reached"}

        unsummarized = [
            record
            for record in state.searches_completed
            if record.index > state.searches_summarized_through
        ]
        summary_text = state.search_history_summary
        action = "continued"
        if unsummarized and len(unsummarized) >= self._config.summarize_at_x:
            summary_payload = self._run_json_subcall(
                system_prompt=SEARCH_SUMMARY_SYSTEM_PROMPT,
                sections=(
                    AgentParameterSection(
                        title="Company Description",
                        content=self._memory_store.read_company_description() or DEFAULT_COMPANY_DESCRIPTION,
                    ),
                    AgentParameterSection(title="Prior Summary", content=summary_text or "(none)"),
                    AgentParameterSection(
                        title="New Searches",
                        content=json.dumps([record.as_dict() for record in unsummarized], indent=2, sort_keys=True),
                    ),
                ),
                label="search_summary",
            )
            summary_text = str(summary_payload.get("summary", "")).strip() or summary_text
            summarized_through_index = max(record.index for record in unsummarized)
            retained = tuple(
                record for record in state.searches_completed if record.index > summarized_through_index
            )
            self._memory_store.write_state(
                ProspectingState(
                    run_id=state.run_id,
                    company_description=state.company_description,
                    searches_completed=retained,
                    searches_summarized_through=summarized_through_index,
                    search_history_summary=summary_text,
                    last_completed_search_index=state.last_completed_search_index,
                    current_search_in_progress=state.current_search_in_progress,
                    qualified_leads_posted=state.qualified_leads_posted,
                    disqualified_leads_count=state.disqualified_leads_count,
                    session_reset_count=state.session_reset_count,
                    run_status=state.run_status,
                    error_log=state.error_log,
                )
            )
            state = self._memory_store.read_state()
            action = "summarized_and_continued"

        next_query_payload = self._run_json_subcall(
            system_prompt=NEXT_QUERY_SYSTEM_PROMPT,
            sections=(
                AgentParameterSection(
                    title="Company Description",
                    content=self._memory_store.read_company_description() or DEFAULT_COMPANY_DESCRIPTION,
                ),
                AgentParameterSection(
                    title="Search History Summary",
                    content=summary_text or "(none)",
                ),
                AgentParameterSection(
                    title="Recent Searches",
                    content=json.dumps(
                        [record.as_dict() for record in state.searches_completed[-10:]],
                        indent=2,
                        sort_keys=True,
                    ),
                ),
                AgentParameterSection(
                    title="Last Completed Search Index",
                    content=str(state.last_completed_search_index),
                ),
            ),
            label="next_maps_query",
        )
        next_query = str(next_query_payload.get("query", "")).strip()
        next_location = str(next_query_payload.get("location", "")).strip()
        if not next_query or not next_location:
            return {"action": "no_next_query", "reason": "planner_returned_blank"}
        payload: dict[str, Any] = {
            "action": action,
            "next_query": next_query,
            "next_location": next_location,
            "next_search_index": next_index,
        }
        if action == "summarized_and_continued":
            payload["new_summary"] = summary_text
            payload["summarized_through_index"] = state.searches_summarized_through
        return payload

    def _handle_start_search(self, arguments: dict[str, Any]) -> dict[str, Any]:
        state = self._memory_store.read_state()
        progress = {
            "index": int(arguments["index"]),
            "query": str(arguments["query"]),
            "location": str(arguments["location"]),
            "last_listing_position": -1,
        }
        self._memory_store.write_state(
            ProspectingState.from_dict({**state.as_dict(), "current_search_in_progress": progress})
        )
        return progress

    def _handle_record_listing_result(self, arguments: dict[str, Any]) -> dict[str, Any]:
        state = self._memory_store.read_state()
        progress = state.current_search_in_progress
        if progress is None or progress.index != int(arguments["search_index"]):
            raise StateError("record_listing_result requires an active matching search.")
        disqualified_count = state.disqualified_leads_count
        if str(arguments["verdict"]).upper() == "DISQUALIFIED":
            disqualified_count += 1
        next_state = ProspectingState(
            run_id=state.run_id,
            company_description=state.company_description,
            searches_completed=state.searches_completed,
            searches_summarized_through=state.searches_summarized_through,
            search_history_summary=state.search_history_summary,
            last_completed_search_index=state.last_completed_search_index,
            current_search_in_progress=type(progress)(
                index=progress.index,
                query=progress.query,
                location=progress.location,
                last_listing_position=int(arguments["listing_position"]),
            ),
            qualified_leads_posted=state.qualified_leads_posted,
            disqualified_leads_count=disqualified_count,
            session_reset_count=state.session_reset_count,
            run_status=state.run_status,
            error_log=state.error_log,
        )
        self._memory_store.write_state(next_state)
        return next_state.current_search_in_progress.as_dict() if next_state.current_search_in_progress else {}

    def _handle_save_qualified_lead(self, arguments: dict[str, Any]) -> dict[str, Any]:
        state = self._memory_store.read_state()
        raw_record = dict(arguments["record"])
        lead = QualifiedLeadRecord(
            record_type=str(raw_record.get("record_type", self._config.sink_record_type)),
            run_id=str(raw_record.get("run_id", state.run_id)),
            business_name=str(raw_record["business_name"]),
            maps_url=str(raw_record["maps_url"]),
            website_url=str(raw_record["website_url"]) if raw_record.get("website_url") is not None else None,
            score=int(raw_record["score"]),
            verdict=str(raw_record.get("verdict", "QUALIFIED")),
            score_breakdown=dict(raw_record.get("score_breakdown", {})),
            pitch_hook=str(raw_record["pitch_hook"]) if raw_record.get("pitch_hook") is not None else None,
            search_query=str(raw_record["search_query"]),
            search_index=int(raw_record["search_index"]),
            evaluated_at=str(raw_record.get("evaluated_at", utcnow())),
            raw_listing=dict(raw_record.get("raw_listing", {})),
        )
        self._memory_store.append_qualified_lead(lead)
        self._memory_store.update_state(qualified_leads_posted=state.qualified_leads_posted + 1)
        return lead.as_dict()

    def _handle_complete_search(self, arguments: dict[str, Any]) -> dict[str, Any]:
        state = self._memory_store.read_state()
        search_index = int(arguments["search_index"])
        progress = state.current_search_in_progress
        listings_evaluated = 0
        if progress is not None and progress.index == search_index:
            listings_evaluated = progress.last_listing_position + 1
        record = SearchRecord(
            index=search_index,
            query=str(arguments["query"]),
            location=str(arguments["location"]),
            listings_found=int(arguments["listings_found"]),
            listings_evaluated=max(0, listings_evaluated),
            qualified_count=self._memory_store.qualified_count_for_search(search_index),
            completed_at=utcnow(),
        )
        next_state = ProspectingState(
            run_id=state.run_id,
            company_description=state.company_description,
            searches_completed=(*state.searches_completed, record),
            searches_summarized_through=state.searches_summarized_through,
            search_history_summary=state.search_history_summary,
            last_completed_search_index=search_index,
            current_search_in_progress=None,
            qualified_leads_posted=state.qualified_leads_posted,
            disqualified_leads_count=state.disqualified_leads_count,
            session_reset_count=state.session_reset_count,
            run_status=state.run_status,
            error_log=state.error_log,
        )
        self._memory_store.write_state(next_state)
        return record.as_dict()

    def _run_json_subcall(
        self,
        *,
        system_prompt: str,
        sections: Sequence[AgentParameterSection],
        label: str,
    ) -> dict[str, Any]:
        if self._json_subcall_runner is not None:
            payload = self._json_subcall_runner(system_prompt, sections, label)
            if not isinstance(payload, dict):
                raise ValidationError(f"{label} runner must return a dict.")
            return payload
        response = self._model.generate_turn(
            AgentModelRequest(
                agent_name=f"{self.name}.{label}",
                system_prompt=system_prompt,
                parameter_sections=tuple(sections),
                transcript=(),
                tools=(),
            )
        )
        if not response.assistant_message.strip():
            raise ValidationError(f"{label} returned empty assistant content.")
        return _parse_json_object(response.assistant_message)
__all__ = [
    "GoogleMapsProspectingAgent",
    "ProspectingAgentConfig",
    "ProspectingMemoryStore",
    "QualifiedLeadRecord",
]
