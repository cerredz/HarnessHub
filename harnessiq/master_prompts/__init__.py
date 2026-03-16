"""Master prompts — curated, deployable system prompts for agents and direct SDK use.

Each master prompt is a structured behavioral contract for a specific domain or
workflow. Prompts can be injected into any agent harness or retrieved via the API
and passed directly to a model.

Basic usage::

    from harnessiq.master_prompts import get_prompt, list_prompts, get_prompt_text

    # Retrieve a full MasterPrompt record
    prompt = get_prompt("create_master_prompts")
    print(prompt.title)
    print(prompt.description)
    system_prompt_text = prompt.prompt

    # Retrieve just the raw prompt string for injection
    system_prompt_text = get_prompt_text("create_master_prompts")

    # List all available master prompts
    for p in list_prompts():
        print(p.key, p.title)

Via the lazy top-level import::

    import harnessiq
    prompt = harnessiq.master_prompts.get_prompt("create_master_prompts")
"""

from __future__ import annotations

from harnessiq.master_prompts.registry import MasterPrompt, MasterPromptRegistry

# Shared module-level registry instance — loaded lazily on first access.
_registry: MasterPromptRegistry | None = None


def _get_registry() -> MasterPromptRegistry:
    global _registry
    if _registry is None:
        _registry = MasterPromptRegistry()
    return _registry


def get_prompt(key: str) -> MasterPrompt:
    """Return the :class:`MasterPrompt` with the given key.

    Args:
        key: The prompt identifier (filename without ``.json`` extension).

    Raises:
        KeyError: If no prompt with that key is registered.
    """
    return _get_registry().get(key)


def get_prompt_text(key: str) -> str:
    """Return just the raw prompt string for the given key.

    This is the most common call when injecting a master prompt into a model
    or agent without needing the metadata fields.

    Args:
        key: The prompt identifier (filename without ``.json`` extension).

    Raises:
        KeyError: If no prompt with that key is registered.
    """
    return _get_registry().get_prompt_text(key)


def list_prompts() -> list[MasterPrompt]:
    """Return all registered master prompts sorted by key."""
    return _get_registry().list()


__all__ = [
    "MasterPrompt",
    "MasterPromptRegistry",
    "get_prompt",
    "get_prompt_text",
    "list_prompts",
]
