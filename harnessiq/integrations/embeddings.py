"""Provider-backed embedding backends for runtime features such as tool selection."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from harnessiq.interfaces import EmbeddingBackend, EmbeddingModelClient
from harnessiq.providers import create_provider_embedding_client


@dataclass(frozen=True, slots=True)
class ProviderEmbeddingBackend:
    """Embedding backend backed by one provider client."""

    provider: str
    model_name: str
    client: EmbeddingModelClient
    dimensions: int | None = None
    encoding_format: str | None = None
    user: str | None = None

    def embed_texts(self, texts: Sequence[str]) -> tuple[tuple[float, ...], ...]:
        normalized_texts = _normalize_texts(texts)
        if not normalized_texts:
            return ()
        raw = self.client.create_embedding(
            model_name=self.model_name,
            input_value=list(normalized_texts),
            dimensions=self.dimensions,
            encoding_format=self.encoding_format,
            user=self.user,
        )
        return parse_embedding_response(raw)


def create_embedding_backend_from_spec(
    spec: str,
    *,
    dimensions: int | None = None,
    encoding_format: str | None = None,
    user: str | None = None,
    timeout_seconds: float = 60.0,
) -> EmbeddingBackend:
    """Construct an embedding backend from ``provider:model_name`` syntax."""
    provider, model_name = _parse_embedding_spec(spec)
    return create_provider_embedding_backend(
        provider=provider,
        model_name=model_name,
        dimensions=dimensions,
        encoding_format=encoding_format,
        user=user,
        timeout_seconds=timeout_seconds,
    )


def create_provider_embedding_backend(
    *,
    provider: str,
    model_name: str,
    dimensions: int | None = None,
    encoding_format: str | None = None,
    user: str | None = None,
    timeout_seconds: float = 60.0,
) -> EmbeddingBackend:
    """Construct a provider-backed embedding backend from environment credentials."""
    normalized_provider = provider.strip().lower()
    normalized_model_name = model_name.strip()
    if not normalized_model_name:
        raise ValueError("Embedding model name must not be blank.")
    if normalized_provider != "openai":
        raise ValueError(
            f"Provider-backed embeddings currently support only 'openai'. Received '{provider}'."
        )
    return ProviderEmbeddingBackend(
        provider=normalized_provider,
        model_name=normalized_model_name,
        client=create_provider_embedding_client(normalized_provider, timeout_seconds=timeout_seconds),
        dimensions=dimensions,
        encoding_format=encoding_format,
        user=user,
    )


def parse_embedding_response(raw: Any) -> tuple[tuple[float, ...], ...]:
    """Extract embedding vectors from an OpenAI-style embeddings response."""
    if not isinstance(raw, Mapping):
        raise ValueError("Embedding response must be a mapping payload.")
    data = raw.get("data")
    if not isinstance(data, list):
        raise ValueError("Embedding response payload must define a 'data' list.")
    indexed_vectors: list[tuple[int, tuple[float, ...]]] = []
    for fallback_index, item in enumerate(data):
        if not isinstance(item, Mapping):
            raise ValueError("Embedding response items must be mapping payloads.")
        raw_embedding = item.get("embedding")
        if not isinstance(raw_embedding, list):
            raise ValueError("Embedding response items must include an 'embedding' list.")
        vector = tuple(float(value) for value in raw_embedding)
        raw_index = item.get("index", fallback_index)
        if isinstance(raw_index, bool) or not isinstance(raw_index, int):
            raise ValueError("Embedding response item indexes must be integers when provided.")
        indexed_vectors.append((raw_index, vector))
    indexed_vectors.sort(key=lambda item: item[0])
    return tuple(vector for _, vector in indexed_vectors)


def _normalize_texts(texts: Sequence[str]) -> tuple[str, ...]:
    if isinstance(texts, (str, bytes)):
        raise ValueError("texts must be a sequence of strings, not a single string.")
    normalized: list[str] = []
    for text in texts:
        if not isinstance(text, str):
            raise ValueError("Embedding inputs must be strings.")
        normalized.append(text)
    return tuple(normalized)


def _parse_embedding_spec(spec: str) -> tuple[str, str]:
    provider, separator, model_name = spec.partition(":")
    normalized_provider = provider.strip().lower()
    normalized_model_name = model_name.strip()
    if not separator or not normalized_provider or not normalized_model_name:
        raise ValueError(
            f"Embedding specs must use the form provider:model_name. Received '{spec}'."
        )
    return normalized_provider, normalized_model_name


__all__ = [
    "ProviderEmbeddingBackend",
    "create_embedding_backend_from_spec",
    "create_provider_embedding_backend",
    "parse_embedding_response",
]
