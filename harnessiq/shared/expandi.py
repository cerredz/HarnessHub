"""Expandi shared operation metadata."""

from __future__ import annotations
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Literal, Sequence

PayloadKind = Literal["none", "object"]


@dataclass(frozen=True, slots=True)
class ExpandiOperation:
    """Declarative metadata for one Expandi API operation."""

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
class ExpandiPreparedRequest:
    """A validated Expandi request ready for execution."""

    operation: ExpandiOperation
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
) -> tuple[str, ExpandiOperation]:
    return (
        name,
        ExpandiOperation(
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


_EXPANDI_CATALOG: OrderedDict[str, ExpandiOperation] = OrderedDict(
    (
        # Campaigns (v1)
        _op("list_campaigns", "Campaigns", "GET", "/open-api/campaigns/"),
        _op("add_prospect_to_campaign", "Campaigns", "POST", "/open-api/campaign-instance/{campaign_id}/assign/", required_path_params=("campaign_id",), payload_kind="object", payload_required=True),
        _op("add_multiple_prospects_to_campaign", "Campaigns", "POST", "/open-api/campaign-instance/{campaign_id}/assign_multiple/", required_path_params=("campaign_id",), payload_kind="object", payload_required=True),
        _op("pause_campaign_contact", "Campaigns", "GET", "/open-api/campaign-contact/{contact_id}/pause/", required_path_params=("contact_id",)),
        _op("resume_campaign_contact", "Campaigns", "GET", "/open-api/campaign-contact/{contact_id}/resume/", required_path_params=("contact_id",)),

        # Campaign Contacts v2
        _op("create_campaign_contact_v2", "Campaign Contacts", "POST", "/open-api/v2/li_accounts/campaign_instances/{campaign_id}/create_contact/", required_path_params=("campaign_id",), payload_kind="object", payload_required=True),
        _op("update_campaign_contact_v2", "Campaign Contacts", "PATCH", "/open-api/v2/li_accounts/campaign_instances/{campaign_id}/update_contact/", required_path_params=("campaign_id",), payload_kind="object", payload_required=True),
        _op("delete_campaign_contact_v2", "Campaign Contacts", "DELETE", "/open-api/v2/li_accounts/campaign_instances/{campaign_id}/delete_contact/", required_path_params=("campaign_id",), payload_kind="object", payload_required=True),

        # LinkedIn Accounts
        _op("list_linkedin_accounts", "LinkedIn Accounts", "GET", "/open-api/fetch_li_accounts/"),
        _op("list_linkedin_accounts_v2", "LinkedIn Accounts", "GET", "/open-api/v2/li_accounts/", allow_query=True),
        _op("send_connection_request", "LinkedIn Accounts", "POST", "/open-api/v2/li_accounts/{account_id}/actions/connection_request/", required_path_params=("account_id",), payload_kind="object", payload_required=True),
        _op("send_message", "LinkedIn Accounts", "POST", "/open-api/v2/li_accounts/{account_id}/actions/message/", required_path_params=("account_id",), payload_kind="object", payload_required=True),
        _op("send_email", "LinkedIn Accounts", "POST", "/open-api/v2/li_accounts/{account_id}/actions/email/", required_path_params=("account_id",), payload_kind="object", payload_required=True),
        _op("check_action_status", "LinkedIn Accounts", "POST", "/open-api/v2/li_accounts/actions/{action_id}/check_action_status/", required_path_params=("action_id",), payload_kind="object", payload_required=True),

        # Messaging (v1)
        _op("fetch_messages", "Messaging", "GET", "/open-api/fetch_messages/"),
        _op("fetch_messages_for_contact", "Messaging", "GET", "/open-api/fetch_messages_contact/"),
        _op("send_message_to_contact", "Messaging", "POST", "/open-api/send_message_to_contact", payload_kind="object", payload_required=True),
        _op("reply_to_message", "Messaging", "POST", "/open-api/reply/", payload_kind="object", payload_required=True),

        # Webhooks
        _op("enable_messaging_webhook", "Webhooks", "POST", "/open-api/li_accounts/messaging/webhooks/enable", payload_kind="object", payload_required=True),
        _op("disable_messaging_webhook", "Webhooks", "POST", "/open-api/li_accounts/messaging/webhooks/disable", payload_kind="object", payload_required=True),

        # Miscellaneous
        _op("add_to_blacklist", "Miscellaneous", "POST", "/open-api/blacklist/", payload_kind="object", payload_required=True),
        _op("fetch_contacts", "Miscellaneous", "GET", "/open-api/fetch_contacts/"),
    )
)


def build_expandi_operation_catalog() -> tuple[ExpandiOperation, ...]:
    """Return the supported Expandi operation catalog in stable order."""
    return tuple(_EXPANDI_CATALOG.values())


def get_expandi_operation(operation_name: str) -> ExpandiOperation:
    """Return a supported Expandi operation or raise a clear error."""
    op = _EXPANDI_CATALOG.get(operation_name)
    if op is None:
        available = ", ".join(_EXPANDI_CATALOG)
        raise ValueError(
            f"Unsupported Expandi operation '{operation_name}'. Available: {available}."
        )
    return op

__all__ = [
    "ExpandiOperation",
    "ExpandiPreparedRequest",
    "build_expandi_operation_catalog",
    "get_expandi_operation",
]
