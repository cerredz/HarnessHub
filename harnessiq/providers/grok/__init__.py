"""Grok request and client helpers."""

from harnessiq.shared.dtos import GrokChatCompletionRequestDTO, GrokSearchParametersDTO

from .client import GrokClient
from .helpers import build_request, format_tool_definition
from .requests import (
    build_chat_completion_request,
    build_response_format_json_object,
    build_response_format_json_schema,
    build_search_parameters,
)
from .tools import (
    build_code_execution_tool,
    build_collections_search_tool,
    build_function_tool,
    build_mcp_tool,
    build_tool_choice,
    build_web_search_tool,
    build_x_search_tool,
)

__all__ = [
    "GrokClient",
    "GrokChatCompletionRequestDTO",
    "GrokSearchParametersDTO",
    "build_chat_completion_request",
    "build_code_execution_tool",
    "build_collections_search_tool",
    "build_function_tool",
    "build_mcp_tool",
    "build_request",
    "build_response_format_json_object",
    "build_response_format_json_schema",
    "build_search_parameters",
    "build_tool_choice",
    "build_web_search_tool",
    "build_x_search_tool",
    "format_tool_definition",
]
