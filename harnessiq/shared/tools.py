"""Shared tool constants, aliases, and runtime data models."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Protocol, Sequence

from harnessiq.shared.validated import NonEmptyString, ToolDescription

JsonObject = dict[str, Any]
ToolArguments = dict[str, Any]

ECHO_TEXT = "core.echo_text"
ADD_NUMBERS = "core.add_numbers"
REMOVE_TOOL_RESULTS = "context.remove_tool_results"
REMOVE_TOOLS = "context.remove_tools"
HEAVY_COMPACTION = "context.heavy_compaction"
LOG_COMPACTION = "context.log_compaction"
CONTEXT_SUMMARIZE_HEADLINE = "context.summarize.headline"
CONTEXT_SUMMARIZE_CHRONOLOGICAL = "context.summarize.chronological"
CONTEXT_SUMMARIZE_STATE_SNAPSHOT = "context.summarize.state_snapshot"
CONTEXT_SUMMARIZE_DECISIONS = "context.summarize.decisions"
CONTEXT_SUMMARIZE_ERRORS = "context.summarize.errors"
CONTEXT_SUMMARIZE_EXTRACTED_DATA = "context.summarize.extracted_data"
CONTEXT_SUMMARIZE_GOALS_AND_GAPS = "context.summarize.goals_and_gaps"
CONTEXT_SUMMARIZE_ENTITIES = "context.summarize.entities"
CONTEXT_SUMMARIZE_OPEN_QUESTIONS = "context.summarize.open_questions"
CONTEXT_STRUCT_TRUNCATE = "context.struct.truncate"
CONTEXT_STRUCT_STRIP_OUTPUTS = "context.struct.strip_outputs"
CONTEXT_STRUCT_DEDUPLICATE = "context.struct.deduplicate"
CONTEXT_STRUCT_REORDER = "context.struct.reorder"
CONTEXT_STRUCT_COLLAPSE_CHAIN = "context.struct.collapse_chain"
CONTEXT_STRUCT_REDACT = "context.struct.redact"
CONTEXT_STRUCT_MERGE_SECTIONS = "context.struct.merge_sections"
CONTEXT_STRUCT_WINDOW_SLICE = "context.struct.window_slice"
CONTEXT_STRUCT_FOLD_BY_TOOL_KEY = "context.struct.fold_by_tool_key"
CONTEXT_SELECT_EXTRACT_AND_COLLAPSE = "context.select.extract_and_collapse"
CONTEXT_SELECT_FILTER_BY_TOOL_KEY = "context.select.filter_by_tool_key"
CONTEXT_SELECT_PROMOTE_AND_STRIP = "context.select.promote_and_strip"
CONTEXT_SELECT_ANNOTATE_ENTRY = "context.select.annotate_entry"
CONTEXT_SELECT_CHECKPOINT = "context.select.checkpoint"
CONTEXT_SELECT_KEEP_BY_TAG = "context.select.keep_by_tag"
CONTEXT_SELECT_SPLIT_AND_PROMOTE = "context.select.split_and_promote"
CONTEXT_PARAM_INJECT_SECTION = "context.param.inject_section"
CONTEXT_PARAM_UPDATE_SECTION = "context.param.update_section"
CONTEXT_PARAM_APPEND_MEMORY_FIELD = "context.param.append_memory_field"
CONTEXT_PARAM_OVERWRITE_MEMORY_FIELD = "context.param.overwrite_memory_field"
CONTEXT_PARAM_WRITE_ONCE_MEMORY_FIELD = "context.param.write_once_memory_field"
CONTEXT_PARAM_INJECT_DIRECTIVE = "context.param.inject_directive"
CONTEXT_PARAM_CLEAR_MEMORY_FIELD = "context.param.clear_memory_field"
CONTEXT_PARAM_BULK_WRITE_MEMORY = "context.param.bulk_write_memory"
CONTEXT_INJECT_SYNTHETIC_TOOL_RESULT = "context.inject.synthetic_tool_result"
CONTEXT_INJECT_ASSISTANT_NOTE = "context.inject.assistant_note"
CONTEXT_INJECT_TOOL_CALL_PAIR = "context.inject.tool_call_pair"
CONTEXT_INJECT_CONTEXT_BLOCK = "context.inject.context_block"
CONTEXT_INJECT_TASK_REMINDER = "context.inject.task_reminder"
CONTEXT_INJECT_REPLAY_MEMORY = "context.inject.replay_memory"
CONTEXT_INJECT_HANDOFF_BRIEF = "context.inject.handoff_brief"
CONTEXT_INJECT_PROGRESS_MARKER = "context.inject.progress_marker"
CONTEXT_SUMMARIZATION_TOOL_KEYS = (
    CONTEXT_SUMMARIZE_HEADLINE,
    CONTEXT_SUMMARIZE_CHRONOLOGICAL,
    CONTEXT_SUMMARIZE_STATE_SNAPSHOT,
    CONTEXT_SUMMARIZE_DECISIONS,
    CONTEXT_SUMMARIZE_ERRORS,
    CONTEXT_SUMMARIZE_EXTRACTED_DATA,
    CONTEXT_SUMMARIZE_GOALS_AND_GAPS,
    CONTEXT_SUMMARIZE_ENTITIES,
    CONTEXT_SUMMARIZE_OPEN_QUESTIONS,
)
CONTEXT_STRUCTURAL_TOOL_KEYS = (
    CONTEXT_STRUCT_TRUNCATE,
    CONTEXT_STRUCT_STRIP_OUTPUTS,
    CONTEXT_STRUCT_DEDUPLICATE,
    CONTEXT_STRUCT_REORDER,
    CONTEXT_STRUCT_COLLAPSE_CHAIN,
    CONTEXT_STRUCT_REDACT,
    CONTEXT_STRUCT_MERGE_SECTIONS,
    CONTEXT_STRUCT_WINDOW_SLICE,
    CONTEXT_STRUCT_FOLD_BY_TOOL_KEY,
)
CONTEXT_SELECTIVE_TOOL_KEYS = (
    CONTEXT_SELECT_EXTRACT_AND_COLLAPSE,
    CONTEXT_SELECT_FILTER_BY_TOOL_KEY,
    CONTEXT_SELECT_PROMOTE_AND_STRIP,
    CONTEXT_SELECT_ANNOTATE_ENTRY,
    CONTEXT_SELECT_CHECKPOINT,
    CONTEXT_SELECT_KEEP_BY_TAG,
    CONTEXT_SELECT_SPLIT_AND_PROMOTE,
)
CONTEXT_PARAMETER_TOOL_KEYS = (
    CONTEXT_PARAM_INJECT_SECTION,
    CONTEXT_PARAM_UPDATE_SECTION,
    CONTEXT_PARAM_APPEND_MEMORY_FIELD,
    CONTEXT_PARAM_OVERWRITE_MEMORY_FIELD,
    CONTEXT_PARAM_WRITE_ONCE_MEMORY_FIELD,
    CONTEXT_PARAM_INJECT_DIRECTIVE,
    CONTEXT_PARAM_CLEAR_MEMORY_FIELD,
    CONTEXT_PARAM_BULK_WRITE_MEMORY,
)
CONTEXT_TRANSCRIPT_INJECTION_TOOL_KEYS = (
    CONTEXT_INJECT_SYNTHETIC_TOOL_RESULT,
    CONTEXT_INJECT_ASSISTANT_NOTE,
    CONTEXT_INJECT_TOOL_CALL_PAIR,
    CONTEXT_INJECT_CONTEXT_BLOCK,
    CONTEXT_INJECT_TASK_REMINDER,
    CONTEXT_INJECT_REPLAY_MEMORY,
    CONTEXT_INJECT_HANDOFF_BRIEF,
    CONTEXT_INJECT_PROGRESS_MARKER,
)
CONTEXT_COMPACTION_TOOL_KEYS = (
    *CONTEXT_SUMMARIZATION_TOOL_KEYS,
    *CONTEXT_STRUCTURAL_TOOL_KEYS,
    *CONTEXT_SELECTIVE_TOOL_KEYS,
    *CONTEXT_TRANSCRIPT_INJECTION_TOOL_KEYS,
)
CONTEXT_TOOL_KEYS = (
    *CONTEXT_COMPACTION_TOOL_KEYS,
    *CONTEXT_PARAMETER_TOOL_KEYS,
)
TEXT_NORMALIZE_WHITESPACE = "text.normalize_whitespace"
TEXT_REGEX_EXTRACT = "text.regex_extract"
TEXT_TRUNCATE_TEXT = "text.truncate_text"
RECORDS_SELECT_FIELDS = "records.select_fields"
RECORDS_FILTER_RECORDS = "records.filter_records"
RECORDS_SORT_RECORDS = "records.sort_records"
RECORDS_LIMIT_RECORDS = "records.limit_records"
RECORDS_UNIQUE_RECORDS = "records.unique_records"
RECORDS_COUNT_BY_FIELD = "records.count_by_field"
CONTROL_PAUSE_FOR_HUMAN = "control.pause_for_human"
PROMPT_CREATE_SYSTEM_PROMPT = "prompt.create_system_prompt"
FILESYSTEM_GET_CURRENT_DIRECTORY = "filesystem.get_current_directory"
FILESYSTEM_PATH_EXISTS = "filesystem.path_exists"
FILESYSTEM_LIST_DIRECTORY = "filesystem.list_directory"
FILESYSTEM_READ_TEXT_FILE = "filesystem.read_text_file"
FILESYSTEM_WRITE_TEXT_FILE = "filesystem.write_text_file"
FILESYSTEM_APPEND_TEXT_FILE = "filesystem.append_text_file"
FILESYSTEM_MAKE_DIRECTORY = "filesystem.make_directory"
FILESYSTEM_COPY_PATH = "filesystem.copy_path"
BROWSER_NAVIGATE = "browser.navigate"
BROWSER_CLICK = "browser.click"
BROWSER_TYPE = "browser.type"
BROWSER_SELECT_OPTION = "browser.select_option"
BROWSER_HOVER = "browser.hover"
BROWSER_UPLOAD_FILE = "browser.upload_file"
BROWSER_PRESS_KEY = "browser.press_key"
BROWSER_SCROLL = "browser.scroll"
BROWSER_WAIT_FOR_ELEMENT = "browser.wait_for_element"
BROWSER_SCREENSHOT = "browser.screenshot"
BROWSER_VIEW_HTML = "browser.view_html"
BROWSER_GET_TEXT = "browser.get_text"
BROWSER_FIND_ELEMENT = "browser.find_element"
BROWSER_GET_CURRENT_URL = "browser.get_current_url"
BROWSER_EXTRACT_CONTENT = "browser.extract_content"
BROWSER_USE_REQUEST = "browser_use.request"
EVALUATE_COMPANY = "eval.evaluate_company"
SEARCH_OR_SUMMARIZE = "search.search_or_summarize"

# Reasoning tool key constants
REASON_BRAINSTORM = "reason.brainstorm"
REASON_CHAIN_OF_THOUGHT = "reason.chain_of_thought"
REASON_CRITIQUE = "reason.critique"

# Numeric bounds for injectable reasoning tools
REASON_BRAINSTORM_COUNT_MIN = 5
REASON_BRAINSTORM_COUNT_MAX = 30
REASON_BRAINSTORM_COUNT_DEFAULT = 10
REASON_BRAINSTORM_COUNT_PRESETS: dict[str, int] = {
    "small": 5,
    "medium": 15,
    "large": 30,
}
REASON_COT_STEPS_MIN = 3
REASON_COT_STEPS_MAX = 10
REASON_COT_STEPS_DEFAULT = 5

# Knowt tool key constants
KNOWT_CREATE_SCRIPT = "knowt.create_script"
KNOWT_CREATE_AVATAR_DESCRIPTION = "knowt.create_avatar_description"
KNOWT_CREATE_VIDEO = "knowt.create_video"
FILES_CREATE_FILE = "files.create_file"
FILES_EDIT_FILE = "files.edit_file"
# Reasoning lens tool key constants
REASONING_ABDUCTIVE_REASONING = "reasoning.abductive_reasoning"
REASONING_ANALOGY_GENERATION = "reasoning.analogy_generation"
REASONING_ASSUMPTION_SURFACING = "reasoning.assumption_surfacing"
REASONING_BACKCASTING = "reasoning.backcasting"
REASONING_BACKWARD_CHAINING = "reasoning.backward_chaining"
REASONING_BIAS_DETECTION = "reasoning.bias_detection"
REASONING_BLINDSPOT_CHECK = "reasoning.blindspot_check"
REASONING_BOTTLENECK_IDENTIFICATION = "reasoning.bottleneck_identification"
REASONING_BUTTERFLY_EFFECT_TRACE = "reasoning.butterfly_effect_trace"
REASONING_CONFIDENCE_CALIBRATION = "reasoning.confidence_calibration"
REASONING_CONSTRAINT_MAPPING = "reasoning.constraint_mapping"
REASONING_COST_BENEFIT_ANALYSIS = "reasoning.cost_benefit_analysis"
REASONING_CYNEFIN_CATEGORIZATION = "reasoning.cynefin_categorization"
REASONING_DEVILS_ADVOCATE = "reasoning.devils_advocate"
REASONING_DIALECTICAL_REASONING = "reasoning.dialectical_reasoning"
REASONING_DIVIDE_AND_CONQUER = "reasoning.divide_and_conquer"
REASONING_FACT_CHECKING = "reasoning.fact_checking"
REASONING_FALSIFICATION_TEST = "reasoning.falsification_test"
REASONING_FEEDBACK_LOOP_IDENTIFICATION = "reasoning.feedback_loop_identification"
REASONING_FIRST_PRINCIPLES = "reasoning.first_principles"
REASONING_FORWARD_CHAINING = "reasoning.forward_chaining"
REASONING_GRAPH_OF_THOUGHTS = "reasoning.graph_of_thoughts"
REASONING_HYPOTHESIS_GENERATION = "reasoning.hypothesis_generation"
REASONING_LATERAL_THINKING = "reasoning.lateral_thinking"
REASONING_MEANS_END_ANALYSIS = "reasoning.means_end_analysis"
REASONING_MORPHOLOGICAL_ANALYSIS = "reasoning.morphological_analysis"
REASONING_NETWORK_MAPPING = "reasoning.network_mapping"
REASONING_PARETO_ANALYSIS = "reasoning.pareto_analysis"
REASONING_PERSONA_ADOPTION = "reasoning.persona_adoption"
REASONING_PLAN_AND_SOLVE = "reasoning.plan_and_solve"
REASONING_POST_MORTEM = "reasoning.post_mortem"
REASONING_PRE_MORTEM = "reasoning.pre_mortem"
REASONING_PROVOCATION_OPERATION = "reasoning.provocation_operation"
REASONING_RED_TEAMING = "reasoning.red_teaming"
REASONING_ROLE_STORMING = "reasoning.role_storming"
REASONING_ROOT_CAUSE_ANALYSIS = "reasoning.root_cause_analysis"
REASONING_SCAMPER = "reasoning.scamper"
REASONING_SCENARIO_PLANNING = "reasoning.scenario_planning"
REASONING_SECOND_ORDER_EFFECTS = "reasoning.second_order_effects"
REASONING_SELF_CRITIQUE = "reasoning.self_critique"
REASONING_SIX_THINKING_HATS = "reasoning.six_thinking_hats"
REASONING_STAKEHOLDER_ANALYSIS = "reasoning.stakeholder_analysis"
REASONING_STEELMANNING = "reasoning.steelmanning"
REASONING_STEP_BY_STEP = "reasoning.step_by_step"
REASONING_SWOT_ANALYSIS = "reasoning.swot_analysis"
REASONING_TRADEOFF_EVALUATION = "reasoning.tradeoff_evaluation"
REASONING_TREE_OF_THOUGHTS = "reasoning.tree_of_thoughts"
REASONING_TREND_EXTRAPOLATION = "reasoning.trend_extrapolation"
REASONING_VARIABLE_ISOLATION = "reasoning.variable_isolation"
REASONING_WORST_IDEA_GENERATION = "reasoning.worst_idea_generation"

# ExaOutreach agent internal tool key constants
EXA_OUTREACH_LIST_TEMPLATES = "exa_outreach.list_templates"
EXA_OUTREACH_GET_TEMPLATE = "exa_outreach.get_template"
EXA_OUTREACH_CHECK_CONTACTED = "exa_outreach.check_contacted"
EXA_OUTREACH_LOG_LEAD = "exa_outreach.log_lead"
EXA_OUTREACH_LOG_EMAIL_SENT = "exa_outreach.log_email_sent"

# Leads agent internal tool key constants
LEADS_CHECK_SEEN = "leads.check_seen_lead"
LEADS_COMPACT_SEARCH_HISTORY = "leads.compact_search_history"
LEADS_LOG_SEARCH = "leads.log_search"
LEADS_SAVE_LEADS = "leads.save_leads"

# Provider tool key constants
ATTIO_REQUEST = "attio.request"
ARCADS_REQUEST = "arcads.request"
ARXIV_REQUEST = "arxiv.request"
CREATIFY_REQUEST = "creatify.request"
EXA_REQUEST = "exa.request"
INSTANTLY_REQUEST = "instantly.request"
INBOXAPP_REQUEST = "inboxapp.request"
LEMLIST_REQUEST = "lemlist.request"
OUTREACH_REQUEST = "outreach.request"
SNOVIO_REQUEST = "snovio.request"
LEADIQ_REQUEST = "leadiq.request"
SALESFORGE_REQUEST = "salesforge.request"
PHANTOMBUSTER_REQUEST = "phantombuster.request"
ZOOMINFO_REQUEST = "zoominfo.request"
PEOPLEDATALABS_REQUEST = "peopledatalabs.request"
PROXYCURL_REQUEST = "proxycurl.request"
CORESIGNAL_REQUEST = "coresignal.request"
APOLLO_REQUEST = "apollo.request"
ZEROBOUNCE_REQUEST = "zerobounce.request"
EXPANDI_REQUEST = "expandi.request"
SMARTLEAD_REQUEST = "smartlead.request"
LUSHA_REQUEST = "lusha.request"
GOOGLE_DRIVE_REQUEST = "google_drive.request"
PAPERCLIP_REQUEST = "paperclip.request"
SERPER_REQUEST = "serper.request"
INSTAGRAM_SEARCH_KEYWORD = "instagram.search_keyword"


@dataclass(frozen=True, slots=True)
class ToolDefinition:
    """Provider-agnostic metadata for a callable tool.

    Attributes:
        key: Unique tool identifier in ``namespace.name`` format.
        name: Short human-readable name (snake_case).
        description: What the tool does and when to use it.
        input_schema: JSON Schema object describing accepted arguments.
        tool_type: The execution type for this tool.  Currently only
            ``"function"`` is supported.  Additional types
            (``"computer_use"``, ``"code_interpreter"``, ``"multi_agent"``,
            etc.) will be introduced in future SDK releases.
    """

    key: str
    name: str
    description: str
    input_schema: JsonObject
    tool_type: str = "function"

    def __post_init__(self) -> None:
        object.__setattr__(self, "key", NonEmptyString(self.key, field_name="tool key"))
        object.__setattr__(self, "name", NonEmptyString(self.name, field_name="tool name"))
        object.__setattr__(
            self,
            "description",
            ToolDescription(self.description, field_name=f"tool description for {self.key}"),
        )
        if not isinstance(self.input_schema, dict):
            raise TypeError("ToolDefinition input_schema must be a JSON object mapping.")
        object.__setattr__(self, "input_schema", deepcopy(self.input_schema))

    def as_dict(self) -> JsonObject:
        """Return the canonical metadata without executable runtime state.

        ``tool_type`` is intentionally omitted — it is SDK metadata used to
        identify the tool's execution model, not part of the model API payload.
        Provider adapters serialise ``ToolDefinition`` to their own wire format
        independently of this method.
        """
        return {
            "key": self.key,
            "name": self.name,
            "description": self.description,
            "input_schema": deepcopy(self.input_schema),
        }

    def inspect(self) -> JsonObject:
        """Return a richer inspection payload for humans and tooling."""
        properties = self.input_schema.get("properties", {})
        if not isinstance(properties, dict):
            properties = {}
        required_parameters = self.input_schema.get("required", ())
        if not isinstance(required_parameters, list):
            required_parameters = list(required_parameters)
        required_parameter_names = [str(parameter) for parameter in required_parameters]
        required_lookup = set(required_parameter_names)
        property_names: set[str] = set()

        parameters: list[JsonObject] = []
        for parameter_name, parameter_schema in properties.items():
            normalized_name = str(parameter_name)
            property_names.add(normalized_name)
            normalized_schema = deepcopy(parameter_schema) if isinstance(parameter_schema, dict) else {}
            parameters.append(
                {
                    "name": normalized_name,
                    "required": normalized_name in required_lookup,
                    "type": normalized_schema.get("type"),
                    "description": normalized_schema.get("description"),
                    "schema": normalized_schema,
                }
            )

        for parameter_name in required_parameter_names:
            if parameter_name in property_names:
                continue
            parameters.append(
                {
                    "name": parameter_name,
                    "required": True,
                    "type": None,
                    "description": None,
                    "schema": {},
                }
            )

        payload = self.as_dict()
        payload["parameters"] = parameters
        payload["required_parameters"] = required_parameter_names
        payload["additional_properties"] = deepcopy(self.input_schema.get("additionalProperties", True))
        return payload


@dataclass(frozen=True, slots=True)
class ToolCall:
    """A concrete invocation request for a tool."""

    tool_key: str
    arguments: ToolArguments


@dataclass(frozen=True, slots=True)
class ToolResult:
    """A normalized local execution result."""

    tool_key: str
    output: Any


class ToolHandler(Protocol):
    """Callable runtime contract for built-in and custom tools."""

    def __call__(self, arguments: ToolArguments) -> object:
        """Execute the tool with normalized arguments."""


@dataclass(frozen=True, slots=True)
class RegisteredTool:
    """Bind canonical tool metadata to a local executable handler."""

    definition: ToolDefinition
    handler: ToolHandler

    @property
    def key(self) -> str:
        return self.definition.key

    def execute(self, arguments: ToolArguments) -> ToolResult:
        """Run the tool handler and normalize its output."""
        return ToolResult(tool_key=self.key, output=self.handler(arguments))

    def inspect(self) -> JsonObject:
        """Return serialized tool metadata including handler identity."""
        payload = self.definition.inspect()
        payload["function"] = _describe_handler(self.handler)
        return payload


def _describe_handler(handler: ToolHandler) -> JsonObject:
    handler_type = type(handler)
    module = getattr(handler, "__module__", handler_type.__module__)
    qualname = getattr(handler, "__qualname__", handler_type.__qualname__)
    name = getattr(handler, "__name__", qualname.split(".")[-1])
    return {
        "module": str(module),
        "qualname": str(qualname),
        "name": str(name),
    }


def build_grouped_operation_description(
    operations: Sequence[object],
    *,
    lead: str,
    usage: str | None = None,
    closing: str | None = None,
) -> str:
    """Build a stable grouped operation description for provider-backed request tools."""

    grouped: dict[str, list[str]] = {}
    for operation in operations:
        category = str(getattr(operation, "category"))
        summary = str(operation.summary())
        grouped.setdefault(category, []).append(summary)

    lines = [str(ToolDescription(lead, field_name="operation description lead"))]
    if usage is not None:
        lines.extend(["", str(ToolDescription(usage, field_name="operation description usage"))])
    for category, summaries in grouped.items():
        lines.append(f"{category}: {', '.join(summaries)}")
    if closing is not None:
        lines.append(str(ToolDescription(closing, field_name="operation description closing")))
    return str(ToolDescription("\n".join(lines), field_name="operation description"))


__all__ = [
    "ADD_NUMBERS",
    "ATTIO_REQUEST",
    "APOLLO_REQUEST",
    "ARCADS_REQUEST",
    "ARXIV_REQUEST",
    "BROWSER_CLICK",
    "BROWSER_EXTRACT_CONTENT",
    "BROWSER_FIND_ELEMENT",
    "BROWSER_GET_CURRENT_URL",
    "BROWSER_GET_TEXT",
    "BROWSER_HOVER",
    "BROWSER_NAVIGATE",
    "BROWSER_PRESS_KEY",
    "BROWSER_SCREENSHOT",
    "BROWSER_SCROLL",
    "BROWSER_SELECT_OPTION",
    "BROWSER_TYPE",
    "BROWSER_UPLOAD_FILE",
    "BROWSER_USE_REQUEST",
    "BROWSER_VIEW_HTML",
    "BROWSER_WAIT_FOR_ELEMENT",
    "CONTROL_PAUSE_FOR_HUMAN",
    "CORESIGNAL_REQUEST",
    "CREATIFY_REQUEST",
    "ECHO_TEXT",
    "EVALUATE_COMPANY",
    "EXA_OUTREACH_CHECK_CONTACTED",
    "EXA_OUTREACH_GET_TEMPLATE",
    "EXPANDI_REQUEST",
    "EXA_OUTREACH_LIST_TEMPLATES",
    "EXA_OUTREACH_LOG_EMAIL_SENT",
    "EXA_OUTREACH_LOG_LEAD",
    "EXA_REQUEST",
    "FILESYSTEM_APPEND_TEXT_FILE",
    "FILESYSTEM_COPY_PATH",
    "FILESYSTEM_GET_CURRENT_DIRECTORY",
    "FILESYSTEM_LIST_DIRECTORY",
    "FILESYSTEM_MAKE_DIRECTORY",
    "FILESYSTEM_PATH_EXISTS",
    "FILESYSTEM_READ_TEXT_FILE",
    "FILESYSTEM_WRITE_TEXT_FILE",
    "CONTEXT_COMPACTION_TOOL_KEYS",
    "CONTEXT_INJECT_ASSISTANT_NOTE",
    "CONTEXT_INJECT_CONTEXT_BLOCK",
    "CONTEXT_INJECT_HANDOFF_BRIEF",
    "CONTEXT_INJECT_PROGRESS_MARKER",
    "CONTEXT_INJECT_REPLAY_MEMORY",
    "CONTEXT_INJECT_SYNTHETIC_TOOL_RESULT",
    "CONTEXT_INJECT_TASK_REMINDER",
    "CONTEXT_INJECT_TOOL_CALL_PAIR",
    "CONTEXT_PARAMETER_TOOL_KEYS",
    "CONTEXT_PARAM_APPEND_MEMORY_FIELD",
    "CONTEXT_PARAM_BULK_WRITE_MEMORY",
    "CONTEXT_PARAM_CLEAR_MEMORY_FIELD",
    "CONTEXT_PARAM_INJECT_DIRECTIVE",
    "CONTEXT_PARAM_INJECT_SECTION",
    "CONTEXT_PARAM_OVERWRITE_MEMORY_FIELD",
    "CONTEXT_PARAM_UPDATE_SECTION",
    "CONTEXT_PARAM_WRITE_ONCE_MEMORY_FIELD",
    "CONTEXT_SELECTIVE_TOOL_KEYS",
    "CONTEXT_SELECT_ANNOTATE_ENTRY",
    "CONTEXT_SELECT_CHECKPOINT",
    "CONTEXT_SELECT_EXTRACT_AND_COLLAPSE",
    "CONTEXT_SELECT_FILTER_BY_TOOL_KEY",
    "CONTEXT_SELECT_KEEP_BY_TAG",
    "CONTEXT_SELECT_PROMOTE_AND_STRIP",
    "CONTEXT_SELECT_SPLIT_AND_PROMOTE",
    "CONTEXT_STRUCTURAL_TOOL_KEYS",
    "CONTEXT_STRUCT_COLLAPSE_CHAIN",
    "CONTEXT_STRUCT_DEDUPLICATE",
    "CONTEXT_STRUCT_FOLD_BY_TOOL_KEY",
    "CONTEXT_STRUCT_MERGE_SECTIONS",
    "CONTEXT_STRUCT_REDACT",
    "CONTEXT_STRUCT_REORDER",
    "CONTEXT_STRUCT_STRIP_OUTPUTS",
    "CONTEXT_STRUCT_TRUNCATE",
    "CONTEXT_STRUCT_WINDOW_SLICE",
    "CONTEXT_SUMMARIZATION_TOOL_KEYS",
    "CONTEXT_SUMMARIZE_CHRONOLOGICAL",
    "CONTEXT_SUMMARIZE_DECISIONS",
    "CONTEXT_SUMMARIZE_ENTITIES",
    "CONTEXT_SUMMARIZE_ERRORS",
    "CONTEXT_SUMMARIZE_EXTRACTED_DATA",
    "CONTEXT_SUMMARIZE_GOALS_AND_GAPS",
    "CONTEXT_SUMMARIZE_HEADLINE",
    "CONTEXT_SUMMARIZE_OPEN_QUESTIONS",
    "CONTEXT_SUMMARIZE_STATE_SNAPSHOT",
    "CONTEXT_TOOL_KEYS",
    "CONTEXT_TRANSCRIPT_INJECTION_TOOL_KEYS",
    "HEAVY_COMPACTION",
    "INSTANTLY_REQUEST",
    "INBOXAPP_REQUEST",
    "INSTAGRAM_SEARCH_KEYWORD",
    "JsonObject",
    "FILES_CREATE_FILE",
    "FILES_EDIT_FILE",
    "GOOGLE_DRIVE_REQUEST",
    "PAPERCLIP_REQUEST",
    "KNOWT_CREATE_AVATAR_DESCRIPTION",
    "KNOWT_CREATE_SCRIPT",
    "KNOWT_CREATE_VIDEO",
    "LEADIQ_REQUEST",
    "LEADS_CHECK_SEEN",
    "LEADS_COMPACT_SEARCH_HISTORY",
    "LEADS_LOG_SEARCH",
    "LEADS_SAVE_LEADS",
    "LUSHA_REQUEST",
    "LEMLIST_REQUEST",
    "LOG_COMPACTION",
    "OUTREACH_REQUEST",
    "PAPERCLIP_REQUEST",
    "PEOPLEDATALABS_REQUEST",
    "PHANTOMBUSTER_REQUEST",
    "PROMPT_CREATE_SYSTEM_PROMPT",
    "PROXYCURL_REQUEST",
    "REASON_BRAINSTORM",
    "REASON_BRAINSTORM_COUNT_DEFAULT",
    "REASON_BRAINSTORM_COUNT_MAX",
    "REASON_BRAINSTORM_COUNT_MIN",
    "REASON_BRAINSTORM_COUNT_PRESETS",
    "REASON_CHAIN_OF_THOUGHT",
    "REASON_COT_STEPS_DEFAULT",
    "REASON_COT_STEPS_MAX",
    "REASON_COT_STEPS_MIN",
    "REASON_CRITIQUE",
    "REASONING_ABDUCTIVE_REASONING",
    "REASONING_ANALOGY_GENERATION",
    "REASONING_ASSUMPTION_SURFACING",
    "REASONING_BACKCASTING",
    "REASONING_BACKWARD_CHAINING",
    "REASONING_BIAS_DETECTION",
    "REASONING_BLINDSPOT_CHECK",
    "REASONING_BOTTLENECK_IDENTIFICATION",
    "REASONING_BUTTERFLY_EFFECT_TRACE",
    "REASONING_CONFIDENCE_CALIBRATION",
    "REASONING_CONSTRAINT_MAPPING",
    "REASONING_COST_BENEFIT_ANALYSIS",
    "REASONING_CYNEFIN_CATEGORIZATION",
    "REASONING_DEVILS_ADVOCATE",
    "REASONING_DIALECTICAL_REASONING",
    "REASONING_DIVIDE_AND_CONQUER",
    "REASONING_FACT_CHECKING",
    "REASONING_FALSIFICATION_TEST",
    "REASONING_FEEDBACK_LOOP_IDENTIFICATION",
    "REASONING_FIRST_PRINCIPLES",
    "REASONING_FORWARD_CHAINING",
    "REASONING_GRAPH_OF_THOUGHTS",
    "REASONING_HYPOTHESIS_GENERATION",
    "REASONING_LATERAL_THINKING",
    "REASONING_MEANS_END_ANALYSIS",
    "REASONING_MORPHOLOGICAL_ANALYSIS",
    "REASONING_NETWORK_MAPPING",
    "REASONING_PARETO_ANALYSIS",
    "REASONING_PERSONA_ADOPTION",
    "REASONING_PLAN_AND_SOLVE",
    "REASONING_POST_MORTEM",
    "REASONING_PRE_MORTEM",
    "REASONING_PROVOCATION_OPERATION",
    "REASONING_RED_TEAMING",
    "REASONING_ROLE_STORMING",
    "REASONING_ROOT_CAUSE_ANALYSIS",
    "REASONING_SCAMPER",
    "REASONING_SCENARIO_PLANNING",
    "REASONING_SECOND_ORDER_EFFECTS",
    "REASONING_SELF_CRITIQUE",
    "REASONING_SIX_THINKING_HATS",
    "REASONING_STAKEHOLDER_ANALYSIS",
    "REASONING_STEELMANNING",
    "REASONING_STEP_BY_STEP",
    "REASONING_SWOT_ANALYSIS",
    "REASONING_TRADEOFF_EVALUATION",
    "REASONING_TREE_OF_THOUGHTS",
    "REASONING_TREND_EXTRAPOLATION",
    "REASONING_VARIABLE_ISOLATION",
    "REASONING_WORST_IDEA_GENERATION",
    "RECORDS_COUNT_BY_FIELD",
    "RECORDS_FILTER_RECORDS",
    "RECORDS_LIMIT_RECORDS",
    "RECORDS_SELECT_FIELDS",
    "RECORDS_SORT_RECORDS",
    "RECORDS_UNIQUE_RECORDS",
    "REMOVE_TOOL_RESULTS",
    "REMOVE_TOOLS",
    "RegisteredTool",
    "SALESFORGE_REQUEST",
    "SEARCH_OR_SUMMARIZE",
    "SERPER_REQUEST",
    "SMARTLEAD_REQUEST",
    "SNOVIO_REQUEST",
    "TEXT_NORMALIZE_WHITESPACE",
    "TEXT_REGEX_EXTRACT",
    "TEXT_TRUNCATE_TEXT",
    "ToolArguments",
    "ToolCall",
    "build_grouped_operation_description",
    "ToolDefinition",
    "ToolHandler",
    "ToolResult",
    "ZEROBOUNCE_REQUEST",
    "ZOOMINFO_REQUEST",
]
