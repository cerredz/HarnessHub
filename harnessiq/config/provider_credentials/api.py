"""Lookup helpers for provider credential metadata."""

from __future__ import annotations

from harnessiq.shared.validated import ProviderFamilyName

from .catalog import PROVIDER_CREDENTIAL_SPECS
from .models import ProviderCredentialSpec


def get_provider_credential_spec(family: str) -> ProviderCredentialSpec:
    """Resolve one provider credential spec by normalized family name."""
    normalized_family = str(ProviderFamilyName(family))
    if normalized_family not in PROVIDER_CREDENTIAL_SPECS:
        raise KeyError(f"No provider credential spec exists for '{family}'.")
    return PROVIDER_CREDENTIAL_SPECS[normalized_family]


def list_provider_credential_specs() -> tuple[ProviderCredentialSpec, ...]:
    """Return the registered provider credential specs in deterministic order."""
    return tuple(PROVIDER_CREDENTIAL_SPECS.values())


__all__ = [
    "get_provider_credential_spec",
    "list_provider_credential_specs",
]
