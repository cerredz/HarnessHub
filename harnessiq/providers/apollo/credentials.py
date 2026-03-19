"""Apollo runtime credentials."""

from __future__ import annotations

from dataclasses import dataclass

from harnessiq.providers.apollo.api import DEFAULT_BASE_URL


@dataclass(frozen=True, slots=True)
class ApolloCredentials:
    """Runtime credentials for the Apollo REST API."""

    api_key: str
    base_url: str = DEFAULT_BASE_URL
    timeout_seconds: float = 60.0

    def __post_init__(self) -> None:
        if not self.api_key.strip():
            raise ValueError("Apollo api_key must not be blank.")
        if not self.base_url.strip():
            raise ValueError("Apollo base_url must not be blank.")
        if self.timeout_seconds <= 0:
            raise ValueError("Apollo timeout_seconds must be greater than zero.")

    def masked_api_key(self) -> str:
        """Return a redacted version of the API key."""
        api_key = self.api_key
        if len(api_key) <= 4:
            return "*" * len(api_key)
        return f"{api_key[:3]}{'*' * max(1, len(api_key) - 7)}{api_key[-4:]}"

    def as_redacted_dict(self) -> dict[str, object]:
        """Return a safe-to-log credential summary."""
        return {
            "api_key_masked": self.masked_api_key(),
            "base_url": self.base_url,
            "timeout_seconds": self.timeout_seconds,
        }


__all__ = ["ApolloCredentials"]
