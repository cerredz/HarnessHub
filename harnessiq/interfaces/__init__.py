"""Public interface contracts for runtime dependency seams."""

from __future__ import annotations

from .cli import FactoryLoader, IterableFactory, PreparedStoreLoader, ZeroArgumentFactory
from .models import AnthropicModelClient, GeminiModelClient, OpenAIStyleModelClient
from .output_sinks import (
    ConfluenceSinkClient,
    GoogleSheetsSinkClient,
    LinearSinkClient,
    MongoClientFactory,
    MongoCollectionSinkClient,
    NotionSinkClient,
    SupabaseSinkClient,
    WebhookSinkClient,
)
from .provider_clients import (
    PreparedRequest,
    ProviderClientBuilder,
    RequestExecutor,
    RequestPreparingClient,
    ResendRequestClient,
    TimeoutConfig,
)

__all__ = [
    "AnthropicModelClient",
    "ConfluenceSinkClient",
    "FactoryLoader",
    "GeminiModelClient",
    "GoogleSheetsSinkClient",
    "IterableFactory",
    "LinearSinkClient",
    "MongoClientFactory",
    "MongoCollectionSinkClient",
    "NotionSinkClient",
    "OpenAIStyleModelClient",
    "PreparedRequest",
    "PreparedStoreLoader",
    "ProviderClientBuilder",
    "RequestExecutor",
    "RequestPreparingClient",
    "ResendRequestClient",
    "SupabaseSinkClient",
    "TimeoutConfig",
    "WebhookSinkClient",
    "ZeroArgumentFactory",
]
