"""Provider-specific request translation and client helpers."""

from harnessiq.shared.providers import ProviderMessage, ProviderName, RequestPayload, SUPPORTED_PROVIDERS

from .base import ProviderFormatError, normalize_messages, omit_none_values
from .http import ProviderHTTPError, RequestExecutor, request_json
from .langsmith import (
    build_langsmith_client,
    trace_agent_run,
    trace_async_agent_run,
    trace_async_model_call,
    trace_async_tool_call,
    trace_model_call,
    trace_tool_call,
)
from .output_sinks import (
    ConfluenceClient,
    GoogleSheetsClient,
    LinearClient,
    MongoDBClient,
    NotionClient,
    SupabaseClient,
    WebhookDeliveryClient,
    extract_model_metadata,
)
from .playwright import (
    PlaywrightBrowserSession,
    chromium_context,
    get_or_create_page,
    goto_page,
    playwright_runtime,
    read_page_text,
    safe_page_title,
    wait_for_page_ready,
)

__all__ = [
    "ProviderFormatError",
    "ProviderHTTPError",
    "ProviderMessage",
    "ProviderName",
    "RequestExecutor",
    "RequestPayload",
    "SupabaseClient",
    "SUPPORTED_PROVIDERS",
    "build_langsmith_client",
    "WebhookDeliveryClient",
    "ConfluenceClient",
    "GoogleSheetsClient",
    "LinearClient",
    "MongoDBClient",
    "NotionClient",
    "PlaywrightBrowserSession",
    "extract_model_metadata",
    "chromium_context",
    "get_or_create_page",
    "goto_page",
    "normalize_messages",
    "omit_none_values",
    "playwright_runtime",
    "read_page_text",
    "request_json",
    "safe_page_title",
    "trace_agent_run",
    "trace_async_agent_run",
    "trace_model_call",
    "trace_async_model_call",
    "trace_tool_call",
    "trace_async_tool_call",
    "wait_for_page_ready",
]
