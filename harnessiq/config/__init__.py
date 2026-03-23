"""Credential configuration and environment-variable loading for Harnessiq providers."""

from __future__ import annotations

from importlib import import_module
from typing import Any

from .credentials import (
    AgentCredentialBinding,
    AgentCredentialsNotConfiguredError,
    CredentialEnvReference,
    CredentialsConfig,
    CredentialsConfigError,
    CredentialsConfigStore,
    DEFAULT_CONFIG_DIRNAME,
    DEFAULT_CREDENTIALS_CONFIG_FILENAME,
    DEFAULT_ENV_FILENAME,
    DotEnvFileNotFoundError,
    MissingEnvironmentVariableError,
    ResolvedAgentCredentials,
    parse_dotenv_file,
)
from .harness_profiles import (
    DEFAULT_HARNESS_PROFILE_FILENAME,
    HarnessProfile,
    HarnessProfileStore,
    build_harness_credential_binding_name,
)
from .loader import CredentialLoader
from .models import ProviderCredentialConfig

__all__ = [
    "AgentCredentialBinding",
    "AgentCredentialsNotConfiguredError",
    "CredentialEnvReference",
    "CredentialLoader",
    "CredentialsConfig",
    "CredentialsConfigError",
    "CredentialsConfigStore",
    "DEFAULT_CONFIG_DIRNAME",
    "DEFAULT_CREDENTIALS_CONFIG_FILENAME",
    "DEFAULT_ENV_FILENAME",
    "DEFAULT_HARNESS_PROFILE_FILENAME",
    "DotEnvFileNotFoundError",
    "HarnessProfile",
    "HarnessProfileStore",
    "MissingEnvironmentVariableError",
    "PROVIDER_CREDENTIAL_SPECS",
    "ProviderCredentialConfig",
    "ProviderCredentialFieldSpec",
    "ProviderCredentialSpec",
    "ResolvedAgentCredentials",
    "build_harness_credential_binding_name",
    "get_provider_credential_spec",
    "list_provider_credential_specs",
    "parse_dotenv_file",
]

_LAZY_PROVIDER_CREDENTIAL_EXPORTS = {
    "PROVIDER_CREDENTIAL_SPECS",
    "ProviderCredentialFieldSpec",
    "ProviderCredentialSpec",
    "get_provider_credential_spec",
    "list_provider_credential_specs",
}


def __getattr__(name: str) -> Any:
    if name not in _LAZY_PROVIDER_CREDENTIAL_EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = import_module(".provider_credentials", __name__)
    value = getattr(module, name)
    globals()[name] = value
    return value
