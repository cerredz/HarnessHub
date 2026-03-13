"""Resend-backed tooling primitives for outbound email workflows."""

from __future__ import annotations

from collections import OrderedDict
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Callable, Literal, Mapping, Sequence
from urllib.parse import quote, urlencode

from src.providers.http import RequestExecutor, request_json
from src.shared.tools import RegisteredTool, ToolArguments, ToolDefinition

DEFAULT_RESEND_BASE_URL = "https://api.resend.com"
DEFAULT_RESEND_USER_AGENT = "HarnessHub/resend-tool"
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


@dataclass(frozen=True, slots=True)
class ResendClient:
    """Small Resend HTTP client suitable for tool execution and tests."""

    credentials: ResendCredentials
    request_executor: RequestExecutor = request_json

    def prepare_request(
        self,
        operation_name: str,
        *,
        path_params: Mapping[str, object] | None = None,
        query: Mapping[str, object] | None = None,
        payload: Any | None = None,
        idempotency_key: str | None = None,
        batch_validation: str | None = None,
    ) -> ResendPreparedRequest:
        """Validate the operation inputs and build an executable request."""
        operation = get_resend_operation(operation_name)
        normalized_path_params = _normalize_path_params(path_params)
        _validate_path_params(operation, normalized_path_params)
        normalized_query = _normalize_mapping(query, field_name="query") if query is not None else None
        _validate_payload(operation, payload)
        _validate_headers(
            operation,
            idempotency_key=idempotency_key,
            batch_validation=batch_validation,
        )

        path = operation.path_builder(normalized_path_params)
        url = _build_url(self.credentials.base_url, path, query=normalized_query)
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.credentials.api_key}",
            "User-Agent": self.credentials.user_agent,
        }
        if idempotency_key is not None:
            headers["Idempotency-Key"] = idempotency_key
        if batch_validation is not None:
            headers["x-batch-validation"] = batch_validation

        return ResendPreparedRequest(
            operation=operation,
            method=operation.method,
            path=path,
            url=url,
            headers=headers,
            json_body=_copy_payload(payload),
        )

    def execute_operation(
        self,
        operation_name: str,
        *,
        path_params: Mapping[str, object] | None = None,
        query: Mapping[str, object] | None = None,
        payload: Any | None = None,
        idempotency_key: str | None = None,
        batch_validation: str | None = None,
    ) -> Any:
        """Execute one validated Resend operation and return the decoded response."""
        prepared = self.prepare_request(
            operation_name,
            path_params=path_params,
            query=query,
            payload=payload,
            idempotency_key=idempotency_key,
            batch_validation=batch_validation,
        )
        return self.request_executor(
            prepared.method,
            prepared.url,
            headers=prepared.headers,
            json_body=prepared.json_body,
            timeout_seconds=self.credentials.timeout_seconds,
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


def build_resend_request_tool_definition(
    *,
    allowed_operations: Sequence[str] | None = None,
) -> ToolDefinition:
    """Return the canonical tool definition for the Resend request surface."""
    operations = _select_operations(allowed_operations)
    operation_names = [operation.name for operation in operations]
    return ToolDefinition(
        key=RESEND_REQUEST,
        name="resend_request",
        description=_build_resend_tool_description(operations),
        input_schema={
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": operation_names,
                    "description": "Supported Resend operation name.",
                },
                "path_params": {
                    "type": "object",
                    "description": "Operation-specific path parameters such as ids used in the URL.",
                    "additionalProperties": True,
                },
                "query": {
                    "type": "object",
                    "description": "Optional query parameters for list/filter operations.",
                    "additionalProperties": True,
                },
                "payload": {
                    "description": "Optional operation-specific JSON body. Some operations require an object or array.",
                    "anyOf": [
                        {"type": "object"},
                        {"type": "array"},
                    ],
                },
                "idempotency_key": {
                    "type": "string",
                    "description": "Optional Resend Idempotency-Key header for supported send operations.",
                },
                "batch_validation": {
                    "type": "string",
                    "enum": sorted(_BATCH_VALIDATION_MODES),
                    "description": "Optional x-batch-validation mode for batch send operations.",
                },
            },
            "required": ["operation"],
            "additionalProperties": False,
        },
    )


def create_resend_tools(
    *,
    credentials: ResendCredentials | None = None,
    client: ResendClient | None = None,
    allowed_operations: Sequence[str] | None = None,
) -> tuple[RegisteredTool, ...]:
    """Return the MCP-style Resend request tool backed by the provided client."""
    resend_client = _coerce_client(credentials=credentials, client=client)
    selected_operations = _select_operations(allowed_operations)
    allowed_names = frozenset(operation.name for operation in selected_operations)
    definition = build_resend_request_tool_definition(
        allowed_operations=tuple(operation.name for operation in selected_operations)
    )

    def handler(arguments: ToolArguments) -> dict[str, Any]:
        operation_name = _require_operation_name(arguments, allowed_names)
        prepared = resend_client.prepare_request(
            operation_name,
            path_params=_optional_mapping(arguments, "path_params"),
            query=_optional_mapping(arguments, "query"),
            payload=arguments.get("payload"),
            idempotency_key=_optional_string(arguments, "idempotency_key"),
            batch_validation=_optional_string(arguments, "batch_validation"),
        )
        response = resend_client.request_executor(
            prepared.method,
            prepared.url,
            headers=prepared.headers,
            json_body=prepared.json_body,
            timeout_seconds=resend_client.credentials.timeout_seconds,
        )
        return {
            "operation": prepared.operation.name,
            "method": prepared.method,
            "path": prepared.path,
            "response": response,
        }

    return (RegisteredTool(definition=definition, handler=handler),)


def _coerce_client(
    *,
    credentials: ResendCredentials | None,
    client: ResendClient | None,
) -> ResendClient:
    if client is not None:
        return client
    if credentials is None:
        raise ValueError("Either Resend credentials or a Resend client must be provided.")
    return ResendClient(credentials=credentials)


def _build_resend_tool_description(operations: Sequence[ResendOperation]) -> str:
    grouped: OrderedDict[str, list[str]] = OrderedDict()
    for operation in operations:
        grouped.setdefault(operation.category, []).append(operation.summary())

    lines = ["Execute authenticated Resend API operations through a single MCP-style request tool."]
    for category, summaries in grouped.items():
        lines.append(f"{category}: {', '.join(summaries)}")
    lines.append(
        "Use `path_params` for URL ids, `query` for list pagination/filtering, `payload` for JSON bodies, "
        "`idempotency_key` for supported send operations, and `batch_validation` for batch sends."
    )
    return "\n".join(lines)


def _select_operations(allowed_operations: Sequence[str] | None) -> tuple[ResendOperation, ...]:
    if allowed_operations is None:
        return build_resend_operation_catalog()
    selected: list[ResendOperation] = []
    seen: set[str] = set()
    for operation_name in allowed_operations:
        operation = get_resend_operation(operation_name)
        if operation.name in seen:
            continue
        seen.add(operation.name)
        selected.append(operation)
    return tuple(selected)


def _require_operation_name(arguments: Mapping[str, object], allowed_names: set[str] | frozenset[str]) -> str:
    value = arguments["operation"]
    if not isinstance(value, str):
        raise ValueError("The 'operation' argument must be a string.")
    if value not in allowed_names:
        allowed = ", ".join(sorted(allowed_names))
        raise ValueError(f"Unsupported Resend operation '{value}' for this tool configuration. Allowed: {allowed}.")
    return value


def _optional_mapping(arguments: Mapping[str, object], key: str) -> Mapping[str, object] | None:
    if key not in arguments or arguments[key] is None:
        return None
    value = arguments[key]
    if not isinstance(value, Mapping):
        raise ValueError(f"The '{key}' argument must be an object when provided.")
    return value


def _optional_string(arguments: Mapping[str, object], key: str) -> str | None:
    if key not in arguments or arguments[key] is None:
        return None
    value = arguments[key]
    if not isinstance(value, str):
        raise ValueError(f"The '{key}' argument must be a string when provided.")
    return value


def _normalize_path_params(path_params: Mapping[str, object] | None) -> dict[str, str]:
    if path_params is None:
        return {}
    normalized = _normalize_mapping(path_params, field_name="path_params")
    return {key: str(value) for key, value in normalized.items()}


def _normalize_mapping(mapping: Mapping[str, object], *, field_name: str) -> dict[str, object]:
    normalized: dict[str, object] = {}
    for key, value in mapping.items():
        if not isinstance(key, str):
            raise ValueError(f"All keys in '{field_name}' must be strings.")
        normalized[key] = deepcopy(value)
    return normalized


def _validate_path_params(operation: ResendOperation, path_params: Mapping[str, str]) -> None:
    allowed = set(operation.required_path_params) | set(operation.optional_path_params)
    unexpected = sorted(set(path_params) - allowed)
    if unexpected:
        raise ValueError(
            f"Operation '{operation.name}' received unexpected path parameters: {', '.join(unexpected)}."
        )

    missing = [key for key in operation.required_path_params if not path_params.get(key)]
    if missing:
        raise ValueError(f"Operation '{operation.name}' requires path parameters: {', '.join(missing)}.")


def _validate_payload(operation: ResendOperation, payload: Any | None) -> None:
    if operation.payload_kind == "none":
        if payload is not None:
            raise ValueError(f"Operation '{operation.name}' does not accept a payload.")
        return

    if payload is None:
        if operation.payload_required:
            raise ValueError(f"Operation '{operation.name}' requires a payload.")
        return

    if operation.payload_kind == "object" and not isinstance(payload, Mapping):
        raise ValueError(f"Operation '{operation.name}' requires an object payload.")
    if operation.payload_kind == "array":
        if not isinstance(payload, list):
            raise ValueError(f"Operation '{operation.name}' requires an array payload.")
        for index, item in enumerate(payload):
            if not isinstance(item, Mapping):
                raise ValueError(f"Operation '{operation.name}' requires payload item {index} to be an object.")


def _validate_headers(
    operation: ResendOperation,
    *,
    idempotency_key: str | None,
    batch_validation: str | None,
) -> None:
    if idempotency_key is not None and not operation.supports_idempotency_key:
        raise ValueError(f"Operation '{operation.name}' does not support idempotency_key.")
    if batch_validation is not None:
        if not operation.supports_batch_validation:
            raise ValueError(f"Operation '{operation.name}' does not support batch_validation.")
        if batch_validation not in _BATCH_VALIDATION_MODES:
            modes = ", ".join(sorted(_BATCH_VALIDATION_MODES))
            raise ValueError(f"batch_validation must be one of: {modes}.")


def _copy_payload(payload: Any | None) -> Any | None:
    if payload is None:
        return None
    return deepcopy(payload)


def _build_url(base_url: str, path: str, *, query: Mapping[str, object] | None = None) -> str:
    base = base_url.rstrip("/")
    if not query:
        return f"{base}{path}"

    encoded_query = urlencode(list(_flatten_query_items(query)), doseq=True)
    return f"{base}{path}?{encoded_query}"


def _flatten_query_items(query: Mapping[str, object]) -> list[tuple[str, object]]:
    items: list[tuple[str, object]] = []
    for key, value in query.items():
        if isinstance(value, (list, tuple)):
            for item in value:
                items.append((key, item))
            continue
        items.append((key, value))
    return items


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
    "ResendClient",
    "ResendCredentials",
    "ResendOperation",
    "ResendPreparedRequest",
    "build_resend_operation_catalog",
    "build_resend_request_tool_definition",
    "create_resend_tools",
    "get_resend_operation",
]
