"""Tests for define_tool(), @tool decorator, and ToolDefinition.tool_type (Ticket 2)."""

from __future__ import annotations

import pytest

from harnessiq.shared.tools import RegisteredTool, ToolDefinition
from harnessiq.toolset import define_tool, tool
from harnessiq.tools import ToolRegistry


# ---------------------------------------------------------------------------
# define_tool — basic construction
# ---------------------------------------------------------------------------


class TestDefineTool:
    def test_returns_registered_tool(self):
        t = define_tool(
            key="custom.shout",
            description="Shout text.",
            parameters={"text": {"type": "string"}},
            handler=lambda args: args["text"].upper(),
        )
        assert isinstance(t, RegisteredTool)

    def test_key_is_set(self):
        t = define_tool(
            key="custom.shout",
            description="Shout text.",
            parameters={"text": {"type": "string"}},
            handler=lambda args: args["text"].upper(),
        )
        assert t.key == "custom.shout"

    def test_description_is_set(self):
        t = define_tool(
            key="custom.shout",
            description="Shout text.",
            parameters={"text": {"type": "string"}},
            handler=lambda args: args["text"].upper(),
        )
        assert t.definition.description == "Shout text."

    def test_name_defaults_to_key_suffix(self):
        t = define_tool(
            key="custom.shout",
            description="Shout.",
            parameters={},
            handler=lambda args: None,
        )
        assert t.definition.name == "shout"

    def test_name_defaults_to_key_suffix_multi_segment(self):
        t = define_tool(
            key="ns.sub.my_tool",
            description="Test.",
            parameters={},
            handler=lambda args: None,
        )
        assert t.definition.name == "my_tool"

    def test_explicit_name_overrides_default(self):
        t = define_tool(
            key="custom.shout",
            description="Shout.",
            parameters={},
            handler=lambda args: None,
            name="MY_EXPLICIT_NAME",
        )
        assert t.definition.name == "MY_EXPLICIT_NAME"

    def test_tool_type_defaults_to_function(self):
        t = define_tool(
            key="custom.x",
            description="Test.",
            parameters={},
            handler=lambda args: None,
        )
        assert t.definition.tool_type == "function"

    def test_tool_type_function_explicit(self):
        t = define_tool(
            key="custom.x",
            description="Test.",
            parameters={},
            handler=lambda args: None,
            tool_type="function",
        )
        assert t.definition.tool_type == "function"

    def test_unsupported_tool_type_raises(self):
        with pytest.raises(ValueError, match="computer_use"):
            define_tool(
                key="custom.x",
                description="Test.",
                parameters={},
                handler=lambda args: None,
                tool_type="computer_use",
            )

    def test_unsupported_tool_type_error_mentions_future_support(self):
        with pytest.raises(ValueError, match="future"):
            define_tool(
                key="custom.x",
                description="Test.",
                parameters={},
                handler=lambda args: None,
                tool_type="computer_use",
            )

    def test_completely_unknown_tool_type_raises(self):
        with pytest.raises(ValueError, match="unknown_type"):
            define_tool(
                key="custom.x",
                description="Test.",
                parameters={},
                handler=lambda args: None,
                tool_type="unknown_type",
            )


# ---------------------------------------------------------------------------
# define_tool — input schema construction
# ---------------------------------------------------------------------------


class TestDefineToolSchema:
    def test_schema_type_is_object(self):
        t = define_tool(
            key="custom.x",
            description="Test.",
            parameters={"v": {"type": "string"}},
            handler=lambda args: None,
        )
        assert t.definition.input_schema["type"] == "object"

    def test_parameters_become_properties(self):
        params = {"text": {"type": "string", "description": "Input."}}
        t = define_tool(
            key="custom.x",
            description="Test.",
            parameters=params,
            handler=lambda args: None,
        )
        assert t.definition.input_schema["properties"] == params

    def test_required_defaults_to_empty(self):
        t = define_tool(
            key="custom.x",
            description="Test.",
            parameters={"v": {"type": "string"}},
            handler=lambda args: None,
        )
        assert t.definition.input_schema["required"] == []

    def test_required_explicit(self):
        t = define_tool(
            key="custom.x",
            description="Test.",
            parameters={"v": {"type": "string"}},
            required=["v"],
            handler=lambda args: None,
        )
        assert t.definition.input_schema["required"] == ["v"]

    def test_additional_properties_defaults_false(self):
        t = define_tool(
            key="custom.x",
            description="Test.",
            parameters={},
            handler=lambda args: None,
        )
        assert t.definition.input_schema["additionalProperties"] is False

    def test_additional_properties_true(self):
        t = define_tool(
            key="custom.x",
            description="Test.",
            parameters={},
            handler=lambda args: None,
            additional_properties=True,
        )
        assert t.definition.input_schema["additionalProperties"] is True

    def test_empty_parameters_produces_valid_schema(self):
        t = define_tool(
            key="custom.x",
            description="Test.",
            parameters={},
            handler=lambda args: None,
        )
        schema = t.definition.input_schema
        assert schema["type"] == "object"
        assert schema["properties"] == {}
        assert schema["required"] == []

    def test_multiple_parameters(self):
        params = {
            "a": {"type": "string"},
            "b": {"type": "integer"},
        }
        t = define_tool(
            key="custom.x",
            description="Test.",
            parameters=params,
            required=["a"],
            handler=lambda args: None,
        )
        assert set(t.definition.input_schema["properties"]) == {"a", "b"}
        assert t.definition.input_schema["required"] == ["a"]


# ---------------------------------------------------------------------------
# define_tool — handler execution
# ---------------------------------------------------------------------------


class TestDefineToolExecution:
    def test_handler_is_called_with_args(self):
        calls = []
        def h(args):
            calls.append(args)
            return "ok"

        t = define_tool(
            key="custom.record",
            description="Record args.",
            parameters={"x": {"type": "string"}},
            handler=h,
        )
        t.execute({"x": "hello"})
        assert calls == [{"x": "hello"}]

    def test_handler_return_value_is_output(self):
        t = define_tool(
            key="custom.shout",
            description="Shout.",
            parameters={"text": {"type": "string"}},
            required=["text"],
            handler=lambda args: args["text"].upper(),
        )
        result = t.execute({"text": "hello"})
        assert result.output == "HELLO"
        assert result.tool_key == "custom.shout"

    def test_handler_can_return_dict(self):
        t = define_tool(
            key="custom.wrap",
            description="Wrap.",
            parameters={"v": {"type": "integer"}},
            handler=lambda args: {"value": args["v"] * 2},
        )
        result = t.execute({"v": 5})
        assert result.output == {"value": 10}


# ---------------------------------------------------------------------------
# @tool decorator
# ---------------------------------------------------------------------------


class TestToolDecorator:
    def test_decorator_produces_registered_tool(self):
        @tool(
            key="custom.shout",
            description="Shout text.",
            parameters={"text": {"type": "string"}},
            required=["text"],
        )
        def shout(args):
            return args["text"].upper()

        assert isinstance(shout, RegisteredTool)

    def test_decorator_key_is_set(self):
        @tool(
            key="custom.shout",
            description="Shout.",
            parameters={"text": {"type": "string"}},
        )
        def shout(args):
            return args["text"].upper()

        assert shout.key == "custom.shout"

    def test_decorator_name_defaults_to_key_suffix(self):
        @tool(
            key="custom.my_func",
            description="Test.",
            parameters={},
        )
        def my_func(args):
            return None

        assert my_func.definition.name == "my_func"

    def test_decorator_handler_executes(self):
        @tool(
            key="custom.double",
            description="Double a number.",
            parameters={"n": {"type": "integer"}},
            required=["n"],
        )
        def double(args):
            return args["n"] * 2

        result = double.execute({"n": 7})
        assert result.output == 14

    def test_decorator_schema_has_required(self):
        @tool(
            key="custom.x",
            description="Test.",
            parameters={"a": {"type": "string"}},
            required=["a"],
        )
        def fn(args):
            return None

        assert fn.definition.input_schema["required"] == ["a"]

    def test_decorator_tool_type_default(self):
        @tool(
            key="custom.x",
            description="Test.",
            parameters={},
        )
        def fn(args):
            return None

        assert fn.definition.tool_type == "function"

    def test_decorator_unsupported_tool_type_raises(self):
        with pytest.raises(ValueError):
            @tool(
                key="custom.x",
                description="Test.",
                parameters={},
                tool_type="code_interpreter",
            )
            def fn(args):
                return None


# ---------------------------------------------------------------------------
# Integration — custom tool in ToolRegistry
# ---------------------------------------------------------------------------


class TestCustomToolInRegistry:
    def test_can_register_custom_tool(self):
        my_tool = define_tool(
            key="custom.upper",
            description="Uppercase.",
            parameters={"text": {"type": "string"}},
            required=["text"],
            handler=lambda args: args["text"].upper(),
        )
        registry = ToolRegistry([my_tool])
        assert "custom.upper" in registry

    def test_can_execute_custom_tool_via_registry(self):
        my_tool = define_tool(
            key="custom.upper",
            description="Uppercase.",
            parameters={"text": {"type": "string"}},
            required=["text"],
            handler=lambda args: args["text"].upper(),
        )
        registry = ToolRegistry([my_tool])
        result = registry.execute("custom.upper", {"text": "hello"})
        assert result.output == "HELLO"

    def test_custom_tool_plus_builtin_tools(self):
        from harnessiq.toolset import get_family
        my_tool = define_tool(
            key="custom.shout",
            description="Shout.",
            parameters={"text": {"type": "string"}},
            handler=lambda args: args["text"].upper(),
        )
        registry = ToolRegistry([*get_family("reason"), my_tool])
        assert "reason.brainstorm" in registry
        assert "custom.shout" in registry

    def test_registry_validates_required_args(self):
        from harnessiq.tools.registry import ToolValidationError
        my_tool = define_tool(
            key="custom.strict",
            description="Strict tool.",
            parameters={"x": {"type": "string"}},
            required=["x"],
            handler=lambda args: args["x"],
        )
        registry = ToolRegistry([my_tool])
        with pytest.raises(ToolValidationError, match="missing required"):
            registry.execute("custom.strict", {})


# ---------------------------------------------------------------------------
# ToolDefinition.tool_type — backwards compatibility
# ---------------------------------------------------------------------------


class TestToolDefinitionToolType:
    def test_existing_definitions_default_to_function(self):
        defn = ToolDefinition(
            key="test.x",
            name="x",
            description="Test.",
            input_schema={"type": "object", "properties": {}},
        )
        assert defn.tool_type == "function"

    def test_as_dict_does_not_include_tool_type(self):
        # tool_type is SDK metadata, not model API payload — excluded from as_dict()
        defn = ToolDefinition(
            key="test.x",
            name="x",
            description="Test.",
            input_schema={"type": "object", "properties": {}},
        )
        d = defn.as_dict()
        assert "tool_type" not in d

    def test_as_dict_has_standard_keys(self):
        defn = ToolDefinition(
            key="test.x",
            name="x",
            description="Test.",
            input_schema={"type": "object", "properties": {}},
        )
        assert set(defn.as_dict().keys()) == {"key", "name", "description", "input_schema"}

    def test_all_existing_builtin_tools_have_function_type(self):
        from harnessiq.tools.builtin import BUILTIN_TOOLS
        for t in BUILTIN_TOOLS:
            assert t.definition.tool_type == "function", (
                f"Tool {t.key!r} has unexpected tool_type {t.definition.tool_type!r}"
            )
