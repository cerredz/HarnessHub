"""Compatibility facade for provider output sink helpers."""

from __future__ import annotations

from harnessiq.shared.output_sinks import (
    DEFAULT_NOTION_VERSION,
    GOOGLE_SHEETS_DEFAULT_BASE_URL,
    GOOGLE_SHEETS_DEFAULT_SCOPE,
    GOOGLE_SHEETS_DEFAULT_TOKEN_URL,
    LINEAR_DEFAULT_BASE_URL,
    NOTION_DEFAULT_BASE_URL,
)

from .output_sink_clients import (
    ConfluenceClient,
    GoogleSheetsClient,
    LinearClient,
    MongoDBClient,
    NotionClient,
    SupabaseClient,
    WebhookDeliveryClient,
)
from .output_sink_metadata import extract_model_metadata

ConfluenceClient.__module__ = __name__
GoogleSheetsClient.__module__ = __name__
LinearClient.__module__ = __name__
MongoDBClient.__module__ = __name__
NotionClient.__module__ = __name__
SupabaseClient.__module__ = __name__
WebhookDeliveryClient.__module__ = __name__
extract_model_metadata.__module__ = __name__

__all__ = [
    "ConfluenceClient",
    "DEFAULT_NOTION_VERSION",
    "GOOGLE_SHEETS_DEFAULT_BASE_URL",
    "GOOGLE_SHEETS_DEFAULT_SCOPE",
    "GOOGLE_SHEETS_DEFAULT_TOKEN_URL",
    "GoogleSheetsClient",
    "LINEAR_DEFAULT_BASE_URL",
    "LinearClient",
    "MongoDBClient",
    "NOTION_DEFAULT_BASE_URL",
    "NotionClient",
    "SupabaseClient",
    "WebhookDeliveryClient",
    "extract_model_metadata",
]
