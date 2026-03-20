"""OpenAI endpoint and authentication helpers."""

from __future__ import annotations

from typing import Mapping

from harnessiq.providers.base import omit_none_values
from harnessiq.providers.http import join_url

from harnessiq.shared.providers import OPENAI_DEFAULT_BASE_URL as DEFAULT_BASE_URL


def build_headers(
    api_key: str,
    *,
    organization: str | None = None,
    project: str | None = None,
    extra_headers: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Build the headers required for OpenAI API requests."""
    headers = omit_none_values(
        {
            "Authorization": f"Bearer {api_key}",
            "OpenAI-Organization": organization,
            "OpenAI-Project": project,
        }
    )
    if extra_headers:
        headers.update(extra_headers)
    return headers


def responses_url(base_url: str = DEFAULT_BASE_URL) -> str:
    """Return the Responses API URL."""
    return join_url(base_url, "/v1/responses")


def chat_completions_url(base_url: str = DEFAULT_BASE_URL) -> str:
    """Return the Chat Completions API URL."""
    return join_url(base_url, "/v1/chat/completions")


def embeddings_url(base_url: str = DEFAULT_BASE_URL) -> str:
    """Return the Embeddings API URL."""
    return join_url(base_url, "/v1/embeddings")


def models_url(base_url: str = DEFAULT_BASE_URL) -> str:
    """Return the Models API URL."""
    return join_url(base_url, "/v1/models")

