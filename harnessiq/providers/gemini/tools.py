"""Gemini tool and tool-config builders."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Literal, Sequence

from harnessiq.providers.base import build_gemini_tool_declaration, omit_none_values
from harnessiq.shared.tools import ToolDefinition

FunctionCallingMode = Literal["AUTO", "ANY", "NONE"]


def format_tool_definition(definition: ToolDefinition) -> dict[str, object]:
    """Translate a canonical tool definition into a Gemini function declaration."""
    return build_gemini_tool_declaration(definition)


def build_function_tool(
    definitions: Sequence[ToolDefinition | dict[str, Any]],
) -> dict[str, object]:
    """Build a Gemini function-declarations tool entry."""
    declarations: list[dict[str, Any]] = []
    for definition in definitions:
        if isinstance(definition, ToolDefinition):
            declarations.append(format_tool_definition(definition))
        else:
            declarations.append(deepcopy(definition))
    return {"functionDeclarations": declarations}


def build_function_calling_config(
    *,
    mode: FunctionCallingMode = "AUTO",
    allowed_function_names: Sequence[str] | None = None,
) -> dict[str, object]:
    """Build Gemini function-calling configuration."""
    return omit_none_values(
        {
            "mode": mode,
            "allowedFunctionNames": list(allowed_function_names) if allowed_function_names is not None else None,
        }
    )


def build_tool_config(
    *,
    function_calling_config: dict[str, Any] | None = None,
) -> dict[str, object]:
    """Build Gemini tool configuration."""
    return omit_none_values(
        {
            "functionCallingConfig": deepcopy(function_calling_config) if function_calling_config is not None else None,
        }
    )


def build_google_search_tool() -> dict[str, object]:
    """Build the Gemini Google Search tool payload."""
    return {"googleSearch": {}}


def build_google_maps_tool() -> dict[str, object]:
    """Build the Gemini Google Maps tool payload."""
    return {"googleMaps": {}}


def build_url_context_tool() -> dict[str, object]:
    """Build the Gemini URL context tool payload."""
    return {"urlContext": {}}


def build_code_execution_tool() -> dict[str, object]:
    """Build the Gemini code execution tool payload."""
    return {"codeExecution": {}}


def build_file_search_tool(
    *,
    data_store_ids: Sequence[str] | None = None,
    max_results: int | None = None,
) -> dict[str, object]:
    """Build the Gemini file-search tool payload."""
    return {
        "fileSearch": omit_none_values(
            {
                "dataStoreIds": list(data_store_ids) if data_store_ids is not None else None,
                "maxResults": max_results,
            }
        )
    }
