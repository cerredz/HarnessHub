"""Shared Resend operation catalog construction and lookup."""

from __future__ import annotations

from collections import OrderedDict
from typing import Sequence

from harnessiq.shared.resend_models import PayloadKind, ResendOperation
from harnessiq.shared.resend_paths import (
    build_contact_collection_path,
    build_contact_item_path,
    static_path_builder,
)


def build_resend_operation_catalog() -> tuple[ResendOperation, ...]:
    """Return the supported Resend operation catalog in stable order."""
    return tuple(_RESEND_OPERATION_CATALOG.values())


def get_resend_operation(operation_name: str) -> ResendOperation:
    """Return a supported Resend operation or raise a clear error."""
    operation = _RESEND_OPERATION_CATALOG.get(operation_name)
    if operation is None:
        available = ", ".join(_RESEND_OPERATION_CATALOG)
        raise ValueError(f"Unsupported Resend operation '{operation_name}'. Available operations: {available}.")
    return operation


def _operation(
    name: str,
    category: str,
    method: str,
    path_hint: str,
    *,
    path_builder=None,
    required_path_params: Sequence[str] = (),
    optional_path_params: Sequence[str] = (),
    payload_kind: PayloadKind = "none",
    payload_required: bool = False,
    allow_query: bool = False,
    supports_idempotency_key: bool = False,
    supports_batch_validation: bool = False,
    deprecated: bool = False,
) -> tuple[str, ResendOperation]:
    return (
        name,
        ResendOperation(
            name=name,
            category=category,
            method=method,  # type: ignore[arg-type]
            path_hint=path_hint,
            path_builder=path_builder or static_path_builder(path_hint),
            required_path_params=tuple(required_path_params),
            optional_path_params=tuple(optional_path_params),
            payload_kind=payload_kind,
            payload_required=payload_required,
            allow_query=allow_query,
            supports_idempotency_key=supports_idempotency_key,
            supports_batch_validation=supports_batch_validation,
            deprecated=deprecated,
        ),
    )


_RESEND_OPERATION_CATALOG: "OrderedDict[str, ResendOperation]" = OrderedDict(
    (
        _operation(
            "send_email",
            "Emails",
            "POST",
            "/emails",
            payload_kind="object",
            payload_required=True,
            supports_idempotency_key=True,
        ),
        _operation("get_email", "Emails", "GET", "/emails/{email_id}", required_path_params=("email_id",)),
        _operation("cancel_email", "Emails", "POST", "/emails/{email_id}/cancel", required_path_params=("email_id",)),
        _operation(
            "update_email",
            "Emails",
            "PATCH",
            "/emails/{email_id}",
            required_path_params=("email_id",),
            payload_kind="object",
            payload_required=True,
        ),
        _operation("list_emails", "Emails", "GET", "/emails", allow_query=True),
        _operation(
            "send_batch_emails",
            "Emails",
            "POST",
            "/emails/batch",
            payload_kind="array",
            payload_required=True,
            supports_idempotency_key=True,
            supports_batch_validation=True,
        ),
        _operation(
            "get_sent_email_attachment",
            "Emails",
            "GET",
            "/emails/{email_id}/attachments/{attachment_id}",
            required_path_params=("email_id", "attachment_id"),
        ),
        _operation(
            "list_sent_email_attachments",
            "Emails",
            "GET",
            "/emails/{email_id}/attachments",
            required_path_params=("email_id",),
            allow_query=True,
        ),
        _operation(
            "get_received_email",
            "Emails",
            "GET",
            "/emails/receiving/{email_id}",
            required_path_params=("email_id",),
        ),
        _operation("list_received_emails", "Emails", "GET", "/emails/receiving", allow_query=True),
        _operation(
            "get_received_email_attachment",
            "Emails",
            "GET",
            "/emails/receiving/{email_id}/attachments/{attachment_id}",
            required_path_params=("email_id", "attachment_id"),
        ),
        _operation(
            "list_received_email_attachments",
            "Emails",
            "GET",
            "/emails/receiving/{email_id}/attachments",
            required_path_params=("email_id",),
            allow_query=True,
        ),
        _operation("create_domain", "Domains", "POST", "/domains", payload_kind="object", payload_required=True),
        _operation(
            "update_domain",
            "Domains",
            "PATCH",
            "/domains/{domain_id}",
            required_path_params=("domain_id",),
            payload_kind="object",
            payload_required=True,
        ),
        _operation("get_domain", "Domains", "GET", "/domains/{domain_id}", required_path_params=("domain_id",)),
        _operation("list_domains", "Domains", "GET", "/domains", allow_query=True),
        _operation("delete_domain", "Domains", "DELETE", "/domains/{domain_id}", required_path_params=("domain_id",)),
        _operation("verify_domain", "Domains", "POST", "/domains/{domain_id}/verify", required_path_params=("domain_id",)),
        _operation("create_api_key", "API Keys", "POST", "/api-keys", payload_kind="object", payload_required=True),
        _operation("list_api_keys", "API Keys", "GET", "/api-keys", allow_query=True),
        _operation(
            "delete_api_key",
            "API Keys",
            "DELETE",
            "/api-keys/{api_key_id}",
            required_path_params=("api_key_id",),
        ),
        _operation("create_segment", "Segments", "POST", "/segments", payload_kind="object", payload_required=True),
        _operation("list_segments", "Segments", "GET", "/segments", allow_query=True),
        _operation("get_segment", "Segments", "GET", "/segments/{segment_id}", required_path_params=("segment_id",)),
        _operation(
            "delete_segment",
            "Segments",
            "DELETE",
            "/segments/{segment_id}",
            required_path_params=("segment_id",),
        ),
        _operation(
            "create_audience",
            "Audiences",
            "POST",
            "/segments",
            payload_kind="object",
            payload_required=True,
            deprecated=True,
        ),
        _operation("list_audiences", "Audiences", "GET", "/segments", allow_query=True, deprecated=True),
        _operation(
            "get_audience",
            "Audiences",
            "GET",
            "/segments/{audience_id}",
            required_path_params=("audience_id",),
            deprecated=True,
        ),
        _operation(
            "delete_audience",
            "Audiences",
            "DELETE",
            "/segments/{audience_id}",
            required_path_params=("audience_id",),
            deprecated=True,
        ),
        _operation(
            "create_contact",
            "Contacts",
            "POST",
            "/contacts or /audiences/{audience_id}/contacts",
            path_builder=build_contact_collection_path,
            optional_path_params=("audience_id",),
            payload_kind="object",
            payload_required=True,
        ),
        _operation(
            "update_contact",
            "Contacts",
            "PATCH",
            "/contacts/{contact_identifier} or /audiences/{audience_id}/contacts/{contact_identifier}",
            path_builder=build_contact_item_path,
            required_path_params=("contact_identifier",),
            optional_path_params=("audience_id",),
            payload_kind="object",
            payload_required=True,
        ),
        _operation(
            "list_contacts",
            "Contacts",
            "GET",
            "/contacts or /audiences/{audience_id}/contacts",
            path_builder=build_contact_collection_path,
            optional_path_params=("audience_id",),
            allow_query=True,
        ),
        _operation(
            "get_contact",
            "Contacts",
            "GET",
            "/contacts/{contact_identifier} or /audiences/{audience_id}/contacts/{contact_identifier}",
            path_builder=build_contact_item_path,
            required_path_params=("contact_identifier",),
            optional_path_params=("audience_id",),
        ),
        _operation(
            "delete_contact",
            "Contacts",
            "DELETE",
            "/contacts/{contact_identifier} or /audiences/{audience_id}/contacts/{contact_identifier}",
            path_builder=build_contact_item_path,
            required_path_params=("contact_identifier",),
            optional_path_params=("audience_id",),
        ),
        _operation("get_contact_topics", "Contacts", "GET", "/contacts/{contact}/topics", required_path_params=("contact",), allow_query=True),
        _operation(
            "update_contact_topics",
            "Contacts",
            "PATCH",
            "/contacts/{contact}/topics",
            required_path_params=("contact",),
            payload_kind="object",
            payload_required=True,
        ),
        _operation(
            "create_contact_property",
            "Contact Properties",
            "POST",
            "/contact-properties",
            payload_kind="object",
            payload_required=True,
        ),
        _operation("list_contact_properties", "Contact Properties", "GET", "/contact-properties", allow_query=True),
        _operation(
            "get_contact_property",
            "Contact Properties",
            "GET",
            "/contact-properties/{contact_property_id}",
            required_path_params=("contact_property_id",),
        ),
        _operation(
            "update_contact_property",
            "Contact Properties",
            "PATCH",
            "/contact-properties/{contact_property_id}",
            required_path_params=("contact_property_id",),
            payload_kind="object",
            payload_required=True,
        ),
        _operation(
            "delete_contact_property",
            "Contact Properties",
            "DELETE",
            "/contact-properties/{contact_property_id}",
            required_path_params=("contact_property_id",),
        ),
        _operation("create_broadcast", "Broadcasts", "POST", "/broadcasts", payload_kind="object", payload_required=True),
        _operation(
            "update_broadcast",
            "Broadcasts",
            "PATCH",
            "/broadcasts/{broadcast_id}",
            required_path_params=("broadcast_id",),
            payload_kind="object",
            payload_required=True,
        ),
        _operation(
            "send_broadcast",
            "Broadcasts",
            "POST",
            "/broadcasts/{broadcast_id}/send",
            required_path_params=("broadcast_id",),
            payload_kind="object",
        ),
        _operation("list_broadcasts", "Broadcasts", "GET", "/broadcasts", allow_query=True),
        _operation("get_broadcast", "Broadcasts", "GET", "/broadcasts/{broadcast_id}", required_path_params=("broadcast_id",)),
        _operation(
            "delete_broadcast",
            "Broadcasts",
            "DELETE",
            "/broadcasts/{broadcast_id}",
            required_path_params=("broadcast_id",),
        ),
        _operation("create_template", "Templates", "POST", "/templates", payload_kind="object", payload_required=True),
        _operation("get_template", "Templates", "GET", "/templates/{template_id}", required_path_params=("template_id",)),
        _operation("list_templates", "Templates", "GET", "/templates", allow_query=True),
        _operation(
            "update_template",
            "Templates",
            "PATCH",
            "/templates/{template_id}",
            required_path_params=("template_id",),
            payload_kind="object",
            payload_required=True,
        ),
        _operation("publish_template", "Templates", "POST", "/templates/{template_id}/publish", required_path_params=("template_id",)),
        _operation("duplicate_template", "Templates", "POST", "/templates/{template_id}/duplicate", required_path_params=("template_id",)),
        _operation("delete_template", "Templates", "DELETE", "/templates/{template_id}", required_path_params=("template_id",)),
        _operation("create_topic", "Topics", "POST", "/topics", payload_kind="object", payload_required=True),
        _operation("get_topic", "Topics", "GET", "/topics/{topic_id}", required_path_params=("topic_id",)),
        _operation(
            "update_topic",
            "Topics",
            "PATCH",
            "/topics/{topic_id}",
            required_path_params=("topic_id",),
            payload_kind="object",
            payload_required=True,
        ),
        _operation("delete_topic", "Topics", "DELETE", "/topics/{topic_id}", required_path_params=("topic_id",)),
        _operation("list_topics", "Topics", "GET", "/topics", allow_query=True),
        _operation("create_webhook", "Webhooks", "POST", "/webhooks", payload_kind="object", payload_required=True),
        _operation("get_webhook", "Webhooks", "GET", "/webhooks/{webhook_id}", required_path_params=("webhook_id",)),
        _operation(
            "update_webhook",
            "Webhooks",
            "PATCH",
            "/webhooks/{webhook_id}",
            required_path_params=("webhook_id",),
            payload_kind="object",
            payload_required=True,
        ),
        _operation("list_webhooks", "Webhooks", "GET", "/webhooks", allow_query=True),
        _operation("delete_webhook", "Webhooks", "DELETE", "/webhooks/{webhook_id}", required_path_params=("webhook_id",)),
    )
)


__all__ = [
    "build_resend_operation_catalog",
    "get_resend_operation",
]
