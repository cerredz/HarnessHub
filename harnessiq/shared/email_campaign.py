"""Shared durable-memory models and helpers for the email campaign harness."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

from harnessiq.shared.agents import DEFAULT_AGENT_MAX_TOKENS, DEFAULT_AGENT_RESET_THRESHOLD
from harnessiq.shared.email import DEFAULT_EMAIL_AGENT_IDENTITY
from harnessiq.shared.harness_manifest import HarnessManifest, HarnessMemoryFileSpec, HarnessParameterSpec

SOURCE_CONFIG_FILENAME = "source_config.json"
CAMPAIGN_CONFIG_FILENAME = "campaign_config.json"
SENT_HISTORY_FILENAME = "sent_history.json"
RUNTIME_PARAMETERS_FILENAME = "runtime_parameters.json"
CUSTOM_PARAMETERS_FILENAME = "custom_parameters.json"
AGENT_IDENTITY_FILENAME = "agent_identity.txt"
ADDITIONAL_PROMPT_FILENAME = "additional_prompt.txt"

DEFAULT_EMAIL_BATCH_SIZE = 100
DEFAULT_EMAIL_PATHS = (
    "record.emails",
    "emails",
    "record.email",
    "email",
    "record.email_address",
    "email_address",
)
DEFAULT_NAME_PATHS = (
    "record.title",
    "title",
    "record.name",
    "name",
    "record.username",
    "username",
)
DEFAULT_METADATA_PATHS: dict[str, tuple[str, ...]] = {
    "instagram_url": ("record.instagram_url", "instagram_url", "record.source_url", "source_url"),
    "source_url": ("record.source_url", "source_url", "record.instagram_url", "instagram_url"),
    "title": ("record.title", "title"),
    "username": ("record.username", "username"),
    "snippet": ("record.snippet", "snippet"),
}
_TEMPLATE_PATTERN = re.compile(r"{{\s*([a-zA-Z0-9_.-]+)\s*}}")


@dataclass(frozen=True, slots=True)
class MongoRecipientSourceConfig:
    """Describe the MongoDB collection used as the email recipient source."""

    connection_uri_env_var: str = ""
    database: str = ""
    collection: str = ""
    query_filter: Mapping[str, Any] = field(default_factory=dict)
    email_paths: tuple[str, ...] = DEFAULT_EMAIL_PATHS
    name_paths: tuple[str, ...] = DEFAULT_NAME_PATHS

    def __post_init__(self) -> None:
        object.__setattr__(self, "connection_uri_env_var", self.connection_uri_env_var.strip())
        object.__setattr__(self, "database", self.database.strip())
        object.__setattr__(self, "collection", self.collection.strip())
        object.__setattr__(self, "query_filter", dict(self.query_filter))
        object.__setattr__(self, "email_paths", tuple(_clean_string_sequence(self.email_paths, default=DEFAULT_EMAIL_PATHS)))
        object.__setattr__(self, "name_paths", tuple(_clean_string_sequence(self.name_paths, default=DEFAULT_NAME_PATHS)))

    def is_configured(self) -> bool:
        return bool(self.connection_uri_env_var and self.database and self.collection)

    def validate_for_run(self) -> None:
        if not self.connection_uri_env_var:
            raise ValueError("Email source config requires a MongoDB URI env var name.")
        if not self.database:
            raise ValueError("Email source config requires a MongoDB database name.")
        if not self.collection:
            raise ValueError("Email source config requires a MongoDB collection name.")

    def as_dict(self) -> dict[str, Any]:
        return {
            "collection": self.collection,
            "connection_uri_env_var": self.connection_uri_env_var,
            "database": self.database,
            "email_paths": list(self.email_paths),
            "name_paths": list(self.name_paths),
            "query_filter": dict(self.query_filter),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any] | None) -> "MongoRecipientSourceConfig":
        payload = dict(data or {})
        return cls(
            connection_uri_env_var=str(payload.get("connection_uri_env_var", "")),
            database=str(payload.get("database", "")),
            collection=str(payload.get("collection", "")),
            query_filter=dict(payload.get("query_filter", {})) if isinstance(payload.get("query_filter", {}), Mapping) else {},
            email_paths=tuple(str(value) for value in payload.get("email_paths", DEFAULT_EMAIL_PATHS)),
            name_paths=tuple(str(value) for value in payload.get("name_paths", DEFAULT_NAME_PATHS)),
        )


@dataclass(frozen=True, slots=True)
class EmailCampaignConfig:
    """Describe the operator-authored email campaign payload."""

    from_address: str = ""
    subject: str = ""
    html_body: str | None = None
    text_body: str | None = None
    reply_to: str | None = None
    batch_validation: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "from_address", self.from_address.strip())
        object.__setattr__(self, "subject", self.subject.strip())
        object.__setattr__(self, "html_body", _normalize_optional_text(self.html_body))
        object.__setattr__(self, "text_body", _normalize_optional_text(self.text_body))
        object.__setattr__(self, "reply_to", _normalize_optional_text(self.reply_to))
        object.__setattr__(self, "batch_validation", _normalize_optional_text(self.batch_validation))

    def is_configured(self) -> bool:
        return bool(self.from_address and self.subject and (self.html_body or self.text_body))

    def validate_for_run(self) -> None:
        if not self.from_address:
            raise ValueError("Email campaign config requires a non-empty from_address.")
        if not self.subject:
            raise ValueError("Email campaign config requires a non-empty subject.")
        if not (self.html_body or self.text_body):
            raise ValueError("Email campaign config requires either html_body or text_body.")

    def as_dict(self) -> dict[str, Any]:
        return {
            "batch_validation": self.batch_validation,
            "from_address": self.from_address,
            "html_body": self.html_body,
            "reply_to": self.reply_to,
            "subject": self.subject,
            "text_body": self.text_body,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any] | None) -> "EmailCampaignConfig":
        payload = dict(data or {})
        return cls(
            batch_validation=str(payload["batch_validation"]) if payload.get("batch_validation") else None,
            from_address=str(payload.get("from_address", "")),
            html_body=str(payload["html_body"]) if payload.get("html_body") is not None else None,
            reply_to=str(payload["reply_to"]) if payload.get("reply_to") else None,
            subject=str(payload.get("subject", "")),
            text_body=str(payload["text_body"]) if payload.get("text_body") is not None else None,
        )


@dataclass(frozen=True, slots=True)
class EmailCampaignRecipient:
    """One deduplicated outbound email recipient resolved from source records."""

    email_address: str
    name: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "email_address", self.email_address.strip().lower())
        object.__setattr__(self, "name", _normalize_optional_text(self.name))
        object.__setattr__(self, "metadata", dict(self.metadata))
        if not self.email_address:
            raise ValueError("EmailCampaignRecipient.email_address must not be blank.")

    def template_context(self) -> dict[str, str]:
        payload = {
            "email": self.email_address,
            "name": self.name or "",
        }
        for key, value in self.metadata.items():
            if value is None:
                continue
            payload[str(key)] = str(value)
        return payload

    def as_dict(self) -> dict[str, Any]:
        return {
            "email_address": self.email_address,
            "metadata": dict(self.metadata),
            "name": self.name,
        }


@dataclass(frozen=True, slots=True)
class EmailSendRecord:
    """Persist one successfully sent email recipient for future dedupe."""

    email_address: str
    sent_at: str
    subject: str
    resend_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "email_address", self.email_address.strip().lower())
        object.__setattr__(self, "sent_at", self.sent_at.strip())
        object.__setattr__(self, "subject", self.subject.strip())
        object.__setattr__(self, "resend_id", _normalize_optional_text(self.resend_id))
        if not self.email_address:
            raise ValueError("EmailSendRecord.email_address must not be blank.")

    def as_dict(self) -> dict[str, Any]:
        return {
            "email_address": self.email_address,
            "resend_id": self.resend_id,
            "sent_at": self.sent_at,
            "subject": self.subject,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "EmailSendRecord":
        return cls(
            email_address=str(data["email_address"]),
            resend_id=str(data["resend_id"]) if data.get("resend_id") else None,
            sent_at=str(data["sent_at"]),
            subject=str(data.get("subject", "")),
        )


@dataclass(slots=True)
class EmailCampaignMemoryStore:
    """Manage the durable memory files for the email campaign harness."""

    memory_path: Path

    def __post_init__(self) -> None:
        self.memory_path = Path(self.memory_path)

    @property
    def source_config_path(self) -> Path:
        return self.memory_path / SOURCE_CONFIG_FILENAME

    @property
    def campaign_config_path(self) -> Path:
        return self.memory_path / CAMPAIGN_CONFIG_FILENAME

    @property
    def sent_history_path(self) -> Path:
        return self.memory_path / SENT_HISTORY_FILENAME

    @property
    def runtime_parameters_path(self) -> Path:
        return self.memory_path / RUNTIME_PARAMETERS_FILENAME

    @property
    def custom_parameters_path(self) -> Path:
        return self.memory_path / CUSTOM_PARAMETERS_FILENAME

    @property
    def agent_identity_path(self) -> Path:
        return self.memory_path / AGENT_IDENTITY_FILENAME

    @property
    def additional_prompt_path(self) -> Path:
        return self.memory_path / ADDITIONAL_PROMPT_FILENAME

    def prepare(self) -> None:
        self.memory_path.mkdir(parents=True, exist_ok=True)
        _ensure_json_file(self.source_config_path, {})
        _ensure_json_file(self.campaign_config_path, {})
        _ensure_json_file(self.sent_history_path, [])
        _ensure_json_file(self.runtime_parameters_path, {})
        _ensure_json_file(self.custom_parameters_path, {})
        _ensure_text_file(self.agent_identity_path, DEFAULT_EMAIL_AGENT_IDENTITY)
        _ensure_text_file(self.additional_prompt_path, "")

    def read_source_config(self) -> MongoRecipientSourceConfig:
        return MongoRecipientSourceConfig.from_dict(_read_json_file(self.source_config_path, expected_type=dict))

    def write_source_config(self, config: MongoRecipientSourceConfig) -> None:
        self.prepare()
        _write_json(self.source_config_path, config.as_dict())

    def read_campaign_config(self) -> EmailCampaignConfig:
        return EmailCampaignConfig.from_dict(_read_json_file(self.campaign_config_path, expected_type=dict))

    def write_campaign_config(self, config: EmailCampaignConfig) -> None:
        self.prepare()
        _write_json(self.campaign_config_path, config.as_dict())

    def read_sent_history(self) -> list[EmailSendRecord]:
        payload = _read_json_file(self.sent_history_path, expected_type=list)
        return [EmailSendRecord.from_dict(dict(item)) for item in payload if isinstance(item, Mapping)]

    def append_sent_records(self, records: Sequence[EmailSendRecord]) -> None:
        if not records:
            return
        payload = [record.as_dict() for record in self.read_sent_history()]
        payload.extend(record.as_dict() for record in records)
        _write_json(self.sent_history_path, payload)

    def sent_email_addresses(self) -> set[str]:
        return {record.email_address for record in self.read_sent_history()}

    def read_runtime_parameters(self) -> dict[str, Any]:
        return _read_json_file(self.runtime_parameters_path, expected_type=dict)

    def write_runtime_parameters(self, parameters: Mapping[str, Any]) -> None:
        self.prepare()
        _write_json(self.runtime_parameters_path, dict(parameters))

    def read_custom_parameters(self) -> dict[str, Any]:
        return _read_json_file(self.custom_parameters_path, expected_type=dict)

    def write_custom_parameters(self, parameters: Mapping[str, Any]) -> None:
        self.prepare()
        _write_json(self.custom_parameters_path, dict(parameters))

    def read_agent_identity(self) -> str:
        self.prepare()
        return self.agent_identity_path.read_text(encoding="utf-8").strip()

    def write_agent_identity(self, text: str) -> None:
        self.prepare()
        _write_text(self.agent_identity_path, text)

    def read_additional_prompt(self) -> str:
        self.prepare()
        return self.additional_prompt_path.read_text(encoding="utf-8").strip()

    def write_additional_prompt(self, text: str) -> None:
        self.prepare()
        _write_text(self.additional_prompt_path, text)


def normalize_email_runtime_parameters(parameters: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and normalize explicit email runtime parameters."""
    payload = EMAIL_HARNESS_MANIFEST.coerce_runtime_parameters(parameters)
    batch_size = int(payload.get("batch_size", DEFAULT_EMAIL_BATCH_SIZE))
    if batch_size <= 0:
        raise ValueError("Email batch_size must be positive.")
    recipient_limit = payload.get("recipient_limit")
    if recipient_limit is not None and int(recipient_limit) <= 0:
        raise ValueError("Email recipient_limit must be positive when provided.")
    return payload


def resolve_email_runtime_parameters(parameters: Mapping[str, Any]) -> dict[str, Any]:
    """Merge email runtime defaults with validated explicit values."""
    payload = EMAIL_HARNESS_MANIFEST.default_runtime_parameters()
    payload.update(normalize_email_runtime_parameters(parameters))
    return payload


def normalize_email_custom_parameters(parameters: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and normalize explicit email custom parameters."""
    return EMAIL_HARNESS_MANIFEST.coerce_custom_parameters(parameters)


def load_email_campaign_recipients(
    source_config: MongoRecipientSourceConfig,
    *,
    limit: int | None = None,
    sent_emails: set[str] | None = None,
    mongo_client=None,
) -> list[EmailCampaignRecipient]:
    """Load, normalize, dedupe, and filter recipients from the configured Mongo source."""
    source_config.validate_for_run()
    documents = _load_mongo_documents(source_config, limit=limit, mongo_client=mongo_client)
    seen: set[str] = set()
    blocked = {value.lower() for value in (sent_emails or set())}
    recipients: list[EmailCampaignRecipient] = []
    for document in documents:
        for recipient in _extract_recipients_from_document(document, source_config):
            normalized = recipient.email_address.lower()
            if normalized in seen or normalized in blocked:
                continue
            seen.add(normalized)
            recipients.append(recipient)
            if limit is not None and len(recipients) >= limit:
                return recipients
    return recipients


def render_email_campaign_template(template: str | None, recipient: EmailCampaignRecipient) -> str | None:
    """Render one lightweight `{{field}}` template against a recipient context."""
    if template is None:
        return None
    context = recipient.template_context()

    def _replace(match: re.Match[str]) -> str:
        return context.get(match.group(1), "")

    return _TEMPLATE_PATTERN.sub(_replace, template)


def build_resend_batch_payload(
    campaign_config: EmailCampaignConfig,
    recipients: Sequence[EmailCampaignRecipient],
) -> list[dict[str, Any]]:
    """Build the concrete Resend batch payload for one recipient batch."""
    campaign_config.validate_for_run()
    payload: list[dict[str, Any]] = []
    for recipient in recipients:
        record: dict[str, Any] = {
            "from": campaign_config.from_address,
            "subject": render_email_campaign_template(campaign_config.subject, recipient) or campaign_config.subject,
            "to": [recipient.email_address],
        }
        html_body = render_email_campaign_template(campaign_config.html_body, recipient)
        text_body = render_email_campaign_template(campaign_config.text_body, recipient)
        if html_body:
            record["html"] = html_body
        if text_body:
            record["text"] = text_body
        if campaign_config.reply_to:
            record["reply_to"] = campaign_config.reply_to
        payload.append(record)
    return payload


def summarize_email_campaign_store(
    store: EmailCampaignMemoryStore,
    *,
    runtime_parameters: Mapping[str, Any] | None = None,
    mongo_client=None,
) -> dict[str, Any]:
    """Return a JSON-safe state summary for builders and CLI adapters."""
    store.prepare()
    source_config = store.read_source_config()
    campaign_config = store.read_campaign_config()
    raw_runtime = dict(runtime_parameters) if runtime_parameters is not None else store.read_runtime_parameters()
    resolved_runtime = resolve_email_runtime_parameters(raw_runtime)
    custom_parameters = store.read_custom_parameters()
    payload: dict[str, Any] = {
        "additional_prompt": store.read_additional_prompt(),
        "agent_identity": store.read_agent_identity(),
        "campaign_config": campaign_config.as_dict(),
        "custom_parameters": custom_parameters,
        "memory_path": str(store.memory_path.resolve()),
        "ready": source_config.is_configured() and campaign_config.is_configured(),
        "runtime_parameters": resolved_runtime,
        "sent_count": len(store.read_sent_history()),
        "source_config": source_config.as_dict(),
    }
    try:
        selection_limit = int(resolved_runtime["batch_size"])
        if resolved_runtime.get("recipient_limit") is not None:
            selection_limit = min(selection_limit, int(resolved_runtime["recipient_limit"]))
        recipients = load_email_campaign_recipients(
            source_config,
            limit=selection_limit,
            sent_emails=store.sent_email_addresses(),
            mongo_client=mongo_client,
        )
        payload["recipient_count"] = len(recipients)
        payload["recipient_preview"] = [recipient.as_dict() for recipient in recipients[:5]]
    except Exception as exc:
        payload["recipient_count"] = 0
        payload["recipient_preview"] = []
        payload["recipient_preview_error"] = str(exc)
    return payload


EMAIL_HARNESS_MANIFEST = HarnessManifest(
    manifest_id="email",
    agent_name="email_campaign_agent",
    display_name="Email Campaign",
    module_path="harnessiq.agents.email",
    class_name="EmailCampaignAgent",
    cli_command="email",
    cli_adapter_path="harnessiq.cli.adapters.email:EmailHarnessCliAdapter",
    default_memory_root="memory/email",
    runtime_parameters=(
        HarnessParameterSpec("max_tokens", "integer", "Maximum model context budget for the harness.", default=DEFAULT_AGENT_MAX_TOKENS),
        HarnessParameterSpec("reset_threshold", "number", "Fraction of max_tokens that triggers a reset.", default=DEFAULT_AGENT_RESET_THRESHOLD),
        HarnessParameterSpec("batch_size", "integer", "Maximum deduplicated recipients selected for one batch send run.", default=DEFAULT_EMAIL_BATCH_SIZE),
        HarnessParameterSpec("recipient_limit", "integer", "Optional upper bound for recipients considered from the source.", nullable=True),
    ),
    custom_parameters_open_ended=True,
    memory_files=(
        HarnessMemoryFileSpec("source_config", SOURCE_CONFIG_FILENAME, "MongoDB-backed recipient source configuration.", format="json"),
        HarnessMemoryFileSpec("campaign_config", CAMPAIGN_CONFIG_FILENAME, "Operator-authored email campaign content and delivery settings.", format="json"),
        HarnessMemoryFileSpec("sent_history", SENT_HISTORY_FILENAME, "Append-only record of recipients already sent by this harness.", format="json"),
        HarnessMemoryFileSpec("runtime_parameters", RUNTIME_PARAMETERS_FILENAME, "Persisted typed runtime overrides.", format="json"),
        HarnessMemoryFileSpec("custom_parameters", CUSTOM_PARAMETERS_FILENAME, "Open-ended custom parameter payload.", format="json"),
        HarnessMemoryFileSpec("agent_identity", AGENT_IDENTITY_FILENAME, "Override for the email system identity.", format="text"),
        HarnessMemoryFileSpec("additional_prompt", ADDITIONAL_PROMPT_FILENAME, "Additional free-form prompt data.", format="text"),
    ),
    provider_families=("resend",),
    output_schema={
        "type": "object",
        "properties": {
            "campaign": {"type": "object", "additionalProperties": True},
            "delivery_records": {"type": "array", "items": {"type": "object", "additionalProperties": True}},
            "recipient_batch": {"type": "array", "items": {"type": "object", "additionalProperties": True}},
        },
        "additionalProperties": False,
    },
)


def _load_mongo_documents(
    source_config: MongoRecipientSourceConfig,
    *,
    limit: int | None,
    mongo_client=None,
) -> list[dict[str, Any]]:
    client = mongo_client
    if client is None:
        connection_uri = os.environ.get(source_config.connection_uri_env_var, "").strip()
        if not connection_uri:
            raise ValueError(
                f"MongoDB URI env var '{source_config.connection_uri_env_var}' is not set for the email source."
            )
        from harnessiq.providers.output_sinks import MongoDBClient

        client = MongoDBClient(
            connection_uri=connection_uri,
            database=source_config.database,
            collection=source_config.collection,
        )
    return client.find_documents(filter=source_config.query_filter, limit=limit)


def _extract_recipients_from_document(
    document: Mapping[str, Any],
    source_config: MongoRecipientSourceConfig,
) -> list[EmailCampaignRecipient]:
    emails = _extract_email_values(document, source_config.email_paths)
    if not emails:
        return []
    name = _first_string_value(document, source_config.name_paths)
    metadata = _extract_metadata(document)
    return [
        EmailCampaignRecipient(
            email_address=email,
            name=name,
            metadata=metadata,
        )
        for email in emails
    ]


def _extract_email_values(document: Mapping[str, Any], paths: Sequence[str]) -> list[str]:
    values: list[str] = []
    for path in paths:
        candidate = _resolve_path(document, path)
        values.extend(_coerce_email_candidates(candidate))
    deduped: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = value.strip().lower()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(normalized)
    return deduped


def _extract_metadata(document: Mapping[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for key, paths in DEFAULT_METADATA_PATHS.items():
        value = _first_present_value(document, paths)
        if value is None:
            continue
        payload[key] = value
    if "instagram_url" not in payload and "source_url" in payload:
        payload["instagram_url"] = payload["source_url"]
    return payload


def _first_string_value(document: Mapping[str, Any], paths: Sequence[str]) -> str | None:
    value = _first_present_value(document, paths)
    if value is None:
        return None
    return str(value).strip() or None


def _first_present_value(document: Mapping[str, Any], paths: Sequence[str]) -> Any:
    for path in paths:
        value = _resolve_path(document, path)
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        return value
    return None


def _resolve_path(payload: Any, path: str) -> Any:
    current = payload
    for segment in path.split("."):
        if not isinstance(current, Mapping):
            return None
        if segment not in current:
            return None
        current = current[segment]
    return current


def _coerce_email_candidates(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        cleaned = value.strip()
        return [cleaned] if cleaned else []
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        payload: list[str] = []
        for item in value:
            payload.extend(_coerce_email_candidates(item))
        return payload
    return []


def _clean_string_sequence(
    values: Sequence[str] | None,
    *,
    default: Sequence[str],
) -> list[str]:
    cleaned = [str(value).strip() for value in (values or ()) if str(value).strip()]
    return cleaned or [str(value) for value in default]


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    rendered = text if not text or text.endswith("\n") else f"{text}\n"
    path.write_text(rendered, encoding="utf-8")


def _ensure_json_file(path: Path, default_payload: Any) -> None:
    if not path.exists():
        _write_json(path, default_payload)


def _ensure_text_file(path: Path, default_content: str) -> None:
    if not path.exists():
        _write_text(path, default_content)


def _read_json_file(path: Path, *, expected_type: type) -> Any:
    if not path.exists():
        return expected_type()
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return expected_type()
    payload = json.loads(raw)
    if not isinstance(payload, expected_type):
        raise ValueError(f"Expected JSON {expected_type.__name__} in '{path.name}'.")
    return payload


__all__ = [
    "ADDITIONAL_PROMPT_FILENAME",
    "AGENT_IDENTITY_FILENAME",
    "CAMPAIGN_CONFIG_FILENAME",
    "CUSTOM_PARAMETERS_FILENAME",
    "DEFAULT_EMAIL_BATCH_SIZE",
    "EMAIL_HARNESS_MANIFEST",
    "EmailCampaignConfig",
    "EmailCampaignMemoryStore",
    "EmailCampaignRecipient",
    "EmailSendRecord",
    "MongoRecipientSourceConfig",
    "RUNTIME_PARAMETERS_FILENAME",
    "SENT_HISTORY_FILENAME",
    "SOURCE_CONFIG_FILENAME",
    "build_resend_batch_payload",
    "load_email_campaign_recipients",
    "normalize_email_custom_parameters",
    "normalize_email_runtime_parameters",
    "render_email_campaign_template",
    "resolve_email_runtime_parameters",
    "summarize_email_campaign_store",
]
