from __future__ import annotations

from unittest.mock import patch

import pytest

from harnessiq.integrations import (
    ProviderEmbeddingBackend,
    create_embedding_backend_from_spec,
    create_provider_embedding_backend,
    parse_embedding_response,
)


class _FakeEmbeddingClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def create_embedding(
        self,
        *,
        model_name: str,
        input_value,
        dimensions: int | None = None,
        encoding_format: str | None = None,
        user: str | None = None,
    ) -> dict[str, object]:
        self.calls.append(
            {
                "model_name": model_name,
                "input_value": input_value,
                "dimensions": dimensions,
                "encoding_format": encoding_format,
                "user": user,
            }
        )
        return {
            "data": [
                {"index": 1, "embedding": [2.0, 3.0]},
                {"index": 0, "embedding": [0.5, 1.5]},
            ]
        }


def test_provider_embedding_backend_embeds_texts_in_index_order() -> None:
    client = _FakeEmbeddingClient()
    backend = ProviderEmbeddingBackend(
        provider="openai",
        model_name="text-embedding-3-small",
        client=client,
        dimensions=128,
        encoding_format="float",
        user="demo",
    )

    vectors = backend.embed_texts(("alpha", "beta"))

    assert vectors == ((0.5, 1.5), (2.0, 3.0))
    assert client.calls[0]["model_name"] == "text-embedding-3-small"
    assert client.calls[0]["dimensions"] == 128
    assert client.calls[0]["encoding_format"] == "float"
    assert client.calls[0]["user"] == "demo"


def test_provider_embedding_backend_rejects_single_string_inputs() -> None:
    client = _FakeEmbeddingClient()
    backend = ProviderEmbeddingBackend(
        provider="openai",
        model_name="text-embedding-3-small",
        client=client,
    )

    with pytest.raises(ValueError, match="sequence of strings"):
        backend.embed_texts("alpha")  # type: ignore[arg-type]


def test_parse_embedding_response_requires_data_list() -> None:
    with pytest.raises(ValueError, match="'data' list"):
        parse_embedding_response({"object": "list"})


def test_create_provider_embedding_backend_supports_openai_only() -> None:
    with pytest.raises(ValueError, match="support only 'openai'"):
        create_provider_embedding_backend(provider="grok", model_name="embed-model")


def test_create_embedding_backend_from_spec_constructs_openai_backend() -> None:
    with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}, clear=False):
        backend = create_embedding_backend_from_spec(
            "openai:text-embedding-3-small",
            dimensions=64,
            encoding_format="float",
        )

    assert isinstance(backend, ProviderEmbeddingBackend)
    assert backend.provider == "openai"
    assert backend.model_name == "text-embedding-3-small"
    assert backend.dimensions == 64
    assert backend.encoding_format == "float"
