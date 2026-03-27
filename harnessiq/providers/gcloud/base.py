"""Shared base class for Google Cloud providers."""

from __future__ import annotations

from abc import ABC
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from harnessiq.providers.gcloud.client import GcloudClient
    from harnessiq.providers.gcloud.config import GcpAgentConfig


class BaseGcpProvider(ABC):
    """Base class for all GCP provider implementations."""

    def __init__(self, client: "GcloudClient", config: "GcpAgentConfig") -> None:
        self._client = client
        self._config = config

    @property
    def client(self) -> "GcloudClient":
        return self._client

    @property
    def config(self) -> "GcpAgentConfig":
        return self._config
