"""Provider delivery clients used by ledger output sinks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from harnessiq.providers.http import RequestExecutor, request_json
from harnessiq.shared.output_sinks import (
    DEFAULT_NOTION_VERSION,
    LINEAR_DEFAULT_BASE_URL,
    NOTION_DEFAULT_BASE_URL,
)


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


__all__ = [
    "ConfluenceClient",
    "DEFAULT_NOTION_VERSION",
    "LINEAR_DEFAULT_BASE_URL",
    "LinearClient",
    "NOTION_DEFAULT_BASE_URL",
    "NotionClient",
    "SupabaseClient",
    "WebhookDeliveryClient",
]
