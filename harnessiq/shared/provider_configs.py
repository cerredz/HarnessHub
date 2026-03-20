"""Shared provider transport configuration models."""

from __future__ import annotations

from dataclasses import dataclass

from harnessiq.shared.providers import ARXIV_DEFAULT_BASE_URL


@dataclass(frozen=True, slots=True)
class ArxivConfig:
    """Transport configuration for the arXiv API."""

    base_url: str = ARXIV_DEFAULT_BASE_URL
    timeout_seconds: float = 30.0
    delay_seconds: float = 0.0

    def __post_init__(self) -> None:
        if not self.base_url.strip():
            raise ValueError("ArxivConfig.base_url must not be blank.")
        if self.timeout_seconds <= 0:
            raise ValueError("ArxivConfig.timeout_seconds must be greater than zero.")
        if self.delay_seconds < 0:
            raise ValueError("ArxivConfig.delay_seconds must be zero or greater.")


__all__ = ["ArxivConfig"]
