"""Master prompts sourced from repository prompt artifacts."""

from __future__ import annotations

from harnessiq.master_prompts.registry import MasterPrompt, MasterPromptRegistry


_registry: MasterPromptRegistry | None = None


def _get_registry() -> MasterPromptRegistry:
    global _registry
    if _registry is None:
        _registry = MasterPromptRegistry()
    return _registry


def get_prompt(key: str) -> MasterPrompt:
    """Return the artifact-backed prompt identified by the Markdown filename stem."""
    return _get_registry().get(key)


def get_prompt_text(key: str) -> str:
    """Return the raw prompt text for one artifact-backed prompt."""
    return _get_registry().get_prompt_text(key)


def list_prompts() -> list[MasterPrompt]:
    """Return all registered master prompts sorted by key."""
    return _get_registry().list()


def list_prompt_keys() -> list[str]:
    """Return all registered prompt keys sorted alphabetically."""
    return _get_registry().keys()


def has_prompt(key: str) -> bool:
    """Return whether an artifact-backed prompt with the given key exists."""
    return _get_registry().has(key)


__all__ = [
    "MasterPrompt",
    "MasterPromptRegistry",
    "get_prompt",
    "get_prompt_text",
    "has_prompt",
    "list_prompt_keys",
    "list_prompts",
]
