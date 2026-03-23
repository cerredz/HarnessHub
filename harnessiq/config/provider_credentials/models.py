"""Typed provider credential metadata models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Mapping

from .masking import mask_secret


@dataclass(frozen=True, slots=True)
class ProviderCredentialFieldSpec:
    """Describe one bindable credential field for a provider family."""

    name: str
    description: str

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Provider credential field name must not be blank.")
        if not self.description.strip():
            raise ValueError("Provider credential field description must not be blank.")


@dataclass(frozen=True, slots=True)
class ProviderCredentialSpec:
    """Describe how one provider family's credentials are validated and constructed."""

    family: str
    description: str
    fields: tuple[ProviderCredentialFieldSpec, ...]
    builder: Callable[[Mapping[str, str]], object]

    def __post_init__(self) -> None:
        normalized_family = self.family.strip().lower()
        if not normalized_family:
            raise ValueError("Provider credential family must not be blank.")
        if not self.description.strip():
            raise ValueError("Provider credential description must not be blank.")
        if not self.fields:
            raise ValueError("Provider credential specs must declare at least one field.")
        object.__setattr__(self, "family", normalized_family)
        object.__setattr__(self, "fields", tuple(self.fields))

    @property
    def field_names(self) -> tuple[str, ...]:
        """Return the ordered field names expected by this provider family."""
        return tuple(field.name for field in self.fields)

    def validate_fields(self, values: Mapping[str, str]) -> dict[str, str]:
        """Validate one raw field mapping against the declared provider field set."""
        normalized = {str(key): str(value) for key, value in values.items()}
        missing = [field.name for field in self.fields if not normalized.get(field.name, "").strip()]
        if missing:
            rendered = ", ".join(missing)
            raise ValueError(f"Provider family '{self.family}' is missing required credential fields: {rendered}.")
        unsupported = sorted(set(normalized) - set(self.field_names))
        if unsupported:
            rendered = ", ".join(unsupported)
            raise ValueError(f"Provider family '{self.family}' does not support credential fields: {rendered}.")
        return {key: normalized[key] for key in self.field_names}

    def build_credentials(self, values: Mapping[str, str]) -> object:
        """Construct one provider credential object from validated values."""
        return self.builder(self.validate_fields(values))

    def redact_values(self, values: Mapping[str, str]) -> dict[str, str]:
        """Return a masked representation of validated credential values for CLI output."""
        return {key: mask_secret(value) for key, value in self.validate_fields(values).items()}


__all__ = [
    "ProviderCredentialFieldSpec",
    "ProviderCredentialSpec",
]
