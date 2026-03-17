"""Custom tool creation helpers for Harnessiq.

:func:`define_tool` and the :func:`tool` decorator let you create
``RegisteredTool`` objects using the same ergonomic style as the built-in tool
families — without manually constructing ``ToolDefinition`` and the raw
JSON Schema wrapper.

Example — factory function style::

    from harnessiq.toolset import define_tool

    def shout(args):
        return args["text"].upper()

    shout_tool = define_tool(
        key="custom.shout",
        description="Convert text to uppercase.",
        parameters={"text": {"type": "string", "description": "The text to shout."}},
        required=["text"],
        handler=shout,
    )

Example — decorator style::

    from harnessiq.toolset import tool

    @tool(
        key="custom.shout",
        description="Convert text to uppercase.",
        parameters={"text": {"type": "string", "description": "The text to shout."}},
        required=["text"],
    )
    def shout(args):
        return args["text"].upper()

    # shout is now a RegisteredTool, not a plain function.

Both return a ``RegisteredTool`` that can be passed directly to a
``ToolRegistry`` or used alongside tools retrieved from the toolset catalog::

    from harnessiq.toolset import get_family
    from harnessiq.tools import ToolRegistry

    registry = ToolRegistry([*get_family("reasoning"), shout_tool])
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

from harnessiq.shared.tools import RegisteredTool, ToolDefinition, ToolHandler

# ---------------------------------------------------------------------------
# Supported tool types
# ---------------------------------------------------------------------------
# Only "function" is currently supported.  The set will grow in future SDK
# releases to include computer_use, code_interpreter, multi_agent, and others.
_SUPPORTED_TOOL_TYPES: frozenset[str] = frozenset({"function"})

_PLANNED_TOOL_TYPES: frozenset[str] = frozenset(
    {"computer_use", "code_interpreter", "multi_agent", "sandbox", "web_search"}
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def define_tool(
    *,
    key: str,
    description: str,
    parameters: dict[str, Any],
    handler: ToolHandler,
    name: str | None = None,
    required: Sequence[str] | None = None,
    additional_properties: bool = False,
    tool_type: str = "function",
) -> RegisteredTool:
    """Create and return a :class:`~harnessiq.shared.tools.RegisteredTool`.

    Args:
        key: Unique tool identifier in ``namespace.name`` format, e.g.
            ``"custom.shout"``.  Must not clash with any key already in
            the registry you intend to add this tool to.
        description: What the tool does and when an agent should use it.
            Write this as if explaining the tool to the model — be specific.
        parameters: The tool's input parameters as a flat dict of
            ``{param_name: json_schema_property}``.  Each value should be a
            dict with at minimum a ``"type"`` key and ideally a
            ``"description"`` key, e.g.
            ``{"text": {"type": "string", "description": "The input text."}}``.
            This is wrapped into a full JSON Schema object automatically.
        handler: A callable that accepts a ``ToolArguments`` dict and returns
            any JSON-serialisable value.  The dict keys match the parameter
            names declared in *parameters*.
        name: Short snake_case name for the tool.  Defaults to the last
            segment of *key* (e.g. ``"custom.shout"`` → ``"shout"``).
        required: List of parameter names that are required.  Defaults to
            ``[]`` (no required parameters).  Pass ``list(parameters)`` to
            require all parameters.
        additional_properties: Whether the tool's input schema allows
            extra keys beyond those declared in *parameters*.  Defaults to
            ``False`` (strict schema).
        tool_type: The execution type for this tool.  Currently only
            ``"function"`` is supported.  Passing any other value raises
            ``ValueError`` with a message explaining future support.

    Returns:
        A :class:`~harnessiq.shared.tools.RegisteredTool` ready to be added
        to a :class:`~harnessiq.tools.ToolRegistry`.

    Raises:
        ValueError: If *tool_type* is not a currently supported type.

    Example::

        my_tool = define_tool(
            key="custom.reverse",
            description="Reverse a string.",
            parameters={"text": {"type": "string", "description": "String to reverse."}},
            required=["text"],
            handler=lambda args: args["text"][::-1],
        )
    """
    _validate_tool_type(tool_type)
    resolved_name = name if name is not None else _name_from_key(key)
    input_schema = _build_input_schema(
        parameters=parameters,
        required=list(required) if required is not None else [],
        additional_properties=additional_properties,
    )
    definition = ToolDefinition(
        key=key,
        name=resolved_name,
        description=description,
        input_schema=input_schema,
        tool_type=tool_type,
    )
    return RegisteredTool(definition=definition, handler=handler)


def tool(
    *,
    key: str,
    description: str,
    parameters: dict[str, Any],
    name: str | None = None,
    required: Sequence[str] | None = None,
    additional_properties: bool = False,
    tool_type: str = "function",
) -> Callable[[ToolHandler], RegisteredTool]:
    """Decorator that converts a handler function into a :class:`~harnessiq.shared.tools.RegisteredTool`.

    All keyword arguments match :func:`define_tool` exactly.  The decorated
    function is replaced by the resulting ``RegisteredTool``.

    Example::

        @tool(
            key="custom.shout",
            description="Convert text to uppercase.",
            parameters={"text": {"type": "string", "description": "The text."}},
            required=["text"],
        )
        def shout(args):
            return args["text"].upper()

        # shout is now a RegisteredTool.
        result = shout.execute({"text": "hello"})
    """
    def decorator(handler: ToolHandler) -> RegisteredTool:
        return define_tool(
            key=key,
            description=description,
            parameters=parameters,
            handler=handler,
            name=name,
            required=required,
            additional_properties=additional_properties,
            tool_type=tool_type,
        )

    return decorator


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _validate_tool_type(tool_type: str) -> None:
    if tool_type in _SUPPORTED_TOOL_TYPES:
        return
    if tool_type in _PLANNED_TOOL_TYPES:
        raise ValueError(
            f"Tool type '{tool_type}' is planned for a future SDK release and is not "
            f"yet supported.  Currently supported types: {sorted(_SUPPORTED_TOOL_TYPES)}."
        )
    raise ValueError(
        f"Unknown tool type '{tool_type}'.  Currently supported: "
        f"{sorted(_SUPPORTED_TOOL_TYPES)}.  Additional types "
        f"({', '.join(sorted(_PLANNED_TOOL_TYPES))}) are planned for future releases."
    )


def _name_from_key(key: str) -> str:
    """Return the last dot-segment of a key as the tool name."""
    return key.rsplit(".", 1)[-1]


def _build_input_schema(
    parameters: dict[str, Any],
    required: list[str],
    additional_properties: bool,
) -> dict[str, Any]:
    """Build a full JSON Schema object from the user-supplied parameters dict."""
    return {
        "type": "object",
        "properties": parameters,
        "required": required,
        "additionalProperties": additional_properties,
    }


__all__ = [
    "define_tool",
    "tool",
]
