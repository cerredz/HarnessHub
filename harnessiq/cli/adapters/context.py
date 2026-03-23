"""Shared context models for platform-first CLI adapters."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from harnessiq.config import HarnessProfile
from harnessiq.shared.harness_manifest import HarnessManifest


@dataclass(frozen=True, slots=True)
class HarnessAdapterContext:
    """Bundle the shared state one platform CLI adapter needs for a command."""

    manifest: HarnessManifest
    agent_name: str
    memory_path: Path
    repo_root: Path
    profile: HarnessProfile
    runtime_parameters: dict[str, Any]
    custom_parameters: dict[str, Any]
    bound_credentials: dict[str, object]


__all__ = ["HarnessAdapterContext"]
