"""Gemini request and client helpers."""

from harnessiq.shared.dtos import (
    GeminiCacheCreateRequestDTO,
    GeminiContentDTO,
    GeminiCountTokensRequestDTO,
    GeminiGenerateContentRequestDTO,
    GeminiGenerationConfigDTO,
    GeminiSystemInstructionDTO,
)

from .client import GeminiClient
from .content import (
    build_cached_content_request,
    build_content,
    build_count_tokens_request,
    build_file_data_part,
    build_generate_content_request,
    build_generation_config,
    build_inline_data_part,
    build_request,
    build_system_instruction,
    build_text_part,
)
from .helpers import format_tool_definition
from .tools import (
    build_code_execution_tool,
    build_file_search_tool,
    build_function_calling_config,
    build_function_tool,
    build_google_maps_tool,
    build_google_search_tool,
    build_tool_config,
    build_url_context_tool,
)

__all__ = [
    "GeminiClient",
    "GeminiCacheCreateRequestDTO",
    "GeminiContentDTO",
    "GeminiCountTokensRequestDTO",
    "GeminiGenerateContentRequestDTO",
    "GeminiGenerationConfigDTO",
    "GeminiSystemInstructionDTO",
    "build_cached_content_request",
    "build_code_execution_tool",
    "build_content",
    "build_count_tokens_request",
    "build_file_data_part",
    "build_file_search_tool",
    "build_function_calling_config",
    "build_function_tool",
    "build_generate_content_request",
    "build_generation_config",
    "build_google_maps_tool",
    "build_google_search_tool",
    "build_inline_data_part",
    "build_request",
    "build_system_instruction",
    "build_text_part",
    "build_tool_config",
    "build_url_context_tool",
    "format_tool_definition",
]
