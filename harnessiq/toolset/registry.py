"""Toolset registry — resolves ``RegisteredTool`` objects from the catalog.

``ToolsetRegistry`` is the backing implementation for the module-level
``get_tool``, ``get_tools``, ``get_family``, ``list_tools``, ``register_tool``,
and ``register_tools`` helpers.  It mirrors the design of
``MasterPromptRegistry``: lazy initialization on first access, an in-memory
cache, and clear ``KeyError`` / ``ValueError`` messages that name available
alternatives.
"""

from __future__ import annotations

import importlib

from harnessiq.shared.tools import RegisteredTool

from .catalog import (
    BUILTIN_FAMILY_FACTORIES,
    PROVIDER_ENTRIES,
    PROVIDER_ENTRY_INDEX,
    PROVIDER_FACTORY_MAP,
    ToolEntry,
)


class ToolsetRegistry:
    """Catalog-backed registry for the complete Harnessiq tool surface.

    Built-in tools (no credentials required) are instantiated once and cached.
    Provider tools (credentials required) are instantiated on demand by
    delegating to their respective ``create_*_tools()`` factory.
    Custom tools can be inserted at runtime via :meth:`register_tool` and
    :meth:`register_tools` so they appear alongside built-ins in all lookups.

    Example::

        registry = ToolsetRegistry()
        brainstorm = registry.get("reason.brainstorm")
        reasoning_tools = registry.get_family("reasoning", count=4)
        all_entries = registry.list()

        # Register a custom tool so it's retrievable by key
        registry.register_tool(my_custom_tool)
        retrieved = registry.get("custom.my_tool")
    """

    def __init__(self) -> None:
        # key → RegisteredTool for built-in tools (populated lazily)
        self._builtin_by_key: dict[str, RegisteredTool] | None = None
        # family → ordered tuple of RegisteredTool for built-in families
        self._builtin_by_family: dict[str, tuple[RegisteredTool, ...]] | None = None
        # Custom tools registered at runtime via register_tool()
        self._custom_by_key: dict[str, RegisteredTool] = {}
        self._custom_by_family: dict[str, list[RegisteredTool]] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, key: str, *, credentials: object = None) -> RegisteredTool:
        """Return the ``RegisteredTool`` for *key*.

        For built-in tools *credentials* is ignored.  For provider tools
        *credentials* is required — passing ``None`` raises ``ValueError``
        with a descriptive message.  Custom tools registered via
        :meth:`register_tool` are resolved before raising ``KeyError``.

        Raises:
            KeyError: If *key* is not in the catalog.
            ValueError: If a provider tool is requested without credentials.
        """
        if key in PROVIDER_ENTRY_INDEX:
            return self._resolve_provider_tool(key, credentials)
        self._ensure_builtin_loaded()
        assert self._builtin_by_key is not None  # noqa: S101
        if key in self._builtin_by_key:
            return self._builtin_by_key[key]
        if key in self._custom_by_key:
            return self._custom_by_key[key]
        raise KeyError(
            f"No tool with key '{key}' in the Harnessiq catalog. "
            f"Call list_tools() to see all available keys."
        )

    def register_tool(self, tool: RegisteredTool) -> None:
        """Insert *tool* into the registry so it is retrievable by key.

        After registration, ``get(tool.key)`` returns *tool* and
        ``get_family(family)`` includes it in the appropriate family bucket.
        ``list_tools()`` also returns a metadata entry for the tool.

        Args:
            tool: A :class:`~harnessiq.shared.tools.RegisteredTool` to insert.
                Typically created with :func:`~harnessiq.toolset.define_tool`
                or the :func:`~harnessiq.toolset.tool` decorator.

        Raises:
            ValueError: If *tool.key* already exists in the built-in catalog,
                the provider catalog, or a previously registered custom tool.

        Example::

            my_tool = define_tool(
                key="custom.shout",
                description="Uppercase.",
                parameters={"text": {"type": "string"}},
                handler=lambda args: args["text"].upper(),
            )
            registry.register_tool(my_tool)
            registry.get("custom.shout")  # returns my_tool
        """
        key = tool.key
        self._ensure_builtin_loaded()
        assert self._builtin_by_key is not None  # noqa: S101
        if key in self._builtin_by_key:
            raise ValueError(
                f"Cannot register custom tool: key '{key}' is already used by a "
                f"built-in Harnessiq tool."
            )
        if key in PROVIDER_ENTRY_INDEX:
            raise ValueError(
                f"Cannot register custom tool: key '{key}' is already used by a "
                f"provider tool."
            )
        if key in self._custom_by_key:
            raise ValueError(
                f"Cannot register custom tool: key '{key}' has already been "
                f"registered as a custom tool."
            )
        self._custom_by_key[key] = tool
        family = _family_of(key)
        self._custom_by_family.setdefault(family, []).append(tool)

    def register_tools(self, *tools: RegisteredTool) -> None:
        """Insert multiple tools into the registry in order.

        Equivalent to calling :meth:`register_tool` for each tool in *tools*.
        If any key collides, the error is raised immediately and subsequent
        tools in the call are not registered.

        Args:
            *tools: One or more :class:`~harnessiq.shared.tools.RegisteredTool`
                objects to register.

        Raises:
            ValueError: If any key already exists in the built-in, provider,
                or custom catalog.
        """
        for tool in tools:
            self.register_tool(tool)

    def get_many(self, *keys: str, credentials: object = None) -> tuple[RegisteredTool, ...]:
        """Return a tuple of ``RegisteredTool`` objects for the given keys.

        All keys must be present in the catalog.  Provider keys require
        *credentials* — a single credentials object is shared across all
        provider keys in the call.

        Raises:
            KeyError: If any key is not in the catalog.
            ValueError: If a provider key is requested without credentials.
        """
        return tuple(self.get(key, credentials=credentials) for key in keys)

    def get_family(
        self,
        family: str,
        *,
        count: int | None = None,
        credentials: object = None,
    ) -> tuple[RegisteredTool, ...]:
        """Return all tools in *family*, optionally limited to the first *count*.

        For built-in families *credentials* is ignored.  For provider families
        *credentials* is required.

        Args:
            family: The family name (key namespace prefix, e.g. ``"reasoning"``,
                ``"filesystem"``, ``"creatify"``).
            count: If provided, return only the first *count* tools in the
                family's canonical insertion order.
            credentials: Required for provider families.

        Raises:
            KeyError: If *family* is not in the catalog.
            ValueError: If a provider family is requested without credentials,
                or if *count* is not a positive integer.
        """
        if count is not None and (not isinstance(count, int) or count <= 0):
            raise ValueError(f"'count' must be a positive integer, got {count!r}.")

        tools = self._resolve_family(family, credentials)
        return tools[:count] if count is not None else tools

    def list(self) -> list[ToolEntry]:
        """Return metadata entries for all registered tools, built-ins first.

        Built-in entries are derived from instantiated tool definitions;
        provider entries are returned from the static catalog; custom entries
        appear last.
        """
        self._ensure_builtin_loaded()
        assert self._builtin_by_key is not None  # noqa: S101

        builtin_entries = [
            ToolEntry(
                key=tool.definition.key,
                name=tool.definition.name,
                description=tool.definition.description,
                family=_family_of(tool.definition.key),
                requires_credentials=False,
            )
            for tool in self._builtin_by_key.values()
        ]
        custom_entries = [
            ToolEntry(
                key=tool.definition.key,
                name=tool.definition.name,
                description=tool.definition.description,
                family=_family_of(tool.definition.key),
                requires_credentials=False,
            )
            for tool in self._custom_by_key.values()
        ]
        return [*builtin_entries, *PROVIDER_ENTRIES, *custom_entries]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_builtin_loaded(self) -> None:
        if self._builtin_by_key is not None:
            return

        by_key: dict[str, RegisteredTool] = {}
        by_family: dict[str, list[RegisteredTool]] = {}

        for factory in BUILTIN_FAMILY_FACTORIES:
            tools: tuple[RegisteredTool, ...] = factory()
            for tool in tools:
                if tool.key in by_key:
                    continue  # deduplicate (core tools appear in BUILTIN_TOOLS)
                by_key[tool.key] = tool
                # Group by the actual key prefix, not the factory's family name,
                # since general_purpose returns text.*, records.*, and control.*
                prefix = _family_of(tool.key)
                by_family.setdefault(prefix, []).append(tool)

        self._builtin_by_key = by_key
        self._builtin_by_family = {k: tuple(v) for k, v in by_family.items()}

    def _resolve_family(
        self,
        family: str,
        credentials: object,
    ) -> tuple[RegisteredTool, ...]:
        # Provider family?
        if family in PROVIDER_FACTORY_MAP:
            if credentials is None:
                raise ValueError(
                    f"Provider family '{family}' requires credentials. "
                    f"Pass the appropriate credentials object via the "
                    f"'credentials=' keyword argument."
                )
            tools = _invoke_provider_factory(family, credentials)
            return tools

        # Built-in family?
        self._ensure_builtin_loaded()
        assert self._builtin_by_family is not None  # noqa: S101
        builtin = self._builtin_by_family.get(family)
        custom = tuple(self._custom_by_family.get(family, []))
        if builtin is not None or custom:
            return (*builtin, *custom) if builtin is not None else custom

        available = sorted(
            set(self._builtin_by_family.keys())
            | set(PROVIDER_FACTORY_MAP.keys())
            | set(self._custom_by_family.keys())
        )
        raise KeyError(
            f"No tool family '{family}' in the Harnessiq catalog. "
            f"Available families: {', '.join(available)}."
        )

    def _resolve_provider_tool(
        self,
        key: str,
        credentials: object,
    ) -> RegisteredTool:
        entry = PROVIDER_ENTRY_INDEX[key]
        family = entry.family
        if credentials is None:
            raise ValueError(
                f"Tool '{key}' requires credentials for the '{family}' provider. "
                f"Pass the appropriate credentials object via the "
                f"'credentials=' keyword argument, e.g. "
                f"get_tool('{key}', credentials=<{family.capitalize()}Credentials>(...))."
            )
        tools = _invoke_provider_factory(family, credentials)
        tool_map = {t.key: t for t in tools}
        if key not in tool_map:
            raise KeyError(
                f"Tool '{key}' was not found in the resolved '{family}' tool set."
            )
        return tool_map[key]


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

def _family_of(key: str) -> str:
    """Return the family name (key prefix before the first dot)."""
    return key.split(".")[0]


def _invoke_provider_factory(family: str, credentials: object) -> tuple[RegisteredTool, ...]:
    """Import and call the provider factory for *family* with *credentials*."""
    module_path, func_name = PROVIDER_FACTORY_MAP[family]
    module = importlib.import_module(module_path)
    factory = getattr(module, func_name)
    return tuple(factory(credentials=credentials))


__all__ = ["ToolsetRegistry"]  # register_tool / register_tools are on the instance
