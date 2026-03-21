"""Built-in tool family factory catalog for the Harnessiq toolset."""

from __future__ import annotations

from collections.abc import Callable

from harnessiq.shared.tools import RegisteredTool

_BuiltinFactory = Callable[[], tuple[RegisteredTool, ...]]


def _builtin_core() -> tuple[RegisteredTool, ...]:
    from harnessiq.shared.tools import ADD_NUMBERS, ECHO_TEXT
    from harnessiq.tools.builtin import BUILTIN_TOOLS

    core_keys = frozenset({ECHO_TEXT, ADD_NUMBERS})
    return tuple(tool for tool in BUILTIN_TOOLS if tool.key in core_keys)


def _builtin_context() -> tuple[RegisteredTool, ...]:
    from harnessiq.tools.context_compaction import create_context_compaction_tools

    return create_context_compaction_tools()


def _builtin_general_purpose() -> tuple[RegisteredTool, ...]:
    # Returns text.*, records.*, and control.* tools. The registry groups them
    # by their actual key prefix instead of this factory name.
    from harnessiq.tools.general_purpose import create_general_purpose_tools

    return create_general_purpose_tools()


def _builtin_prompt() -> tuple[RegisteredTool, ...]:
    from harnessiq.tools.prompting import create_prompt_tools

    return create_prompt_tools()


def _builtin_filesystem() -> tuple[RegisteredTool, ...]:
    from harnessiq.tools.filesystem import create_filesystem_tools

    return create_filesystem_tools()


def _builtin_instagram() -> tuple[RegisteredTool, ...]:
    from harnessiq.tools.instagram import create_instagram_tools

    return create_instagram_tools()


def _builtin_reason() -> tuple[RegisteredTool, ...]:
    from harnessiq.tools.reasoning.core import create_injectable_reasoning_tools

    return create_injectable_reasoning_tools()


def _builtin_reasoning() -> tuple[RegisteredTool, ...]:
    from harnessiq.tools.reasoning.lenses import create_reasoning_tools

    return create_reasoning_tools()


BUILTIN_FAMILY_FACTORIES: tuple[_BuiltinFactory, ...] = (
    _builtin_core,
    _builtin_context,
    _builtin_general_purpose,
    _builtin_prompt,
    _builtin_filesystem,
    _builtin_instagram,
    _builtin_reason,
    _builtin_reasoning,
)


__all__ = ["BUILTIN_FAMILY_FACTORIES"]
