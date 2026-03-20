"""Instantly operation catalog, tool definition, and MCP-style tool factory."""

from __future__ import annotations
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Literal, Mapping, Sequence

PayloadKind = Literal["none", "object"]


@dataclass(frozen=True, slots=True)
class InstantlyOperation:
    """Declarative metadata for one Instantly API operation."""

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
class InstantlyPreparedRequest:
    """A validated Instantly request ready for execution."""

    operation: InstantlyOperation
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
) -> tuple[str, InstantlyOperation]:
    return (
        name,
        InstantlyOperation(
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


_INSTANTLY_CATALOG: OrderedDict[str, InstantlyOperation] = OrderedDict(
    (
        # Account
        _op("list_accounts", "Account", "GET", "/accounts"),
        _op("get_account", "Account", "GET", "/accounts/{account_id}", required_path_params=("account_id",)),
        _op("create_account", "Account", "POST", "/accounts", payload_kind="object", payload_required=True),
        _op("update_account", "Account", "PATCH", "/accounts/{account_id}", required_path_params=("account_id",), payload_kind="object", payload_required=True),
        _op("delete_account", "Account", "DELETE", "/accounts/{account_id}", required_path_params=("account_id",)),
        _op("test_account_vitals", "Account", "GET", "/accounts/{account_id}/vitals", required_path_params=("account_id",)),
        _op("get_account_warmup_analytics", "Account", "GET", "/accounts/{account_id}/warmup-analytics", required_path_params=("account_id",)),
        # Account Campaign Mapping
        _op("list_account_campaign_mappings", "Account Campaign Mapping", "GET", "/account-campaign-mappings", allow_query=True),
        _op("create_account_campaign_mapping", "Account Campaign Mapping", "POST", "/account-campaign-mappings", payload_kind="object", payload_required=True),
        _op("delete_account_campaign_mapping", "Account Campaign Mapping", "DELETE", "/account-campaign-mappings/{mapping_id}", required_path_params=("mapping_id",)),
        # Analytics
        _op("get_campaign_summary", "Analytics", "GET", "/analytics/campaign-summary", allow_query=True),
        _op("get_campaign_step_summary", "Analytics", "GET", "/analytics/campaign-step-summary", allow_query=True),
        _op("get_account_summary", "Analytics", "GET", "/analytics/account-summary", allow_query=True),
        # API Key
        _op("list_api_keys", "API Key", "GET", "/api-keys"),
        _op("create_api_key", "API Key", "POST", "/api-keys", payload_kind="object", payload_required=True),
        _op("update_api_key", "API Key", "PATCH", "/api-keys/{key_id}", required_path_params=("key_id",), payload_kind="object", payload_required=True),
        _op("delete_api_key", "API Key", "DELETE", "/api-keys/{key_id}", required_path_params=("key_id",)),
        # Audit Log
        _op("list_audit_logs", "Audit Log", "GET", "/audit-logs", allow_query=True),
        # Background Job
        _op("get_background_job", "Background Job", "GET", "/background-jobs/{job_id}", required_path_params=("job_id",)),
        # Block List Entry
        _op("list_block_list_entries", "Block List Entry", "GET", "/block-list", allow_query=True),
        _op("create_block_list_entry", "Block List Entry", "POST", "/block-list", payload_kind="object", payload_required=True),
        _op("delete_block_list_entry", "Block List Entry", "DELETE", "/block-list/{entry_id}", required_path_params=("entry_id",)),
        # Campaign
        _op("list_campaigns", "Campaign", "GET", "/campaigns", allow_query=True),
        _op("get_campaign", "Campaign", "GET", "/campaigns/{campaign_id}", required_path_params=("campaign_id",)),
        _op("create_campaign", "Campaign", "POST", "/campaigns", payload_kind="object", payload_required=True),
        _op("update_campaign", "Campaign", "PATCH", "/campaigns/{campaign_id}", required_path_params=("campaign_id",), payload_kind="object", payload_required=True),
        _op("delete_campaign", "Campaign", "DELETE", "/campaigns/{campaign_id}", required_path_params=("campaign_id",)),
        _op("launch_campaign", "Campaign", "POST", "/campaigns/{campaign_id}/launch", required_path_params=("campaign_id",)),
        _op("pause_campaign", "Campaign", "POST", "/campaigns/{campaign_id}/pause", required_path_params=("campaign_id",)),
        # Campaign Subsequence
        _op("list_subsequences", "Campaign Subsequence", "GET", "/campaign-subsequences", allow_query=True),
        _op("get_subsequence", "Campaign Subsequence", "GET", "/campaign-subsequences/{subsequence_id}", required_path_params=("subsequence_id",)),
        _op("create_subsequence", "Campaign Subsequence", "POST", "/campaign-subsequences", payload_kind="object", payload_required=True),
        _op("update_subsequence", "Campaign Subsequence", "PATCH", "/campaign-subsequences/{subsequence_id}", required_path_params=("subsequence_id",), payload_kind="object", payload_required=True),
        _op("delete_subsequence", "Campaign Subsequence", "DELETE", "/campaign-subsequences/{subsequence_id}", required_path_params=("subsequence_id",)),
        # Custom Tag
        _op("list_custom_tags", "Custom Tag", "GET", "/custom-tags", allow_query=True),
        _op("create_custom_tag", "Custom Tag", "POST", "/custom-tags", payload_kind="object", payload_required=True),
        _op("update_custom_tag", "Custom Tag", "PATCH", "/custom-tags/{tag_id}", required_path_params=("tag_id",), payload_kind="object", payload_required=True),
        _op("delete_custom_tag", "Custom Tag", "DELETE", "/custom-tags/{tag_id}", required_path_params=("tag_id",)),
        # Custom Tag Mapping
        _op("list_custom_tag_mappings", "Custom Tag Mapping", "GET", "/custom-tag-mappings", allow_query=True),
        _op("create_custom_tag_mapping", "Custom Tag Mapping", "POST", "/custom-tag-mappings", payload_kind="object", payload_required=True),
        _op("delete_custom_tag_mapping", "Custom Tag Mapping", "DELETE", "/custom-tag-mappings/{mapping_id}", required_path_params=("mapping_id",)),
        # Email
        _op("list_emails", "Email", "GET", "/emails", allow_query=True),
        _op("get_email", "Email", "GET", "/emails/{email_id}", required_path_params=("email_id",)),
        _op("list_email_replies", "Email", "GET", "/emails/{email_id}/replies", required_path_params=("email_id",)),
        _op("mark_email_as_read", "Email", "POST", "/emails/{email_id}/mark-as-read", required_path_params=("email_id",)),
        _op("reply_to_email", "Email", "POST", "/emails/{email_id}/reply", required_path_params=("email_id",), payload_kind="object", payload_required=True),
        # Email Verification
        _op("verify_email", "Email Verification", "POST", "/email-verification", payload_kind="object", payload_required=True),
        # Inbox Placement Test
        _op("list_inbox_placement_tests", "Inbox Placement Test", "GET", "/inbox-placement-tests", allow_query=True),
        _op("get_inbox_placement_test", "Inbox Placement Test", "GET", "/inbox-placement-tests/{test_id}", required_path_params=("test_id",)),
        _op("create_inbox_placement_test", "Inbox Placement Test", "POST", "/inbox-placement-tests", payload_kind="object", payload_required=True),
        # Lead
        _op("list_leads", "Lead", "GET", "/leads", allow_query=True),
        _op("get_lead", "Lead", "GET", "/leads/{lead_id}", required_path_params=("lead_id",)),
        _op("create_lead", "Lead", "POST", "/leads", payload_kind="object", payload_required=True),
        _op("update_lead", "Lead", "PATCH", "/leads/{lead_id}", required_path_params=("lead_id",), payload_kind="object", payload_required=True),
        _op("delete_lead", "Lead", "DELETE", "/leads/{lead_id}", required_path_params=("lead_id",)),
        _op("move_lead", "Lead", "POST", "/leads/{lead_id}/move", required_path_params=("lead_id",), payload_kind="object", payload_required=True),
        _op("set_lead_interest", "Lead", "POST", "/leads/{lead_id}/interest", required_path_params=("lead_id",), payload_kind="object", payload_required=True),
        # Lead Label
        _op("list_lead_labels", "Lead Label", "GET", "/lead-labels", allow_query=True),
        _op("create_lead_label", "Lead Label", "POST", "/lead-labels", payload_kind="object", payload_required=True),
        _op("update_lead_label", "Lead Label", "PATCH", "/lead-labels/{label_id}", required_path_params=("label_id",), payload_kind="object", payload_required=True),
        _op("delete_lead_label", "Lead Label", "DELETE", "/lead-labels/{label_id}", required_path_params=("label_id",)),
        # Lead List
        _op("list_lead_lists", "Lead List", "GET", "/lead-lists", allow_query=True),
        _op("get_lead_list", "Lead List", "GET", "/lead-lists/{list_id}", required_path_params=("list_id",)),
        _op("create_lead_list", "Lead List", "POST", "/lead-lists", payload_kind="object", payload_required=True),
        _op("update_lead_list", "Lead List", "PATCH", "/lead-lists/{list_id}", required_path_params=("list_id",), payload_kind="object", payload_required=True),
        _op("delete_lead_list", "Lead List", "DELETE", "/lead-lists/{list_id}", required_path_params=("list_id",)),
        # Webhook
        _op("list_webhooks", "Webhook", "GET", "/webhooks", allow_query=True),
        _op("get_webhook", "Webhook", "GET", "/webhooks/{webhook_id}", required_path_params=("webhook_id",)),
        _op("create_webhook", "Webhook", "POST", "/webhooks", payload_kind="object", payload_required=True),
        _op("update_webhook", "Webhook", "PATCH", "/webhooks/{webhook_id}", required_path_params=("webhook_id",), payload_kind="object", payload_required=True),
        _op("delete_webhook", "Webhook", "DELETE", "/webhooks/{webhook_id}", required_path_params=("webhook_id",)),
        # Webhook Event
        _op("list_webhook_events", "Webhook Event", "GET", "/webhook-events", allow_query=True),
        _op("get_webhook_event", "Webhook Event", "GET", "/webhook-events/{event_id}", required_path_params=("event_id",)),
        # Workspace
        _op("get_workspace", "Workspace", "GET", "/workspace"),
        _op("update_workspace", "Workspace", "PATCH", "/workspace", payload_kind="object", payload_required=True),
    )
)


def build_instantly_operation_catalog() -> tuple[InstantlyOperation, ...]:
    """Return the supported Instantly operation catalog in stable order."""
    return tuple(_INSTANTLY_CATALOG.values())


def get_instantly_operation(operation_name: str) -> InstantlyOperation:
    """Return a supported Instantly operation or raise a clear error."""
    op = _INSTANTLY_CATALOG.get(operation_name)
    if op is None:
        available = ", ".join(_INSTANTLY_CATALOG)
        raise ValueError(f"Unsupported Instantly operation '{operation_name}'. Available: {available}.")
    return op

__all__ = [
    "InstantlyOperation",
    "InstantlyPreparedRequest",
    "build_instantly_operation_catalog",
    "get_instantly_operation",
]
