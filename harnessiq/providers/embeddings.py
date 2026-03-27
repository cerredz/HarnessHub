"""Provider-backed embedding client helpers."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from harnessiq.interfaces import EmbeddingModelClient


def create_provider_embedding_client(
    provider: str,
    *,
    timeout_seconds: float = 60.0,
) -> "EmbeddingModelClient":
    """Construct an embedding-capable provider client from environment credentials."""
    normalized_provider = str(provider).strip().lower()
    if normalized_provider != "openai":
        raise ValueError(
            f"Provider-backed embeddings currently support only 'openai'. Received '{provider}'."
        )
    from harnessiq.providers.openai import OpenAIClient

    return OpenAIClient(
        api_key=_require_env(("OPENAI_API_KEY",), provider=normalized_provider),
        organization=os.environ.get("OPENAI_ORGANIZATION"),
        project=os.environ.get("OPENAI_PROJECT"),
        timeout_seconds=timeout_seconds,
    )


def _require_env(names: tuple[str, ...], *, provider: str) -> str:
    for env_name in names:
        raw = os.environ.get(env_name)
        if raw is None:
            continue
        normalized = raw.strip()
        if normalized:
            return normalized
    rendered_names = ", ".join(names)
    raise RuntimeError(
        f"{provider} embedding adapter requires one of the following environment variables: {rendered_names}."
    )


__all__ = ["create_provider_embedding_client"]
