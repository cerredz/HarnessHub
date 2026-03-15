"""Credential configuration and environment-variable loading for Harnessiq providers."""

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
    "DotEnvFileNotFoundError",
    "MissingEnvironmentVariableError",
    "ProviderCredentialConfig",
    "ResolvedAgentCredentials",
    "parse_dotenv_file",
]
