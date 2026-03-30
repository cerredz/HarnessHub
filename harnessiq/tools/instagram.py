"""
===============================================================================
File: harnessiq/tools/instagram.py

What this file does:
- Implements focused support logic for `harnessiq/tools`.
- Instagram agent tool definitions and runtime handlers.

Use cases:
- Import this module when sibling runtime code needs the behavior it
  centralizes.

How to use it:
- Use `create_instagram_tools` and the other exported symbols here through
  their package-level integration points.

Intent:
- Keep related runtime behavior centralized and easier to discover during
  maintenance.
===============================================================================
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Mapping

from harnessiq.shared.instagram import DEFAULT_SEARCH_RESULT_LIMIT
from harnessiq.shared.tools import INSTAGRAM_SEARCH_KEYWORD, RegisteredTool, ToolArguments, ToolDefinition

if TYPE_CHECKING:
    from harnessiq.shared.instagram import InstagramMemoryStore, InstagramSearchBackend


def create_instagram_tools(
    *,
    memory_store: "InstagramMemoryStore | None" = None,
    search_backend: "InstagramSearchBackend | None" = None,
    search_result_limit: int = DEFAULT_SEARCH_RESULT_LIMIT,
    current_icp_key: Callable[[], str] | None = None,
) -> tuple[RegisteredTool, ...]:
    """Return the Instagram search tool set.

    When runtime dependencies are omitted, the tool still exists in the shared
    toolset catalog for inspection and discovery, but execution fails with a
    clear runtime error.
    """

    return (
        RegisteredTool(
            definition=_search_keyword_definition(),
            handler=_build_search_keyword_handler(
                memory_store=memory_store,
                search_backend=search_backend,
                search_result_limit=search_result_limit,
                current_icp_key=current_icp_key,
            ),
        ),
    )


def _search_keyword_definition() -> ToolDefinition:
    return ToolDefinition(
        key=INSTAGRAM_SEARCH_KEYWORD,
        name="search_keyword",
        description=(
            "Run a deterministic Google site:instagram search for one keyword, inspect the Google "
            "results page using the spaced query pattern, extract public emails from result snippets "
            "without opening Instagram pages, and persist all new leads/emails to durable memory."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "keyword": {
                    "type": "string",
                    "description": "The concise Instagram creator niche keyword to search.",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of Google result rows to inspect for this keyword.",
                },
            },
            "required": ["keyword"],
            "additionalProperties": False,
        },
    )


def _build_search_keyword_handler(
    *,
    memory_store: "InstagramMemoryStore | None",
    search_backend: "InstagramSearchBackend | None",
    search_result_limit: int,
    current_icp_key: Callable[[], str] | None,
):
    def handler(arguments: ToolArguments) -> dict[str, Any]:
        if memory_store is None or search_backend is None:
            raise RuntimeError(
                "instagram.search_keyword requires a configured memory_store and search_backend."
            )

        keyword = _require_string(arguments, "keyword")
        icp_key = (current_icp_key().strip() or None) if current_icp_key is not None else None
        if memory_store.has_searched(keyword, icp_key=icp_key):
            return {
                "icp_key": icp_key,
                "keyword": keyword,
                "message": "Keyword already exists in durable search history.",
                "status": "already_searched",
            }

        max_results = _optional_positive_int(arguments, "max_results", default=search_result_limit)
        execution = search_backend.search_keyword(keyword=keyword, max_results=max_results)
        memory_store.append_search(execution.search_record, icp_key=icp_key)
        merge_summary = memory_store.merge_leads(execution.leads)
        return {
            "email_count": execution.search_record.email_count,
            "icp_key": icp_key,
            "keyword": execution.search_record.keyword,
            "lead_count": execution.search_record.lead_count,
            "merge_summary": merge_summary.as_dict(),
            "status": "searched",
        }

    return handler


def _require_string(arguments: Mapping[str, Any], key: str) -> str:
    value = arguments.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"'{key}' must be a non-empty string.")
    return value.strip()


def _optional_positive_int(arguments: Mapping[str, Any], key: str, *, default: int) -> int:
    value = arguments.get(key)
    if value is None:
        return default
    if isinstance(value, bool):
        raise ValueError(f"'{key}' must be a positive integer.")
    resolved = int(value)
    if resolved <= 0:
        raise ValueError(f"'{key}' must be positive.")
    return resolved


__all__ = ["create_instagram_tools"]
