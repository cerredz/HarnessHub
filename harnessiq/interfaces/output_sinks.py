"""Interface contracts for ledger output sink delivery clients."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any, Mapping, Protocol, runtime_checkable


@runtime_checkable
class WebhookSinkClient(Protocol):
    """Describe webhook-style delivery clients."""

    def post_json(
        self,
        *,
        url: str,
        payload: Mapping[str, Any],
        headers: Mapping[str, str] | None = None,
        timeout_seconds: float = 30.0,
    ) -> Any:
        """Send one JSON payload to a webhook endpoint."""


@runtime_checkable
class NotionSinkClient(Protocol):
    """Describe the Notion page-creation surface used by ledger sinks."""

    def create_page(
        self,
        *,
        database_id: str,
        properties: Mapping[str, Any],
        children: list[dict[str, Any]] | None = None,
    ) -> Any:
        """Create one page in a Notion database."""


@runtime_checkable
class ConfluenceSinkClient(Protocol):
    """Describe the Confluence page-creation surface used by ledger sinks."""

    def create_page(
        self,
        *,
        space_key: str,
        title: str,
        body_storage: str,
        parent_page_id: str | None = None,
    ) -> Any:
        """Create one Confluence page."""


@runtime_checkable
class SupabaseSinkClient(Protocol):
    """Describe the Supabase row-insert surface used by ledger sinks."""

    def insert_row(self, *, table: str, row: Mapping[str, Any], schema: str = "public") -> Any:
        """Insert one row into a Supabase table."""


@runtime_checkable
class LinearSinkClient(Protocol):
    """Describe the Linear issue-creation surface used by ledger sinks."""

    def create_issue(
        self,
        *,
        team_id: str,
        title: str,
        description: str | None = None,
        priority: int | None = None,
    ) -> Any:
        """Create one Linear issue."""


@runtime_checkable
class GoogleSheetsSinkClient(Protocol):
    """Describe the Google Sheets read/write surface used by ledger sinks."""

    def get_values(self, *, spreadsheet_id: str, range_name: str) -> list[list[Any]]:
        """Read values from one range."""

    def update_values(
        self,
        *,
        spreadsheet_id: str,
        range_name: str,
        values: list[list[Any]],
        value_input_option: str = "RAW",
    ) -> Any:
        """Write values to one range."""

    def append_values(
        self,
        *,
        spreadsheet_id: str,
        range_name: str,
        values: list[list[Any]],
        value_input_option: str = "RAW",
        insert_data_option: str = "INSERT_ROWS",
    ) -> Any:
        """Append values to one range."""


@runtime_checkable
class MongoCollectionSinkClient(Protocol):
    """Describe the MongoDB document-insert surface used by ledger sinks."""

    def insert_documents(self, *, documents: Sequence[Mapping[str, Any]]) -> Any:
        """Insert one or more documents."""


MongoClientFactory = Callable[..., Any]


__all__ = [
    "ConfluenceSinkClient",
    "GoogleSheetsSinkClient",
    "LinearSinkClient",
    "MongoClientFactory",
    "MongoCollectionSinkClient",
    "NotionSinkClient",
    "SupabaseSinkClient",
    "WebhookSinkClient",
]
