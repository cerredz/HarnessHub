"""Provider-family credential specs used by the platform CLI."""

from .api import get_provider_credential_spec, list_provider_credential_specs
from .catalog import PROVIDER_CREDENTIAL_SPECS
from .models import ProviderCredentialFieldSpec, ProviderCredentialSpec

__all__ = [
    "PROVIDER_CREDENTIAL_SPECS",
    "ProviderCredentialFieldSpec",
    "ProviderCredentialSpec",
    "get_provider_credential_spec",
    "list_provider_credential_specs",
]
