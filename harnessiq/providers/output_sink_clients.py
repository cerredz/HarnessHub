"""Provider delivery clients used by ledger output sinks."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any, Mapping
from urllib.parse import quote, urlencode

from harnessiq.providers.google_drive.client import TokenRequestExecutor, request_oauth_token
from harnessiq.providers.http import RequestExecutor, request_json
from harnessiq.shared.output_sinks import (
    DEFAULT_NOTION_VERSION,
    GOOGLE_SHEETS_DEFAULT_BASE_URL,
    GOOGLE_SHEETS_DEFAULT_SCOPE,
    GOOGLE_SHEETS_DEFAULT_TOKEN_URL,
    LINEAR_DEFAULT_BASE_URL,
    NOTION_DEFAULT_BASE_URL,
)

MongoClientFactory = Callable[..., Any]


@dataclass(slots=True)
class WebhookDeliveryClient:
    """Small HTTP helper for webhook-style sinks."""

    request_executor: RequestExecutor = request_json

    def post_json(
        self,
        *,
        url: str,
        payload: Mapping[str, Any],
        headers: Mapping[str, str] | None = None,
        timeout_seconds: float = 30.0,
    ) -> Any:
        return self.request_executor(
            "POST",
            url,
            headers=headers,
            json_body=dict(payload),
            timeout_seconds=timeout_seconds,
        )


@dataclass(slots=True)
class NotionClient:
    """Minimal Notion API client for creating database pages."""

    api_token: str
    notion_version: str = DEFAULT_NOTION_VERSION
    request_executor: RequestExecutor = request_json
    base_url: str = NOTION_DEFAULT_BASE_URL

    def create_page(
        self,
        *,
        database_id: str,
        properties: Mapping[str, Any],
        children: list[dict[str, Any]] | None = None,
    ) -> Any:
        payload: dict[str, Any] = {
            "parent": {"database_id": database_id},
            "properties": dict(properties),
        }
        if children:
            payload["children"] = list(children)
        return self.request_executor(
            "POST",
            f"{self.base_url}/pages",
            headers={
                "Authorization": f"Bearer {self.api_token}",
                "Notion-Version": self.notion_version,
            },
            json_body=payload,
            timeout_seconds=30.0,
        )


@dataclass(slots=True)
class ConfluenceClient:
    """Minimal Confluence API client for creating pages."""

    base_url: str
    api_token: str
    request_executor: RequestExecutor = request_json

    def create_page(
        self,
        *,
        space_key: str,
        title: str,
        body_storage: str,
        parent_page_id: str | None = None,
    ) -> Any:
        payload: dict[str, Any] = {
            "space": {"key": space_key},
            "status": "current",
            "title": title,
            "type": "page",
            "body": {
                "storage": {
                    "representation": "storage",
                    "value": body_storage,
                }
            },
        }
        if parent_page_id is not None:
            payload["ancestors"] = [{"id": str(parent_page_id)}]
        return self.request_executor(
            "POST",
            f"{self.base_url.rstrip('/')}/wiki/rest/api/content",
            headers={
                "Authorization": f"Bearer {self.api_token}",
            },
            json_body=payload,
            timeout_seconds=30.0,
        )


@dataclass(slots=True)
class SupabaseClient:
    """Minimal Supabase REST client for inserting rows."""

    base_url: str
    api_key: str
    request_executor: RequestExecutor = request_json

    def insert_row(self, *, table: str, row: Mapping[str, Any], schema: str = "public") -> Any:
        return self.request_executor(
            "POST",
            f"{self.base_url.rstrip('/')}/rest/v1/{table}",
            headers={
                "apikey": self.api_key,
                "Authorization": f"Bearer {self.api_key}",
                "Prefer": "return=representation",
                "Accept-Profile": schema,
                "Content-Profile": schema,
            },
            json_body=dict(row),
            timeout_seconds=30.0,
        )


@dataclass(slots=True)
class LinearClient:
    """Minimal Linear GraphQL client for creating issues."""

    api_key: str
    request_executor: RequestExecutor = request_json
    base_url: str = LINEAR_DEFAULT_BASE_URL

    def create_issue(
        self,
        *,
        team_id: str,
        title: str,
        description: str | None = None,
        priority: int | None = None,
    ) -> Any:
        query = (
            "mutation CreateIssue($input: IssueCreateInput!) { "
            "issueCreate(input: $input) { success issue { id identifier title url } } }"
        )
        variables: dict[str, Any] = {
            "input": {
                "teamId": team_id,
                "title": title,
            }
        }
        if description is not None:
            variables["input"]["description"] = description
        if priority is not None:
            variables["input"]["priority"] = priority
        return self.request_executor(
            "POST",
            self.base_url,
            headers={
                "Authorization": self.api_key,
            },
            json_body={
                "query": query,
                "variables": variables,
            },
            timeout_seconds=30.0,
        )


@dataclass(slots=True)
class GoogleSheetsClient:
    """Minimal Google Sheets API client for header reads and row writes."""

    client_id: str
    client_secret: str
    refresh_token: str
    request_executor: RequestExecutor = request_json
    token_request_executor: TokenRequestExecutor = request_oauth_token
    base_url: str = GOOGLE_SHEETS_DEFAULT_BASE_URL
    token_url: str = GOOGLE_SHEETS_DEFAULT_TOKEN_URL
    scope: str = GOOGLE_SHEETS_DEFAULT_SCOPE
    timeout_seconds: float = 60.0

    def refresh_access_token(self) -> str:
        response = self.token_request_executor(
            self.token_url,
            form_fields={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token,
                "scope": self.scope,
            },
            timeout_seconds=self.timeout_seconds,
        )
        access_token = response.get("access_token")
        if not isinstance(access_token, str) or not access_token.strip():
            raise ValueError("Google Sheets OAuth token response did not include a usable access_token.")
        return access_token.strip()

    def get_values(self, *, spreadsheet_id: str, range_name: str) -> list[list[Any]]:
        response = self.request_executor(
            "GET",
            _google_sheets_values_url(self.base_url, spreadsheet_id=spreadsheet_id, range_name=range_name),
            headers=self._headers(),
            timeout_seconds=self.timeout_seconds,
        )
        values = response.get("values", []) if isinstance(response, Mapping) else []
        if not isinstance(values, list):
            raise ValueError("Google Sheets get_values response did not include a values array.")
        return [list(row) for row in values if isinstance(row, list)]

    def update_values(
        self,
        *,
        spreadsheet_id: str,
        range_name: str,
        values: list[list[Any]],
        value_input_option: str = "RAW",
    ) -> Any:
        return self.request_executor(
            "PUT",
            _google_sheets_values_url(
                self.base_url,
                spreadsheet_id=spreadsheet_id,
                range_name=range_name,
                query={"valueInputOption": value_input_option},
            ),
            headers=self._headers(),
            json_body={"majorDimension": "ROWS", "values": values},
            timeout_seconds=self.timeout_seconds,
        )

    def append_values(
        self,
        *,
        spreadsheet_id: str,
        range_name: str,
        values: list[list[Any]],
        value_input_option: str = "RAW",
        insert_data_option: str = "INSERT_ROWS",
    ) -> Any:
        return self.request_executor(
            "POST",
            _google_sheets_append_url(
                self.base_url,
                spreadsheet_id=spreadsheet_id,
                range_name=range_name,
                query={
                    "insertDataOption": insert_data_option,
                    "valueInputOption": value_input_option,
                },
            ),
            headers=self._headers(),
            json_body={"majorDimension": "ROWS", "values": values},
            timeout_seconds=self.timeout_seconds,
        )

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.refresh_access_token()}"}


@dataclass(slots=True)
class MongoDBClient:
    """Minimal MongoDB client wrapper for inserting ledger documents."""

    connection_uri: str
    database: str
    collection: str
    app_name: str = "HarnessIQ"
    collection_handle: Any | None = None
    mongo_client_factory: MongoClientFactory | None = None

    def insert_documents(self, *, documents: Sequence[Mapping[str, Any]]) -> Any:
        payload = [dict(document) for document in documents]
        if not payload:
            return None
        collection, managed_client = self._resolve_collection()
        try:
            if len(payload) == 1:
                return collection.insert_one(payload[0])
            return collection.insert_many(payload)
        finally:
            if managed_client is not None:
                closer = getattr(managed_client, "close", None)
                if callable(closer):
                    closer()

    def _resolve_collection(self) -> tuple[Any, Any | None]:
        if self.collection_handle is not None:
            return self.collection_handle, None
        client_factory = self.mongo_client_factory or _build_pymongo_client
        client = client_factory(self.connection_uri, appname=self.app_name)
        return client[self.database][self.collection], client


def _build_pymongo_client(connection_uri: str, **kwargs: Any) -> Any:
    try:
        from pymongo import MongoClient
    except ImportError as exc:  # pragma: no cover - depends on optional environment state
        raise RuntimeError(
            "MongoDB support requires the 'pymongo' package. Install HarnessIQ with its MongoDB dependency."
        ) from exc
    return MongoClient(connection_uri, **kwargs)


def _google_sheets_values_url(
    base_url: str,
    *,
    spreadsheet_id: str,
    range_name: str,
    query: Mapping[str, str | int | float | bool] | None = None,
) -> str:
    base = base_url.rstrip("/")
    suffix = ""
    if query:
        suffix = "?" + urlencode({key: value for key, value in query.items()})
    return (
        f"{base}/spreadsheets/{quote(spreadsheet_id, safe='')}"
        f"/values/{quote(range_name, safe='')}{suffix}"
    )


def _google_sheets_append_url(
    base_url: str,
    *,
    spreadsheet_id: str,
    range_name: str,
    query: Mapping[str, str | int | float | bool] | None = None,
) -> str:
    return (
        f"{_google_sheets_values_url(base_url, spreadsheet_id=spreadsheet_id, range_name=range_name, query=query)}"
        ":append"
    )


__all__ = [
    "ConfluenceClient",
    "DEFAULT_NOTION_VERSION",
    "GOOGLE_SHEETS_DEFAULT_BASE_URL",
    "GOOGLE_SHEETS_DEFAULT_SCOPE",
    "GOOGLE_SHEETS_DEFAULT_TOKEN_URL",
    "GoogleSheetsClient",
    "LINEAR_DEFAULT_BASE_URL",
    "LinearClient",
    "MongoDBClient",
    "NOTION_DEFAULT_BASE_URL",
    "NotionClient",
    "SupabaseClient",
    "WebhookDeliveryClient",
]
