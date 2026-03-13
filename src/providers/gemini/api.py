"""Gemini endpoint and API-key helpers."""

from __future__ import annotations

from src.providers.http import join_url

DEFAULT_BASE_URL = "https://generativelanguage.googleapis.com"
DEFAULT_API_VERSION = "v1beta"


def build_headers() -> dict[str, str]:
    """Build the headers required for Gemini API requests."""
    return {"Content-Type": "application/json"}


def models_url(
    api_key: str,
    *,
    base_url: str = DEFAULT_BASE_URL,
    api_version: str = DEFAULT_API_VERSION,
) -> str:
    """Return the Gemini models URL."""
    return join_url(base_url, f"/{api_version}/models", query={"key": api_key})


def generate_content_url(
    model_name: str,
    api_key: str,
    *,
    base_url: str = DEFAULT_BASE_URL,
    api_version: str = DEFAULT_API_VERSION,
) -> str:
    """Return the Gemini generate-content URL."""
    return join_url(base_url, f"/{api_version}/models/{model_name}:generateContent", query={"key": api_key})


def count_tokens_url(
    model_name: str,
    api_key: str,
    *,
    base_url: str = DEFAULT_BASE_URL,
    api_version: str = DEFAULT_API_VERSION,
) -> str:
    """Return the Gemini count-tokens URL."""
    return join_url(base_url, f"/{api_version}/models/{model_name}:countTokens", query={"key": api_key})


def cached_contents_url(
    api_key: str,
    *,
    base_url: str = DEFAULT_BASE_URL,
    api_version: str = DEFAULT_API_VERSION,
) -> str:
    """Return the Gemini cached-contents URL."""
    return join_url(base_url, f"/{api_version}/cachedContents", query={"key": api_key})
