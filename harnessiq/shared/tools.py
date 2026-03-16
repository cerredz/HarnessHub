"""Shared tool constants, aliases, and runtime data models."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Protocol

JsonObject = dict[str, Any]
ToolArguments = dict[str, Any]

ECHO_TEXT = "core.echo_text"
ADD_NUMBERS = "core.add_numbers"
REMOVE_TOOL_RESULTS = "context.remove_tool_results"
REMOVE_TOOLS = "context.remove_tools"
HEAVY_COMPACTION = "context.heavy_compaction"
LOG_COMPACTION = "context.log_compaction"
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

# Reasoning tool key constants
REASON_BRAINSTORM = "reason.brainstorm"
REASON_CHAIN_OF_THOUGHT = "reason.chain_of_thought"
REASON_CRITIQUE = "reason.critique"

# Knowt tool key constants
KNOWT_CREATE_SCRIPT = "knowt.create_script"
KNOWT_CREATE_AVATAR_DESCRIPTION = "knowt.create_avatar_description"
KNOWT_CREATE_VIDEO = "knowt.create_video"
KNOWT_CREATE_FILE = "knowt.create_file"
KNOWT_EDIT_FILE = "knowt.edit_file"
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

# Provider tool key constants
ARCADS_REQUEST = "arcads.request"
CREATIFY_REQUEST = "creatify.request"
EXA_REQUEST = "exa.request"
INSTANTLY_REQUEST = "instantly.request"
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


@dataclass(frozen=True, slots=True)
class ToolDefinition:
    """Provider-agnostic metadata for a callable tool."""

    key: str
    name: str
    description: str
    input_schema: JsonObject

    def as_dict(self) -> JsonObject:
        """Return the canonical metadata without executable runtime state."""
        return {
            "key": self.key,
            "name": self.name,
            "description": self.description,
            "input_schema": deepcopy(self.input_schema),
        }


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


__all__ = [
    "ADD_NUMBERS",
    "ARCADS_REQUEST",
    "CONTROL_PAUSE_FOR_HUMAN",
    "CORESIGNAL_REQUEST",
    "CREATIFY_REQUEST",
    "ECHO_TEXT",
    "EXA_REQUEST",
    "FILESYSTEM_APPEND_TEXT_FILE",
    "FILESYSTEM_COPY_PATH",
    "FILESYSTEM_GET_CURRENT_DIRECTORY",
    "FILESYSTEM_LIST_DIRECTORY",
    "FILESYSTEM_MAKE_DIRECTORY",
    "FILESYSTEM_PATH_EXISTS",
    "FILESYSTEM_READ_TEXT_FILE",
    "FILESYSTEM_WRITE_TEXT_FILE",
    "HEAVY_COMPACTION",
    "INSTANTLY_REQUEST",
    "JsonObject",
    "KNOWT_CREATE_AVATAR_DESCRIPTION",
    "KNOWT_CREATE_FILE",
    "KNOWT_CREATE_SCRIPT",
    "KNOWT_CREATE_VIDEO",
    "KNOWT_EDIT_FILE",
    "LEADIQ_REQUEST",
    "LEMLIST_REQUEST",
    "LOG_COMPACTION",
    "OUTREACH_REQUEST",
    "PEOPLEDATALABS_REQUEST",
    "PHANTOMBUSTER_REQUEST",
    "PROMPT_CREATE_SYSTEM_PROMPT",
    "PROXYCURL_REQUEST",
    "REASON_BRAINSTORM",
    "REASON_CHAIN_OF_THOUGHT",
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
    "SNOVIO_REQUEST",
    "TEXT_NORMALIZE_WHITESPACE",
    "TEXT_REGEX_EXTRACT",
    "TEXT_TRUNCATE_TEXT",
    "ToolArguments",
    "ToolCall",
    "ToolDefinition",
    "ToolHandler",
    "ToolResult",
    "ZOOMINFO_REQUEST",
]
