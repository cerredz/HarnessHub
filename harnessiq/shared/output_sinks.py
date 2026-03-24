"""Shared constants for provider-backed output sink integrations."""

from __future__ import annotations

GOOGLE_SHEETS_DEFAULT_BASE_URL = "https://sheets.googleapis.com/v4"
GOOGLE_SHEETS_DEFAULT_SCOPE = "https://www.googleapis.com/auth/spreadsheets"
GOOGLE_SHEETS_DEFAULT_TOKEN_URL = "https://oauth2.googleapis.com/token"
DEFAULT_NOTION_VERSION = "2022-06-28"
NOTION_DEFAULT_BASE_URL = "https://api.notion.com/v1"
LINEAR_DEFAULT_BASE_URL = "https://api.linear.app/graphql"

__all__ = [
    "DEFAULT_NOTION_VERSION",
    "GOOGLE_SHEETS_DEFAULT_BASE_URL",
    "GOOGLE_SHEETS_DEFAULT_SCOPE",
    "GOOGLE_SHEETS_DEFAULT_TOKEN_URL",
    "LINEAR_DEFAULT_BASE_URL",
    "NOTION_DEFAULT_BASE_URL",
]
