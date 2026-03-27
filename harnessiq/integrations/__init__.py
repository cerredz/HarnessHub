"""Runtime integrations: concrete model adapters and browser session helpers."""

from .embeddings import (
    ProviderEmbeddingBackend,
    create_embedding_backend_from_spec,
    create_provider_embedding_backend,
    parse_embedding_response,
)
from .agent_models import (
    AnthropicAgentModel,
    DEFAULT_ANTHROPIC_MAX_OUTPUT_TOKENS,
    DEFAULT_GROK_MODEL,
    GeminiAgentModel,
    GrokAgentModel,
    OpenAIAgentModel,
    ProviderAgentModel,
    build_provider_messages,
    create_grok_model,
    create_model_from_profile,
    create_model_from_spec,
    create_provider_model,
    normalize_model_provider,
    parse_model_spec,
)

__all__ = [
    "AnthropicAgentModel",
    "DEFAULT_ANTHROPIC_MAX_OUTPUT_TOKENS",
    "DEFAULT_GROK_MODEL",
    "GeminiAgentModel",
    "GrokAgentModel",
    "OpenAIAgentModel",
    "ProviderEmbeddingBackend",
    "ProviderAgentModel",
    "build_provider_messages",
    "create_embedding_backend_from_spec",
    "create_grok_model",
    "create_model_from_profile",
    "create_model_from_spec",
    "create_provider_embedding_backend",
    "create_provider_model",
    "normalize_model_provider",
    "parse_embedding_response",
    "parse_model_spec",
]
