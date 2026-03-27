"""Shared Resend models and stable constants."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Literal, Mapping

from harnessiq.shared.validated import HttpUrl, NonEmptyString, parse_positive_number

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
        object.__setattr__(self, "api_key", NonEmptyString(self.api_key, field_name="Resend api_key"))
        object.__setattr__(self, "base_url", HttpUrl(self.base_url, field_name="Resend base_url"))
        object.__setattr__(self, "user_agent", NonEmptyString(self.user_agent, field_name="Resend user_agent"))
        object.__setattr__(
            self,
            "timeout_seconds",
            parse_positive_number(self.timeout_seconds, field_name="Resend timeout_seconds"),
        )

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


__all__ = [
    "DEFAULT_RESEND_BASE_URL",
    "DEFAULT_RESEND_USER_AGENT",
    "RESEND_REQUEST",
    "ResendCredentials",
    "ResendOperation",
    "ResendPreparedRequest",
    "_BATCH_VALIDATION_MODES",
]
