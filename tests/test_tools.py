"""Tests for the canonical tool registry."""

from __future__ import annotations

import unittest
from copy import deepcopy

from harnessiq.shared.tools import (
    ADD_NUMBERS,
    CONTROL_PAUSE_FOR_HUMAN,
    ECHO_TEXT,
    FILESYSTEM_APPEND_TEXT_FILE,
    FILESYSTEM_COPY_PATH,
    FILESYSTEM_GET_CURRENT_DIRECTORY,
    FILESYSTEM_LIST_DIRECTORY,
    FILESYSTEM_MAKE_DIRECTORY,
    FILESYSTEM_PATH_EXISTS,
    FILESYSTEM_READ_TEXT_FILE,
    FILESYSTEM_WRITE_TEXT_FILE,
    HEAVY_COMPACTION,
    LOG_COMPACTION,
    PROMPT_CREATE_SYSTEM_PROMPT,
    REASONING_ABDUCTIVE_REASONING,
    REASONING_ANALOGY_GENERATION,
    REASONING_ASSUMPTION_SURFACING,
    REASONING_BACKCASTING,
    REASONING_BACKWARD_CHAINING,
    REASONING_BIAS_DETECTION,
    REASONING_BLINDSPOT_CHECK,
    REASONING_BOTTLENECK_IDENTIFICATION,
    REASONING_BUTTERFLY_EFFECT_TRACE,
    REASONING_CONFIDENCE_CALIBRATION,
    REASONING_CONSTRAINT_MAPPING,
    REASONING_COST_BENEFIT_ANALYSIS,
    REASONING_CYNEFIN_CATEGORIZATION,
    REASONING_DEVILS_ADVOCATE,
    REASONING_DIALECTICAL_REASONING,
    REASONING_DIVIDE_AND_CONQUER,
    REASONING_FACT_CHECKING,
    REASONING_FALSIFICATION_TEST,
    REASONING_FEEDBACK_LOOP_IDENTIFICATION,
    REASONING_FIRST_PRINCIPLES,
    REASONING_FORWARD_CHAINING,
    REASONING_GRAPH_OF_THOUGHTS,
    REASONING_HYPOTHESIS_GENERATION,
    REASONING_LATERAL_THINKING,
    REASONING_MEANS_END_ANALYSIS,
    REASONING_MORPHOLOGICAL_ANALYSIS,
    REASONING_NETWORK_MAPPING,
    REASONING_PARETO_ANALYSIS,
    REASONING_PERSONA_ADOPTION,
    REASONING_PLAN_AND_SOLVE,
    REASONING_POST_MORTEM,
    REASONING_PRE_MORTEM,
    REASONING_PROVOCATION_OPERATION,
    REASONING_RED_TEAMING,
    REASONING_ROLE_STORMING,
    REASONING_ROOT_CAUSE_ANALYSIS,
    REASONING_SCAMPER,
    REASONING_SCENARIO_PLANNING,
    REASONING_SECOND_ORDER_EFFECTS,
    REASONING_SELF_CRITIQUE,
    REASONING_SIX_THINKING_HATS,
    REASONING_STAKEHOLDER_ANALYSIS,
    REASONING_STEELMANNING,
    REASONING_STEP_BY_STEP,
    REASONING_SWOT_ANALYSIS,
    REASONING_TRADEOFF_EVALUATION,
    REASONING_TREE_OF_THOUGHTS,
    REASONING_TREND_EXTRAPOLATION,
    REASONING_VARIABLE_ISOLATION,
    REASONING_WORST_IDEA_GENERATION,
    RECORDS_COUNT_BY_FIELD,
    RECORDS_FILTER_RECORDS,
    RECORDS_LIMIT_RECORDS,
    RECORDS_SELECT_FIELDS,
    RECORDS_SORT_RECORDS,
    RECORDS_UNIQUE_RECORDS,
    REMOVE_TOOL_RESULTS,
    REMOVE_TOOLS,
    RegisteredTool,
    TEXT_NORMALIZE_WHITESPACE,
    TEXT_REGEX_EXTRACT,
    TEXT_TRUNCATE_TEXT,
    ToolDefinition,
)
from harnessiq.tools.registry import (
    DuplicateToolError,
    ToolRegistry,
    ToolValidationError,
    UnknownToolError,
    create_builtin_registry,
)


def _constant_handler(arguments: dict[str, object]) -> dict[str, object]:
    return {"arguments": arguments}


class ToolRegistryTests(unittest.TestCase):
    def test_builtin_registry_keeps_stable_key_order(self) -> None:
        registry = create_builtin_registry()

        self.assertEqual(
            registry.keys(),
            (
                ECHO_TEXT,
                ADD_NUMBERS,
                REMOVE_TOOL_RESULTS,
                REMOVE_TOOLS,
                HEAVY_COMPACTION,
                LOG_COMPACTION,
                TEXT_NORMALIZE_WHITESPACE,
                TEXT_REGEX_EXTRACT,
                TEXT_TRUNCATE_TEXT,
                RECORDS_SELECT_FIELDS,
                RECORDS_FILTER_RECORDS,
                RECORDS_SORT_RECORDS,
                RECORDS_LIMIT_RECORDS,
                RECORDS_UNIQUE_RECORDS,
                RECORDS_COUNT_BY_FIELD,
                CONTROL_PAUSE_FOR_HUMAN,
                PROMPT_CREATE_SYSTEM_PROMPT,
                FILESYSTEM_GET_CURRENT_DIRECTORY,
                FILESYSTEM_PATH_EXISTS,
                FILESYSTEM_LIST_DIRECTORY,
                FILESYSTEM_READ_TEXT_FILE,
                FILESYSTEM_WRITE_TEXT_FILE,
                FILESYSTEM_APPEND_TEXT_FILE,
                FILESYSTEM_MAKE_DIRECTORY,
                FILESYSTEM_COPY_PATH,
                # reasoning lens tools — registered in create_reasoning_tools() order
                REASONING_STEP_BY_STEP,
                REASONING_TREE_OF_THOUGHTS,
                REASONING_GRAPH_OF_THOUGHTS,
                REASONING_FORWARD_CHAINING,
                REASONING_BACKWARD_CHAINING,
                REASONING_PLAN_AND_SOLVE,
                REASONING_MEANS_END_ANALYSIS,
                REASONING_DIVIDE_AND_CONQUER,
                REASONING_FIRST_PRINCIPLES,
                REASONING_ROOT_CAUSE_ANALYSIS,
                REASONING_ASSUMPTION_SURFACING,
                REASONING_SWOT_ANALYSIS,
                REASONING_COST_BENEFIT_ANALYSIS,
                REASONING_PARETO_ANALYSIS,
                REASONING_CONSTRAINT_MAPPING,
                REASONING_VARIABLE_ISOLATION,
                REASONING_DEVILS_ADVOCATE,
                REASONING_STEELMANNING,
                REASONING_RED_TEAMING,
                REASONING_PERSONA_ADOPTION,
                REASONING_SIX_THINKING_HATS,
                REASONING_STAKEHOLDER_ANALYSIS,
                REASONING_DIALECTICAL_REASONING,
                REASONING_BLINDSPOT_CHECK,
                REASONING_SCAMPER,
                REASONING_LATERAL_THINKING,
                REASONING_ANALOGY_GENERATION,
                REASONING_MORPHOLOGICAL_ANALYSIS,
                REASONING_WORST_IDEA_GENERATION,
                REASONING_PROVOCATION_OPERATION,
                REASONING_ROLE_STORMING,
                REASONING_SECOND_ORDER_EFFECTS,
                REASONING_FEEDBACK_LOOP_IDENTIFICATION,
                REASONING_CYNEFIN_CATEGORIZATION,
                REASONING_NETWORK_MAPPING,
                REASONING_BUTTERFLY_EFFECT_TRACE,
                REASONING_BOTTLENECK_IDENTIFICATION,
                REASONING_SCENARIO_PLANNING,
                REASONING_PRE_MORTEM,
                REASONING_POST_MORTEM,
                REASONING_TREND_EXTRAPOLATION,
                REASONING_BACKCASTING,
                REASONING_SELF_CRITIQUE,
                REASONING_BIAS_DETECTION,
                REASONING_FACT_CHECKING,
                REASONING_CONFIDENCE_CALIBRATION,
                REASONING_TRADEOFF_EVALUATION,
                REASONING_HYPOTHESIS_GENERATION,
                REASONING_FALSIFICATION_TEST,
                REASONING_ABDUCTIVE_REASONING,
            ),
        )

    def test_definitions_expose_metadata_without_handlers(self) -> None:
        registry = create_builtin_registry()

        definitions = registry.definitions([ECHO_TEXT])

        self.assertEqual(len(definitions), 1)
        payload = definitions[0].as_dict()
        self.assertEqual(payload["key"], ECHO_TEXT)
        self.assertNotIn("handler", payload)

    def test_execute_runs_registered_tool(self) -> None:
        registry = create_builtin_registry()

        echo_result = registry.execute(ECHO_TEXT, {"text": "hello"})
        add_result = registry.execute(ADD_NUMBERS, {"left": 1, "right": 2.5})
        normalize_result = registry.execute(TEXT_NORMALIZE_WHITESPACE, {"text": "hello   world"})
        limit_result = registry.execute(
            RECORDS_LIMIT_RECORDS,
            {"records": [{"id": 1}, {"id": 2}, {"id": 3}], "limit": 2},
        )

        self.assertEqual(echo_result.output, {"text": "hello"})
        self.assertEqual(add_result.output, {"sum": 3.5})
        self.assertEqual(normalize_result.output, {"text": "hello world"})
        self.assertEqual(limit_result.output["records"], [{"id": 1}, {"id": 2}])

    def test_execute_rejects_missing_required_arguments(self) -> None:
        registry = create_builtin_registry()

        with self.assertRaises(ToolValidationError):
            registry.execute(ADD_NUMBERS, {"left": 1})

    def test_execute_rejects_unexpected_arguments(self) -> None:
        registry = create_builtin_registry()

        with self.assertRaises(ToolValidationError):
            registry.execute(ECHO_TEXT, {"text": "hello", "extra": True})

    def test_duplicate_tool_keys_raise_clear_error(self) -> None:
        definition = ToolDefinition(
            key=ECHO_TEXT,
            name="duplicate_echo",
            description="Duplicate key for validation.",
            input_schema={"type": "object"},
        )
        duplicate_tool = RegisteredTool(definition=definition, handler=_constant_handler)

        with self.assertRaises(DuplicateToolError):
            ToolRegistry([duplicate_tool, duplicate_tool])

    def test_unknown_tool_raises_clear_error(self) -> None:
        registry = create_builtin_registry()

        with self.assertRaises(UnknownToolError):
            registry.execute("missing.tool", {})

    def test_as_dict_returns_copy_of_input_schema(self) -> None:
        registry = create_builtin_registry()

        payload = registry.definitions([ECHO_TEXT])[0].as_dict()
        copied_schema = deepcopy(payload["input_schema"])
        copied_schema["properties"]["text"]["description"] = "changed"

        original_payload = registry.definitions([ECHO_TEXT])[0].as_dict()

        self.assertNotEqual(copied_schema, original_payload["input_schema"])

    def test_registry_inspect_includes_parameters_and_function_metadata(self) -> None:
        definition = ToolDefinition(
            key="custom.inspectable",
            name="inspectable",
            description="Inspect me.",
            input_schema={
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Input text."},
                    "count": {"type": "integer", "description": "Number of times."},
                },
                "required": ["text"],
                "additionalProperties": False,
            },
        )
        registry = ToolRegistry([RegisteredTool(definition=definition, handler=_constant_handler)])

        payload = registry.inspect(["custom.inspectable"])[0]

        self.assertEqual(payload["key"], "custom.inspectable")
        self.assertEqual(payload["required_parameters"], ["text"])
        self.assertFalse(payload["additional_properties"])
        self.assertEqual(
            payload["parameters"],
            [
                {
                    "name": "text",
                    "required": True,
                    "type": "string",
                    "description": "Input text.",
                    "schema": {"type": "string", "description": "Input text."},
                },
                {
                    "name": "count",
                    "required": False,
                    "type": "integer",
                    "description": "Number of times.",
                    "schema": {"type": "integer", "description": "Number of times."},
                },
            ],
        )
        self.assertEqual(payload["function"]["module"], __name__)
        self.assertEqual(payload["function"]["qualname"], "_constant_handler")


if __name__ == "__main__":
    unittest.main()
