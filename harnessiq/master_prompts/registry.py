"""MasterPrompt dataclass and registry for loading artifact-backed master prompts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator


REPO_ROOT = Path(__file__).resolve().parents[2]
PROMPTS_DIR = REPO_ROOT / "artifacts" / "prompts"
REGISTRY_PATH = PROMPTS_DIR / "registry.json"


@dataclass(frozen=True, slots=True)
class MasterPrompt:
    """A named, deployable system prompt with metadata.

    Attributes:
        key: Unique identifier derived from the prompt's filename (no extension).
        title: Human-readable title describing what the prompt is for.
        description: One-paragraph summary of the prompt's purpose and target use case.
        prompt: The full, deployment-ready system prompt text.
    """

    key: str
    title: str
    description: str
    prompt: str


class MasterPromptRegistry:
    """Load and retrieve master prompts from repository prompt artifacts.

    Prompts are stored as Markdown files under ``artifacts/prompts/``.
    The registry metadata is read from ``artifacts/prompts/registry.json`` when present.
    The prompt key is the filename without the ``.md`` extension.

    Example::

        registry = MasterPromptRegistry()
        prompt = registry.get("create_master_prompts")
        system_prompt_text = prompt.prompt
    """

    def __init__(self) -> None:
        self._cache: dict[str, MasterPrompt] | None = None

    def list(self) -> list[MasterPrompt]:
        """Return all registered master prompts sorted by key."""
        return sorted(self._load_all().values(), key=lambda p: p.key)

    def keys(self) -> list[str]:
        """Return all registered prompt keys sorted alphabetically."""
        return [prompt.key for prompt in self.list()]

    def has(self, key: str) -> bool:
        """Return whether a prompt with the given key exists."""
        return key in self._load_all()

    def get(self, key: str) -> MasterPrompt:
        """Return the master prompt with the given key.

        Raises:
            KeyError: If no prompt with that key exists.
        """
        prompts = self._load_all()
        if key not in prompts:
            available = ", ".join(sorted(prompts))
            raise KeyError(f"No master prompt with key '{key}'. Available keys: {available}.")
        return prompts[key]

    def get_prompt_text(self, key: str) -> str:
        """Return just the prompt text for the given key.

        Raises:
            KeyError: If no prompt with that key exists.
        """
        return self.get(key).prompt

    def _load_all(self) -> dict[str, MasterPrompt]:
        if self._cache is not None:
            return self._cache
        descriptions = _load_registry_descriptions()
        self._cache = {}
        for key, prompt_text in _iter_prompt_files():
            self._cache[key] = MasterPrompt(
                key=key,
                title=_slug_to_title(key),
                description=descriptions.get(key, "HarnessHub master prompt"),
                prompt=prompt_text,
            )
        return self._cache


def _iter_prompt_files() -> Iterator[tuple[str, str]]:
    """Yield ``(key, prompt_text)`` for every prompt artifact."""
    for prompt_path in sorted(PROMPTS_DIR.glob("*.md")):
        yield prompt_path.stem, prompt_path.read_text(encoding="utf-8")


def _load_registry_descriptions() -> dict[str, str]:
    if not REGISTRY_PATH.exists():
        return {}
    try:
        import json

        payload = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    harnesses = payload.get("harnesses")
    if not isinstance(harnesses, list):
        return {}
    descriptions: dict[str, str] = {}
    for item in harnesses:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip()
        description = str(item.get("description", "")).strip()
        if name and description:
            descriptions[name] = description
    return descriptions


def _slug_to_title(slug: str) -> str:
    return slug.replace("_", " ").replace("-", " ").title()


__all__ = [
    "MasterPrompt",
    "MasterPromptRegistry",
]
