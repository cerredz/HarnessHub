"""Provider-side helpers for ledger output sink delivery and metadata extraction."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from harnessiq.providers.http import RequestExecutor, request_json
from harnessiq.shared.output_sinks import (
    DEFAULT_NOTION_VERSION,
    LINEAR_DEFAULT_BASE_URL,
    NOTION_DEFAULT_BASE_URL,
)


def extract_model_metadata(model: Any) -> dict[str, Any]:
    """Return best-effort provider/model metadata for an injected AgentModel."""
    metadata: dict[str, Any] = {
        "model_class": type(model).__name__,
        "model_module": type(model).__module__,
    }
    custom = getattr(model, "ledger_metadata", None)
    if callable(custom):
        provided = custom()
        if isinstance(provided, Mapping):
            metadata.update({str(key): value for key, value in provided.items()})
            return metadata

    provider = _extract_provider_name(model)
    model_name = _extract_model_name(model)
    if provider is not None:
        metadata["provider"] = provider
    if model_name is not None:
        metadata["model_name"] = model_name

    tracing_enabled = _coerce_optional_bool(getattr(model, "_tracing_enabled", None))
    if tracing_enabled is not None:
        metadata["tracing_enabled"] = tracing_enabled
    project_name = _coerce_optional_string(getattr(model, "_project_name", None))
    if project_name is not None:
        metadata["project_name"] = project_name
    return metadata


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


def _extract_provider_name(model: Any) -> str | None:
    for attribute_name in ("provider", "_provider", "provider_name", "_provider_name"):
        candidate = _coerce_optional_string(getattr(model, attribute_name, None))
        if candidate is not None:
            return candidate

    module = type(model).__module__.lower()
    for name in (
        "openai",
        "anthropic",
        "grok",
        "gemini",
        "exa",
        "resend",
        "notion",
        "confluence",
        "supabase",
        "linear",
        "slack",
        "discord",
    ):
        if name in module:
            return name

    client = getattr(model, "_client", None)
    if client is None:
        return None
    client_module = type(client).__module__.lower()
    for name in (
        "openai",
        "anthropic",
        "grok",
        "gemini",
        "exa",
        "resend",
        "notion",
        "confluence",
        "supabase",
        "linear",
    ):
        if name in client_module:
            return name
    return None


def _extract_model_name(model: Any) -> str | None:
    for attribute_name in ("model_name", "_model_name", "model", "_model"):
        candidate = _coerce_optional_string(getattr(model, attribute_name, None))
        if candidate is not None:
            return candidate
    return None


def _coerce_optional_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    return None


def _coerce_optional_string(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


__all__ = [
    "ConfluenceClient",
    "DEFAULT_NOTION_VERSION",
    "LinearClient",
    "NotionClient",
    "SupabaseClient",
    "WebhookDeliveryClient",
    "extract_model_metadata",
]
