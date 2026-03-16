"""Plug-and-play toolset access for Harnessiq.

Retrieve built-in tools or provider tools by key or family, list the entire
catalog, or create your own custom tools with :func:`define_tool` and the
:func:`tool` decorator.  The API mirrors :mod:`harnessiq.master_prompts`:
call a function, get back a ready-to-use object.

Retrieve built-in tools by key::

    from harnessiq.toolset import get_tool, get_tools

    brainstorm = get_tool("reason.brainstorm")
    three_core = get_tools("reason.brainstorm", "reason.chain_of_thought", "reason.critique")

Retrieve an entire tool family::

    from harnessiq.toolset import get_family

    reasoning_lenses = get_family("reasoning")          # all 50 lens tools
    first_four = get_family("reasoning", count=4)       # first 4 in catalog order
    filesystem = get_family("filesystem")               # all filesystem tools

Retrieve a provider tool (credentials required)::

    from harnessiq.toolset import get_tool
    from harnessiq.providers.creatify import CreatifyCredentials

    creatify = get_tool(
        "creatify.request",
        credentials=CreatifyCredentials(api_id="...", api_key="..."),
    )

List all available tools::

    from harnessiq.toolset import list_tools

    for entry in list_tools():
        print(entry.key, entry.family, entry.requires_credentials)

Create and register a custom tool::

    from harnessiq.toolset import define_tool
    from harnessiq.tools import ToolRegistry

    def shout(args):
        return args["text"].upper()

    shout_tool = define_tool(
        key="custom.shout",
        description="Convert text to uppercase.",
        parameters={"text": {"type": "string", "description": "The text to shout."}},
        required=["text"],
        handler=shout,
    )

    registry = ToolRegistry([*get_family("reasoning"), shout_tool])
"""

from __future__ import annotations

from harnessiq.shared.tools import RegisteredTool

from .catalog import ToolEntry
from .registry import ToolsetRegistry

# Shared module-level registry instance — initialized lazily on first access.
_registry: ToolsetRegistry | None = None


def _get_registry() -> ToolsetRegistry:
    global _registry
    if _registry is None:
        _registry = ToolsetRegistry()
    return _registry


def get_tool(key: str, *, credentials: object = None) -> RegisteredTool:
    """Return the :class:`~harnessiq.shared.tools.RegisteredTool` for *key*.

    Built-in tools (``reason.*``, ``filesystem.*``, ``reasoning.*``, etc.) do
    not require credentials.  Provider tools (``creatify.request``,
    ``exa.request``, etc.) require the appropriate credentials object.

    Args:
        key: The tool key in ``namespace.name`` format.
        credentials: Required for provider tools; ignored for built-in tools.

    Raises:
        KeyError: If *key* is not in the catalog.
        ValueError: If a provider tool is requested without credentials.

    Example::

        brainstorm = get_tool("reason.brainstorm")
        result = brainstorm.execute({"topic": "AI"})
    """
    return _get_registry().get(key, credentials=credentials)


def get_tools(*keys: str, credentials: object = None) -> tuple[RegisteredTool, ...]:
    """Return a tuple of tools for the given keys.

    All keys must be present in the catalog.  For provider keys, a single
    *credentials* object is forwarded to every provider factory call.

    Args:
        *keys: One or more tool keys in ``namespace.name`` format.
        credentials: Required if any key belongs to a provider family.

    Raises:
        KeyError: If any key is not in the catalog.
        ValueError: If a provider key is requested without credentials.

    Example::

        core_reasoning = get_tools(
            "reason.brainstorm",
            "reason.chain_of_thought",
            "reason.critique",
        )
    """
    return _get_registry().get_many(*keys, credentials=credentials)


def get_family(
    family: str,
    *,
    count: int | None = None,
    credentials: object = None,
) -> tuple[RegisteredTool, ...]:
    """Return all tools in *family*, optionally limited to the first *count*.

    Args:
        family: Family name derived from the key namespace prefix, e.g.
            ``"reasoning"``, ``"filesystem"``, ``"creatify"``.
        count: If given, return only the first *count* tools in catalog order.
        credentials: Required for provider families; ignored for built-ins.

    Raises:
        KeyError: If *family* is not in the catalog.
        ValueError: If a provider family is requested without credentials,
            or if *count* is not a positive integer.

    Example::

        all_lenses = get_family("reasoning")
        first_four = get_family("reasoning", count=4)
    """
    return _get_registry().get_family(family, count=count, credentials=credentials)


def list_tools() -> list[ToolEntry]:
    """Return metadata entries for all tools in the Harnessiq catalog.

    Built-in entries are derived from instantiated tool definitions; provider
    entries are returned from the static catalog without requiring credentials.

    Example::

        for entry in list_tools():
            if not entry.requires_credentials:
                print(entry.key, "—", entry.description)
    """
    return _get_registry().list()


__all__ = [
    "ToolEntry",
    "ToolsetRegistry",
    "get_family",
    "get_tool",
    "get_tools",
    "list_tools",
]
