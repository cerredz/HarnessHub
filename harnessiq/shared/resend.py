"""Resend-backed tooling primitives for outbound email workflows."""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Callable, Literal, Mapping, Sequence
from urllib.parse import quote

DEFAULT_RESEND_BASE_URL = "https://api.resend.com"
DEFAULT_RESEND_USER_AGENT = "Harnessiq/resend-tool"
RESEND_REQUEST = "resend.request"
_BATCH_VALIDATION_MODES = frozenset({"strict", "permissive"})

PayloadKind = Literal["none", "object", "array"]
PathBuilder = Callable[[Mapping[str, str]], str]


@dataclass(frozen=True, slots=True)
class ResendCredentials:
    """Runtime credentials and transport configuration for the Resend API."""

    api_key: str
    base_url: str = DEFAULT_RESEND_BASE_URL
    user_agent: str = DEFAULT_RESEND_USER_AGENT
    timeout_seconds: float = 60.0

    def __post_init__(self) -> None:
        if not self.api_key.strip():
            raise ValueError("Resend api_key must not be blank.")
        if not self.base_url.strip():
            raise ValueError("Resend base_url must not be blank.")
        if not self.user_agent.strip():
            raise ValueError("Resend user_agent must not be blank.")
        if self.timeout_seconds <= 0:
            raise ValueError("Resend timeout_seconds must be greater than zero.")

    def masked_api_key(self) -> str:
        """Return a redacted version of the configured API key."""
        if len(self.api_key) <= 4:
            return "*" * len(self.api_key)
        suffix = self.api_key[-4:]
        return f"{self.api_key[:3]}{'*' * max(1, len(self.api_key) - 7)}{suffix}"

    def as_redacted_dict(self) -> dict[str, object]:
        """Return a safe-to-render credential summary for prompts/logs."""
        return {
            "base_url": self.base_url,
            "user_agent": self.user_agent,
            "api_key_masked": self.masked_api_key(),
            "timeout_seconds": self.timeout_seconds,
        }


@dataclass(frozen=True, slots=True)
class ResendOperation:
    """Declarative metadata for one supported Resend API operation."""

    name: str
    category: str
    method: Literal["GET", "POST", "PATCH", "DELETE"]
    path_hint: str
    path_builder: PathBuilder
    required_path_params: tuple[str, ...] = ()
    optional_path_params: tuple[str, ...] = ()
    payload_kind: PayloadKind = "none"
    payload_required: bool = False
    allow_query: bool = False
    supports_idempotency_key: bool = False
    supports_batch_validation: bool = False
    deprecated: bool = False

    def summary(self) -> str:
        suffix = " [deprecated alias]" if self.deprecated else ""
        return f"{self.name} ({self.method} {self.path_hint}){suffix}"


@dataclass(frozen=True, slots=True)
class ResendPreparedRequest:
    """A validated Resend request ready for execution."""

    operation: ResendOperation
    method: str
    path: str
    url: str
    headers: dict[str, str]
    json_body: Any | None

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

def _static_path_builder(path_hint: str) -> PathBuilder:
    parameter_names = tuple(_extract_path_parameters(path_hint))

    def build(path_params: Mapping[str, str]) -> str:
        rendered = path_hint
        for parameter_name in parameter_names:
            value = path_params[parameter_name]
            rendered = rendered.replace(f"{{{parameter_name}}}", quote(value, safe=""))
        return rendered

    return build


def _extract_path_parameters(path_hint: str) -> list[str]:
    parameters: list[str] = []
    current: list[str] = []
    inside = False
    for character in path_hint:
        if character == "{":
            inside = True
            current = []
            continue
        if character == "}":
            inside = False
            parameters.append("".join(current))
            current = []
            continue
        if inside:
            current.append(character)
    return parameters


def _build_contact_collection_path(path_params: Mapping[str, str]) -> str:
    audience_id = path_params.get("audience_id")
    if audience_id:
        return f"/audiences/{quote(audience_id, safe='')}/contacts"
    return "/contacts"


def _build_contact_item_path(path_params: Mapping[str, str]) -> str:
    contact_identifier = path_params["contact_identifier"]
    audience_id = path_params.get("audience_id")
    contact = quote(contact_identifier, safe="")
    if audience_id:
        return f"/audiences/{quote(audience_id, safe='')}/contacts/{contact}"
    return f"/contacts/{contact}"


def _operation(
    name: str,
    category: str,
    method: Literal["GET", "POST", "PATCH", "DELETE"],
    path_hint: str,
    *,
    path_builder: PathBuilder | None = None,
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
            method=method,
            path_hint=path_hint,
            path_builder=path_builder or _static_path_builder(path_hint),
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
            path_builder=_build_contact_collection_path,
            optional_path_params=("audience_id",),
            payload_kind="object",
            payload_required=True,
        ),
        _operation(
            "update_contact",
            "Contacts",
            "PATCH",
            "/contacts/{contact_identifier} or /audiences/{audience_id}/contacts/{contact_identifier}",
            path_builder=_build_contact_item_path,
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
            path_builder=_build_contact_collection_path,
            optional_path_params=("audience_id",),
            allow_query=True,
        ),
        _operation(
            "get_contact",
            "Contacts",
            "GET",
            "/contacts/{contact_identifier} or /audiences/{audience_id}/contacts/{contact_identifier}",
            path_builder=_build_contact_item_path,
            required_path_params=("contact_identifier",),
            optional_path_params=("audience_id",),
        ),
        _operation(
            "delete_contact",
            "Contacts",
            "DELETE",
            "/contacts/{contact_identifier} or /audiences/{audience_id}/contacts/{contact_identifier}",
            path_builder=_build_contact_item_path,
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
    "DEFAULT_RESEND_BASE_URL",
    "DEFAULT_RESEND_USER_AGENT",
    "RESEND_REQUEST",
    "ResendCredentials",
    "ResendOperation",
    "ResendPreparedRequest",
    "build_resend_operation_catalog",
    "get_resend_operation",
    "_BATCH_VALIDATION_MODES",
]
