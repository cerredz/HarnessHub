"""Interface contracts for dynamic tool selection and embeddings."""

from __future__ import annotations

from typing import Any, Mapping, Protocol, Sequence, runtime_checkable

from harnessiq.shared.agents import AgentContextWindow
from harnessiq.shared.tool_selection import (
    ToolProfile,
    ToolSelectionConfig,
    ToolSelectionResult,
)


@runtime_checkable
class EmbeddingModelClient(Protocol):
    """Describe model clients that can produce embedding vectors."""

    def create_embedding(
        self,
        *,
        model_name: str,
        input_value: str | Sequence[str] | Sequence[int] | Sequence[Sequence[int]],
        dimensions: int | None = None,
        encoding_format: str | None = None,
        user: str | None = None,
    ) -> Any:
        """Create one embeddings response."""


@runtime_checkable
class EmbeddingBackend(Protocol):
    """Describe a backend that can embed one or more text inputs."""

    def embed_texts(self, texts: Sequence[str]) -> tuple[tuple[float, ...], ...]:
        """Return one vector per input text in the same logical order."""


@runtime_checkable
class DynamicToolSelector(Protocol):
    """Select the active model-visible tool subset for one agent turn."""

    @property
    def config(self) -> ToolSelectionConfig:
        """Return the selector configuration for this selector instance."""

    def index(self, profiles: Sequence[ToolProfile]) -> None:
        """Prepare the selector to rank the provided tool profiles."""

    def select(
        self,
        *,
        context_window: AgentContextWindow,
        candidate_profiles: Sequence[ToolProfile],
        metadata: Mapping[str, object] | None = None,
    ) -> ToolSelectionResult:
        """Return the selected subset for the next model turn."""


__all__ = [
    "DynamicToolSelector",
    "EmbeddingBackend",
    "EmbeddingModelClient",
]
