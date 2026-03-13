"""Tests for the canonical tool registry."""

from __future__ import annotations

import unittest
from copy import deepcopy

from src.shared.tools import ADD_NUMBERS, ECHO_TEXT, RegisteredTool, ToolDefinition
from src.tools.registry import (
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

        self.assertEqual(registry.keys(), (ECHO_TEXT, ADD_NUMBERS))

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

        self.assertEqual(echo_result.output, {"text": "hello"})
        self.assertEqual(add_result.output, {"sum": 3.5})

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


if __name__ == "__main__":
    unittest.main()
