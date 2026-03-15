"""Base credential configuration types for the Harnessiq config layer."""
"""Base credential-config type for Harnessiq provider credential models."""

from __future__ import annotations

from typing import TypedDict


class ProviderCredentialConfig(TypedDict, total=False):
    """Base type for per-provider credential configuration.

    Concrete per-provider credential TypedDicts extend this base in their
    respective provider packages (e.g. ``harnessiq/providers/snovio/credentials.py``).
    Concrete subclasses should declare all required fields explicitly and
    typically use ``total=True`` (the default) to enforce that all keys are
    present at construction time.
    """

    """Base shape for provider credential config objects.

    Concrete per-provider credential configs are TypedDicts that extend this
    base by declaring the environment-variable name(s) they require. Each key
    maps a credential field (e.g. ``"api_key"``) to the name of the environment
    variable that holds the secret (e.g. ``"CREATIFY_API_KEY"``).

    Example concrete config::

        class CreatifyCredentialConfig(ProviderCredentialConfig):
            api_id_env_var: str
            api_key_env_var: str

    ``CredentialLoader.load_provider_config(config)`` resolves the env-var
    references at call time from the repo-local ``.env`` file.
    """

    provider: str


__all__ = ["ProviderCredentialConfig"]
