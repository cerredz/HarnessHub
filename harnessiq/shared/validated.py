"""Shared validated scalar value objects and parse helpers."""

from __future__ import annotations

import re
from urllib.parse import urlparse

_ENV_VAR_NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_PROVIDER_FAMILY_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")


class NonEmptyString(str):
    """A trimmed string that cannot be blank."""

    def __new__(cls, value: object, *, field_name: str = "value") -> "NonEmptyString":
        if not isinstance(value, str):
            raise ValueError(f"{field_name} must be a string.")
        normalized = value.strip()
        if not normalized:
            raise ValueError(f"{field_name} must not be blank.")
        return str.__new__(cls, normalized)

    @property
    def value(self) -> str:
        return str(self)


class EnvVarName(NonEmptyString):
    """A valid environment variable name."""

    def __new__(cls, value: object, *, field_name: str = "env_var") -> "EnvVarName":
        normalized = str(NonEmptyString(value, field_name=field_name))
        if not _ENV_VAR_NAME_PATTERN.fullmatch(normalized):
            raise ValueError(
                f"{field_name} must be a valid environment variable name using letters, digits, and underscores."
            )
        return str.__new__(cls, normalized)


class ProviderFamilyName(NonEmptyString):
    """A normalized provider family identifier."""

    def __new__(cls, value: object, *, field_name: str = "family") -> "ProviderFamilyName":
        normalized = str(NonEmptyString(value, field_name=field_name)).lower()
        if not _PROVIDER_FAMILY_PATTERN.fullmatch(normalized):
            raise ValueError(
                f"{field_name} must be a lowercase provider identifier using letters, digits, and underscores."
            )
        return str.__new__(cls, normalized)


class HttpUrl(NonEmptyString):
    """A validated HTTP or HTTPS URL."""

    def __new__(cls, value: object, *, field_name: str = "url") -> "HttpUrl":
        normalized = str(NonEmptyString(value, field_name=field_name))
        parsed = urlparse(normalized)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError(f"{field_name} must be a valid http or https URL.")
        return str.__new__(cls, normalized)


class NonNegativeInt(int):
    """An integer greater than or equal to zero."""

    def __new__(cls, value: object, *, field_name: str = "value") -> "NonNegativeInt":
        normalized = _require_int(value, field_name=field_name)
        if normalized < 0:
            raise ValueError(f"{field_name} must be greater than or equal to zero.")
        return int.__new__(cls, normalized)

    @property
    def value(self) -> int:
        return int(self)


class PositiveInt(int):
    """An integer greater than zero."""

    def __new__(cls, value: object, *, field_name: str = "value") -> "PositiveInt":
        normalized = _require_int(value, field_name=field_name)
        if normalized <= 0:
            raise ValueError(f"{field_name} must be greater than zero.")
        return int.__new__(cls, normalized)

    @property
    def value(self) -> int:
        return int(self)


def parse_bounded_int(
    value: object,
    *,
    field_name: str = "value",
    minimum: int | None = None,
    maximum: int | None = None,
) -> int:
    """Validate one integer against optional inclusive bounds."""

    normalized = _require_int(value, field_name=field_name)
    if minimum is not None and normalized < minimum:
        raise ValueError(f"{field_name} must be greater than or equal to {minimum}.")
    if maximum is not None and normalized > maximum:
        raise ValueError(f"{field_name} must be less than or equal to {maximum}.")
    return normalized


def _require_int(value: object, *, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field_name} must be an integer.")
    return value


__all__ = [
    "EnvVarName",
    "HttpUrl",
    "NonEmptyString",
    "NonNegativeInt",
    "PositiveInt",
    "ProviderFamilyName",
    "parse_bounded_int",
]
