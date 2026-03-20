"""Smartlead operation catalog, tool definition, and MCP-style tool factory."""

from __future__ import annotations
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Literal, Sequence

PayloadKind = Literal["none", "object"]


@dataclass(frozen=True, slots=True)
class SmartleadOperation:
    """Declarative metadata for one Smartlead API operation."""

    name: str
    category: str
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"]
    path_hint: str
    required_path_params: tuple[str, ...] = ()
    payload_kind: PayloadKind = "none"
    payload_required: bool = False
    allow_query: bool = False

    def summary(self) -> str:
        return f"{self.name} ({self.method} {self.path_hint})"


@dataclass(frozen=True, slots=True)
class SmartleadPreparedRequest:
    """A validated Smartlead request ready for execution."""

    operation: SmartleadOperation
    method: str
    path: str
    url: str
    headers: dict[str, str]
    json_body: Any | None


# ---------------------------------------------------------------------------
# Catalog
# ---------------------------------------------------------------------------

def _op(
    name: str,
    category: str,
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"],
    path_hint: str,
    *,
    required_path_params: Sequence[str] = (),
    payload_kind: PayloadKind = "none",
    payload_required: bool = False,
    allow_query: bool = False,
) -> tuple[str, SmartleadOperation]:
    return (
        name,
        SmartleadOperation(
            name=name,
            category=category,
            method=method,
            path_hint=path_hint,
            required_path_params=tuple(required_path_params),
            payload_kind=payload_kind,
            payload_required=payload_required,
            allow_query=allow_query,
        ),
    )


_SMARTLEAD_CATALOG: OrderedDict[str, SmartleadOperation] = OrderedDict(
    (
        # Campaigns
        _op("list_campaigns", "Campaigns", "GET", "/campaigns/", allow_query=True),
        _op("get_campaign", "Campaigns", "GET", "/campaigns/{campaign_id}", required_path_params=("campaign_id",)),
        _op("create_campaign", "Campaigns", "POST", "/campaigns/create", payload_kind="object", payload_required=True),
        _op("update_campaign_status", "Campaigns", "PATCH", "/campaigns/{campaign_id}/status", required_path_params=("campaign_id",), payload_kind="object", payload_required=True),
        _op("update_campaign_schedule", "Campaigns", "POST", "/campaigns/{campaign_id}/schedule", required_path_params=("campaign_id",), payload_kind="object", payload_required=True),
        _op("update_campaign_settings", "Campaigns", "PATCH", "/campaigns/{campaign_id}/settings", required_path_params=("campaign_id",), payload_kind="object", payload_required=True),
        _op("delete_campaign", "Campaigns", "DELETE", "/campaigns/{campaign_id}", required_path_params=("campaign_id",)),

        # Sequences
        _op("get_campaign_sequences", "Sequences", "GET", "/campaigns/{campaign_id}/sequences", required_path_params=("campaign_id",)),
        _op("create_campaign_sequences", "Sequences", "POST", "/campaigns/{campaign_id}/sequences", required_path_params=("campaign_id",), payload_kind="object", payload_required=True),

        # Email Accounts
        _op("list_email_accounts", "Email Accounts", "GET", "/email-accounts/", allow_query=True),
        _op("get_email_account", "Email Accounts", "GET", "/email-accounts/{email_account_id}/", required_path_params=("email_account_id",)),
        _op("save_email_account", "Email Accounts", "POST", "/email-accounts/save", payload_kind="object", payload_required=True),
        _op("update_email_account", "Email Accounts", "POST", "/email-accounts/{email_account_id}", required_path_params=("email_account_id",), payload_kind="object", payload_required=True),
        _op("update_email_account_warmup", "Email Accounts", "POST", "/email-accounts/{email_account_id}/warmup", required_path_params=("email_account_id",), payload_kind="object", payload_required=True),
        _op("get_email_account_warmup_stats", "Email Accounts", "GET", "/email-accounts/{email_account_id}/warmup-stats", required_path_params=("email_account_id",)),
        _op("list_campaign_email_accounts", "Email Accounts", "GET", "/campaigns/{campaign_id}/email-accounts", required_path_params=("campaign_id",)),
        _op("add_email_account_to_campaign", "Email Accounts", "POST", "/campaigns/{campaign_id}/email-accounts", required_path_params=("campaign_id",), payload_kind="object", payload_required=True),
        _op("remove_email_account_from_campaign", "Email Accounts", "DELETE", "/campaigns/{campaign_id}/email-accounts", required_path_params=("campaign_id",), payload_kind="object", payload_required=True),

        # Leads
        _op("list_campaign_leads", "Leads", "GET", "/campaigns/{campaign_id}/leads", required_path_params=("campaign_id",), allow_query=True),
        _op("add_leads_to_campaign", "Leads", "POST", "/campaigns/{campaign_id}/leads", required_path_params=("campaign_id",), payload_kind="object", payload_required=True),
        _op("fetch_lead_by_email", "Leads", "GET", "/leads/", allow_query=True),
        _op("fetch_lead_categories", "Leads", "GET", "/leads/fetch-categories"),
        _op("fetch_global_leads", "Leads", "GET", "/leads/global-leads", allow_query=True),
        _op("get_lead_campaigns", "Leads", "GET", "/leads/{lead_id}/campaigns", required_path_params=("lead_id",)),
        _op("update_lead", "Leads", "POST", "/campaigns/{campaign_id}/leads/{lead_id}", required_path_params=("campaign_id", "lead_id"), payload_kind="object", payload_required=True),
        _op("pause_lead", "Leads", "POST", "/campaigns/{campaign_id}/leads/{lead_id}/pause", required_path_params=("campaign_id", "lead_id")),
        _op("resume_lead", "Leads", "POST", "/campaigns/{campaign_id}/leads/{lead_id}/resume", required_path_params=("campaign_id", "lead_id")),
        _op("delete_lead", "Leads", "DELETE", "/campaigns/{campaign_id}/leads/{lead_id}", required_path_params=("campaign_id", "lead_id")),
        _op("unsubscribe_lead_from_campaign", "Leads", "POST", "/campaigns/{campaign_id}/leads/{lead_id}/unsubscribe", required_path_params=("campaign_id", "lead_id")),
        _op("unsubscribe_lead_globally", "Leads", "POST", "/leads/{lead_id}/unsubscribe", required_path_params=("lead_id",)),
        _op("add_domain_to_block_list", "Leads", "POST", "/leads/add-domain-block-list", payload_kind="object", payload_required=True),

        # Master Inbox
        _op("get_message_history", "Master Inbox", "GET", "/campaigns/{campaign_id}/leads/{lead_id}/message-history", required_path_params=("campaign_id", "lead_id"), allow_query=True),
        _op("reply_to_lead", "Master Inbox", "POST", "/email-campaigns/send-email-thread", payload_kind="object", payload_required=True),
        _op("forward_reply", "Master Inbox", "POST", "/email-campaigns/forward-reply-email", payload_kind="object", payload_required=True),

        # Analytics
        _op("get_campaign_analytics", "Analytics", "GET", "/campaigns/{campaign_id}/analytics", required_path_params=("campaign_id",)),
        _op("get_campaign_analytics_by_date", "Analytics", "GET", "/campaigns/{campaign_id}/analytics-by-date", required_path_params=("campaign_id",), allow_query=True),
        _op("get_campaign_statistics", "Analytics", "GET", "/campaigns/{campaign_id}/statistics", required_path_params=("campaign_id",), allow_query=True),
        _op("get_campaign_lead_stats", "Analytics", "GET", "/campaigns/{campaign_id}/lead-stats", required_path_params=("campaign_id",)),
        _op("get_account_analytics", "Analytics", "GET", "/analytics/overview"),

        # Webhooks
        _op("list_campaign_webhooks", "Webhooks", "GET", "/campaigns/{campaign_id}/webhooks", required_path_params=("campaign_id",)),
        _op("save_campaign_webhook", "Webhooks", "POST", "/campaigns/{campaign_id}/webhooks", required_path_params=("campaign_id",), payload_kind="object", payload_required=True),
        _op("delete_campaign_webhook", "Webhooks", "DELETE", "/campaigns/{campaign_id}/webhooks", required_path_params=("campaign_id",), payload_kind="object", payload_required=True),

        # Client Management
        _op("list_clients", "Clients", "GET", "/client/"),
        _op("save_client", "Clients", "POST", "/client/save", payload_kind="object", payload_required=True),
        _op("list_client_api_keys", "Clients", "GET", "/client/api-key", allow_query=True),
        _op("create_client_api_key", "Clients", "POST", "/client/api-key", payload_kind="object", payload_required=True),
        _op("delete_client_api_key", "Clients", "DELETE", "/client/api-key/{key_id}", required_path_params=("key_id",)),
        _op("reset_client_api_key", "Clients", "PUT", "/client/api-key/reset/{key_id}", required_path_params=("key_id",)),
    )
)


def build_smartlead_operation_catalog() -> tuple[SmartleadOperation, ...]:
    """Return the supported Smartlead operation catalog in stable order."""
    return tuple(_SMARTLEAD_CATALOG.values())


def get_smartlead_operation(operation_name: str) -> SmartleadOperation:
    """Return a supported Smartlead operation or raise a clear error."""
    op = _SMARTLEAD_CATALOG.get(operation_name)
    if op is None:
        available = ", ".join(_SMARTLEAD_CATALOG)
        raise ValueError(
            f"Unsupported Smartlead operation '{operation_name}'. Available: {available}."
        )
    return op

__all__ = [
    "SmartleadOperation",
    "SmartleadPreparedRequest",
    "build_smartlead_operation_catalog",
    "get_smartlead_operation",
]
