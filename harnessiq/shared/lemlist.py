"""Lemlist shared operation metadata."""

from __future__ import annotations
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Literal, Sequence

PayloadKind = Literal["none", "object"]


@dataclass(frozen=True, slots=True)
class LemlistOperation:
    """Declarative metadata for one Lemlist API operation."""

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
class LemlistPreparedRequest:
    """A validated Lemlist request ready for execution."""

    operation: LemlistOperation
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
) -> tuple[str, LemlistOperation]:
    return (
        name,
        LemlistOperation(
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


_LEMLIST_CATALOG: OrderedDict[str, LemlistOperation] = OrderedDict(
    (
        # Team
        _op("get_team", "Team", "GET", "/team"),
        # Campaigns
        _op("list_campaigns", "Campaign", "GET", "/campaigns"),
        _op("get_campaign", "Campaign", "GET", "/campaigns/{campaign_id}", required_path_params=("campaign_id",)),
        _op("create_campaign", "Campaign", "POST", "/campaigns", payload_kind="object", payload_required=True),
        _op("update_campaign", "Campaign", "PATCH", "/campaigns/{campaign_id}", required_path_params=("campaign_id",), payload_kind="object", payload_required=True),
        _op("delete_campaign", "Campaign", "DELETE", "/campaigns/{campaign_id}", required_path_params=("campaign_id",)),
        _op("export_campaign_results", "Campaign", "GET", "/campaigns/{campaign_id}/export", required_path_params=("campaign_id",), allow_query=True),
        # Campaign Stats
        _op("get_campaign_stats", "Campaign Stats", "GET", "/campaigns/{campaign_id}/stats", required_path_params=("campaign_id",)),
        # Leads (within campaigns)
        _op("list_campaign_leads", "Campaign Lead", "GET", "/campaigns/{campaign_id}/leads", required_path_params=("campaign_id",), allow_query=True),
        _op("get_campaign_lead", "Campaign Lead", "GET", "/campaigns/{campaign_id}/leads/{lead_id}", required_path_params=("campaign_id", "lead_id")),
        _op("add_lead_to_campaign", "Campaign Lead", "POST", "/campaigns/{campaign_id}/leads/{lead_id}", required_path_params=("campaign_id", "lead_id"), payload_kind="object"),
        _op("delete_lead_from_campaign", "Campaign Lead", "DELETE", "/campaigns/{campaign_id}/leads/{lead_id}", required_path_params=("campaign_id", "lead_id")),
        _op("unsubscribe_lead_from_campaign", "Campaign Lead", "DELETE", "/campaigns/{campaign_id}/leads/{lead_id}/unsubscribe", required_path_params=("campaign_id", "lead_id")),
        # Leads (global)
        _op("list_leads", "Lead", "GET", "/leads", allow_query=True),
        _op("get_lead", "Lead", "GET", "/leads/{lead_id}", required_path_params=("lead_id",)),
        _op("create_lead", "Lead", "POST", "/leads", payload_kind="object", payload_required=True),
        _op("update_lead", "Lead", "PATCH", "/leads/{lead_id}", required_path_params=("lead_id",), payload_kind="object", payload_required=True),
        _op("delete_lead", "Lead", "DELETE", "/leads/{lead_id}", required_path_params=("lead_id",)),
        _op("unsubscribe_lead", "Lead", "DELETE", "/leads/{lead_id}/unsubscribe", required_path_params=("lead_id",)),
        # Lead Activities
        _op("list_lead_activities", "Lead Activity", "GET", "/leads/{lead_id}/activities", required_path_params=("lead_id",), allow_query=True),
        # Sender Identities
        _op("list_sender_identities", "Sender Identity", "GET", "/sender-identities"),
        _op("get_sender_identity", "Sender Identity", "GET", "/sender-identities/{identity_id}", required_path_params=("identity_id",)),
        # Inboxes
        _op("list_inboxes", "Inbox", "GET", "/inboxes"),
        # Hooks (Webhooks)
        _op("list_hooks", "Hook", "GET", "/hooks"),
        _op("get_hook", "Hook", "GET", "/hooks/{hook_id}", required_path_params=("hook_id",)),
        _op("create_hook", "Hook", "POST", "/hooks", payload_kind="object", payload_required=True),
        _op("update_hook", "Hook", "PATCH", "/hooks/{hook_id}", required_path_params=("hook_id",), payload_kind="object", payload_required=True),
        _op("delete_hook", "Hook", "DELETE", "/hooks/{hook_id}", required_path_params=("hook_id",)),
        # Unsubscribes
        _op("list_unsubscribes", "Unsubscribe", "GET", "/unsubscribes", allow_query=True),
        _op("add_unsubscribe", "Unsubscribe", "POST", "/unsubscribes", payload_kind="object", payload_required=True),
        _op("delete_unsubscribe", "Unsubscribe", "DELETE", "/unsubscribes/{email}", required_path_params=("email",)),
        # DNS Checks
        _op("check_dns", "DNS", "GET", "/dns-check"),
        # Activity Feed
        _op("get_activity_feed", "Activity", "GET", "/activities", allow_query=True),
        # Enrichment
        _op("enrich_lead", "Enrichment", "POST", "/leads/{lead_id}/enrich", required_path_params=("lead_id",), payload_kind="object"),
    )
)


def build_lemlist_operation_catalog() -> tuple[LemlistOperation, ...]:
    """Return the supported Lemlist operation catalog in stable order."""
    return tuple(_LEMLIST_CATALOG.values())


def get_lemlist_operation(operation_name: str) -> LemlistOperation:
    """Return a supported Lemlist operation or raise a clear error."""
    op = _LEMLIST_CATALOG.get(operation_name)
    if op is None:
        available = ", ".join(_LEMLIST_CATALOG)
        raise ValueError(f"Unsupported Lemlist operation '{operation_name}'. Available: {available}.")
    return op

__all__ = [
    "LemlistOperation",
    "LemlistPreparedRequest",
    "build_lemlist_operation_catalog",
    "get_lemlist_operation",
]
