"""Shared constants for provider-backed output sink integrations."""

from __future__ import annotations

DEFAULT_NOTION_VERSION = "2022-06-28"
NOTION_DEFAULT_BASE_URL = "https://api.notion.com/v1"
LINEAR_DEFAULT_BASE_URL = "https://api.linear.app/graphql"

__all__ = [
    "DEFAULT_NOTION_VERSION",
    "LINEAR_DEFAULT_BASE_URL",
    "NOTION_DEFAULT_BASE_URL",
]
