"""Toolset registry — resolves ``RegisteredTool`` objects from the catalog.

``ToolsetRegistry`` is the backing implementation for the module-level
``get_tool``, ``get_tools``, ``get_family``, and ``list_tools`` helpers.  It
mirrors the design of ``MasterPromptRegistry``: lazy initialization on first
access, an in-memory cache, and clear ``KeyError`` / ``ValueError`` messages
that name available alternatives.
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

    Example::

        registry = ToolsetRegistry()
        brainstorm = registry.get("reason.brainstorm")
        reasoning_tools = registry.get_family("reasoning", count=4)
        all_entries = registry.list()
    """

    def __init__(self) -> None:
        # key → RegisteredTool for built-in tools (populated lazily)
        self._builtin_by_key: dict[str, RegisteredTool] | None = None
        # family → ordered tuple of RegisteredTool for built-in families
        self._builtin_by_family: dict[str, tuple[RegisteredTool, ...]] | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, key: str, *, credentials: object = None) -> RegisteredTool:
        """Return the ``RegisteredTool`` for *key*.

        For built-in tools *credentials* is ignored.  For provider tools
        *credentials* is required — passing ``None`` raises ``ValueError``
        with a descriptive message.

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
        raise KeyError(
            f"No tool with key '{key}' in the Harnessiq catalog. "
            f"Call list_tools() to see all available keys."
        )

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
        provider entries are returned from the static catalog.
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
        return [*builtin_entries, *PROVIDER_ENTRIES]

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
            needs_creds = any(
                e.requires_credentials for e in PROVIDER_ENTRIES if e.family == family
            )
            if credentials is None and needs_creds:
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
        if family in self._builtin_by_family:
            return self._builtin_by_family[family]

        available = sorted(
            set(self._builtin_by_family.keys()) | set(PROVIDER_FACTORY_MAP.keys())
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
        if credentials is None and entry.requires_credentials:
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


__all__ = ["ToolsetRegistry"]
