"""Tests for the injectable reasoning tools."""

from __future__ import annotations

import unittest

from harnessiq.shared.tools import REASON_BRAINSTORM, REASON_CHAIN_OF_THOUGHT, REASON_CRITIQUE
from harnessiq.tools import create_reasoning_tools
from harnessiq.tools.reasoning import brainstorm, chain_of_thought, critique
from harnessiq.tools.registry import ToolRegistry, ToolValidationError


class TestReasoningToolsRegistry(unittest.TestCase):
    """Verify factory output and registry integration."""

    def setUp(self) -> None:
        self.tools = create_reasoning_tools()

    def test_factory_returns_three_tools(self) -> None:
        self.assertEqual(len(self.tools), 3)

    def test_factory_returns_stable_key_order(self) -> None:
        keys = tuple(t.key for t in self.tools)
        self.assertEqual(keys, (REASON_BRAINSTORM, REASON_CHAIN_OF_THOUGHT, REASON_CRITIQUE))

    def test_tools_register_without_conflict(self) -> None:
        registry = ToolRegistry(self.tools)
        self.assertIn(REASON_BRAINSTORM, registry)
        self.assertIn(REASON_CHAIN_OF_THOUGHT, registry)
        self.assertIn(REASON_CRITIQUE, registry)

    def test_constants_exported_from_tools_package(self) -> None:
        from harnessiq.tools import REASON_BRAINSTORM as B
        from harnessiq.tools import REASON_CHAIN_OF_THOUGHT as C
        from harnessiq.tools import REASON_CRITIQUE as R

        self.assertEqual(B, "reason.brainstorm")
        self.assertEqual(C, "reason.chain_of_thought")
        self.assertEqual(R, "reason.critique")

    def test_tools_require_mandatory_arguments_via_registry(self) -> None:
        registry = ToolRegistry(self.tools)
        with self.assertRaises(ToolValidationError):
            registry.execute(REASON_BRAINSTORM, {})
        with self.assertRaises(ToolValidationError):
            registry.execute(REASON_CHAIN_OF_THOUGHT, {})
        with self.assertRaises(ToolValidationError):
            registry.execute(REASON_CRITIQUE, {})


class TestBrainstormTool(unittest.TestCase):
    """Unit tests for the brainstorm handler."""

    def test_minimal_call_returns_reasoning_instruction(self) -> None:
        result = brainstorm({"topic": "TikTok hooks"})
        self.assertIn("reasoning_instruction", result)
        self.assertIsInstance(result["reasoning_instruction"], str)

    def test_instruction_contains_topic(self) -> None:
        result = brainstorm({"topic": "product demo scripts"})
        self.assertIn("product demo scripts", result["reasoning_instruction"])

    def test_instruction_contains_default_count(self) -> None:
        result = brainstorm({"topic": "hooks"})
        self.assertIn("10", result["reasoning_instruction"])

    def test_custom_count_reflected_in_instruction(self) -> None:
        result = brainstorm({"topic": "hooks", "count": 15})
        self.assertIn("15", result["reasoning_instruction"])

    def test_context_included_when_provided(self) -> None:
        result = brainstorm({"topic": "hooks", "context": "B2B SaaS audience"})
        self.assertIn("B2B SaaS audience", result["reasoning_instruction"])

    def test_constraints_included_when_provided(self) -> None:
        result = brainstorm({"topic": "hooks", "constraints": "must be under 30 words"})
        self.assertIn("must be under 30 words", result["reasoning_instruction"])

    def test_context_absent_when_not_provided(self) -> None:
        result = brainstorm({"topic": "hooks"})
        self.assertNotIn("Context:", result["reasoning_instruction"])

    def test_constraints_absent_when_not_provided(self) -> None:
        result = brainstorm({"topic": "hooks"})
        self.assertNotIn("Constraints:", result["reasoning_instruction"])

    def test_count_below_minimum_raises(self) -> None:
        with self.assertRaises(ValueError, msg="count=4 should be rejected"):
            brainstorm({"topic": "hooks", "count": 4})

    def test_count_above_maximum_raises(self) -> None:
        with self.assertRaises(ValueError):
            brainstorm({"topic": "hooks", "count": 26})

    def test_count_at_minimum_boundary_accepted(self) -> None:
        result = brainstorm({"topic": "hooks", "count": 5})
        self.assertIn("5", result["reasoning_instruction"])

    def test_count_at_maximum_boundary_accepted(self) -> None:
        result = brainstorm({"topic": "hooks", "count": 25})
        self.assertIn("25", result["reasoning_instruction"])

    def test_empty_topic_raises(self) -> None:
        with self.assertRaises(ValueError):
            brainstorm({"topic": ""})

    def test_whitespace_only_topic_raises(self) -> None:
        with self.assertRaises(ValueError):
            brainstorm({"topic": "   "})

    def test_boolean_count_raises(self) -> None:
        with self.assertRaises(ValueError):
            brainstorm({"topic": "hooks", "count": True})

    def test_instruction_header_present(self) -> None:
        result = brainstorm({"topic": "hooks"})
        self.assertIn("[REASONING: BRAINSTORM]", result["reasoning_instruction"])


class TestChainOfThoughtTool(unittest.TestCase):
    """Unit tests for the chain_of_thought handler."""

    def test_minimal_call_returns_reasoning_instruction(self) -> None:
        result = chain_of_thought({"task": "decide the best script angle"})
        self.assertIn("reasoning_instruction", result)
        self.assertIsInstance(result["reasoning_instruction"], str)

    def test_instruction_contains_task(self) -> None:
        result = chain_of_thought({"task": "evaluate audience fit"})
        self.assertIn("evaluate audience fit", result["reasoning_instruction"])

    def test_default_steps_reflected(self) -> None:
        result = chain_of_thought({"task": "plan"})
        self.assertIn("5", result["reasoning_instruction"])

    def test_custom_steps_reflected(self) -> None:
        result = chain_of_thought({"task": "plan", "steps": 7})
        self.assertIn("7", result["reasoning_instruction"])

    def test_context_included_when_provided(self) -> None:
        result = chain_of_thought({"task": "plan", "context": "enterprise market"})
        self.assertIn("enterprise market", result["reasoning_instruction"])

    def test_context_absent_when_not_provided(self) -> None:
        result = chain_of_thought({"task": "plan"})
        self.assertNotIn("Context:", result["reasoning_instruction"])

    def test_steps_below_minimum_raises(self) -> None:
        with self.assertRaises(ValueError):
            chain_of_thought({"task": "plan", "steps": 2})

    def test_steps_above_maximum_raises(self) -> None:
        with self.assertRaises(ValueError):
            chain_of_thought({"task": "plan", "steps": 11})

    def test_steps_at_boundaries_accepted(self) -> None:
        result_min = chain_of_thought({"task": "plan", "steps": 3})
        result_max = chain_of_thought({"task": "plan", "steps": 10})
        self.assertIn("3", result_min["reasoning_instruction"])
        self.assertIn("10", result_max["reasoning_instruction"])

    def test_empty_task_raises(self) -> None:
        with self.assertRaises(ValueError):
            chain_of_thought({"task": ""})

    def test_instruction_header_present(self) -> None:
        result = chain_of_thought({"task": "plan"})
        self.assertIn("[REASONING: CHAIN OF THOUGHT]", result["reasoning_instruction"])


class TestCritiqueTool(unittest.TestCase):
    """Unit tests for the critique handler."""

    def test_minimal_call_returns_reasoning_instruction(self) -> None:
        result = critique({"content": "Here is my TikTok script draft."})
        self.assertIn("reasoning_instruction", result)
        self.assertIsInstance(result["reasoning_instruction"], str)

    def test_default_aspects_present(self) -> None:
        result = critique({"content": "draft script"})
        instruction = result["reasoning_instruction"]
        self.assertIn("correctness", instruction)
        self.assertIn("clarity", instruction)
        self.assertIn("completeness", instruction)
        self.assertIn("potential improvements", instruction)

    def test_custom_aspects_replace_defaults(self) -> None:
        result = critique({"content": "draft", "aspects": ["tone", "length"]})
        instruction = result["reasoning_instruction"]
        self.assertIn("tone", instruction)
        self.assertIn("length", instruction)
        self.assertNotIn("correctness", instruction)

    def test_content_preview_included(self) -> None:
        result = critique({"content": "short script text"})
        self.assertIn("short script text", result["reasoning_instruction"])

    def test_long_content_truncated_in_preview(self) -> None:
        long_content = "a" * 400
        result = critique({"content": long_content})
        self.assertIn("...", result["reasoning_instruction"])
        # The full content should NOT appear verbatim (it's been truncated)
        self.assertNotIn("a" * 400, result["reasoning_instruction"])

    def test_empty_content_raises(self) -> None:
        with self.assertRaises(ValueError):
            critique({"content": ""})

    def test_empty_aspects_list_raises(self) -> None:
        with self.assertRaises(ValueError):
            critique({"content": "draft", "aspects": []})

    def test_non_string_aspects_raises(self) -> None:
        with self.assertRaises(ValueError):
            critique({"content": "draft", "aspects": [1, 2, 3]})

    def test_non_list_aspects_raises(self) -> None:
        with self.assertRaises(ValueError):
            critique({"content": "draft", "aspects": "correctness"})

    def test_instruction_header_present(self) -> None:
        result = critique({"content": "draft"})
        self.assertIn("[REASONING: CRITIQUE]", result["reasoning_instruction"])

    def test_instruction_is_string_key_only(self) -> None:
        result = critique({"content": "draft"})
        self.assertEqual(set(result.keys()), {"reasoning_instruction"})


class TestReasoningToolsSchema(unittest.TestCase):
    """Verify tool definitions have correct schema structure."""

    def setUp(self) -> None:
        self.tools = {t.key: t for t in create_reasoning_tools()}

    def _schema(self, key: str) -> dict:
        return self.tools[key].definition.input_schema

    def test_all_schemas_disallow_additional_properties(self) -> None:
        for key, tool in self.tools.items():
            self.assertFalse(
                tool.definition.input_schema.get("additionalProperties", True),
                f"{key} should have additionalProperties=False",
            )

    def test_brainstorm_required_fields(self) -> None:
        schema = self._schema(REASON_BRAINSTORM)
        self.assertEqual(schema["required"], ["topic"])

    def test_chain_of_thought_required_fields(self) -> None:
        schema = self._schema(REASON_CHAIN_OF_THOUGHT)
        self.assertEqual(schema["required"], ["task"])

    def test_critique_required_fields(self) -> None:
        schema = self._schema(REASON_CRITIQUE)
        self.assertEqual(schema["required"], ["content"])

    def test_brainstorm_optional_fields_present(self) -> None:
        props = self._schema(REASON_BRAINSTORM)["properties"]
        self.assertIn("count", props)
        self.assertIn("context", props)
        self.assertIn("constraints", props)

    def test_chain_of_thought_optional_fields_present(self) -> None:
        props = self._schema(REASON_CHAIN_OF_THOUGHT)["properties"]
        self.assertIn("steps", props)
        self.assertIn("context", props)

    def test_critique_optional_aspects_field_present(self) -> None:
        props = self._schema(REASON_CRITIQUE)["properties"]
        self.assertIn("aspects", props)
        self.assertEqual(props["aspects"]["type"], "array")


if __name__ == "__main__":
    unittest.main()
