"""MasterPrompt dataclass and registry for loading bundled master prompts."""

from __future__ import annotations

import json
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Iterator


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
    """Load and retrieve master prompts bundled with the harnessiq package.

    Prompts are stored as JSON files under ``harnessiq/master_prompts/prompts/``.
    Each file must contain ``title``, ``description``, and ``prompt`` fields.
    The prompt key is the filename without the ``.json`` extension.

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
        self._cache = {}
        for key, data in _iter_prompt_files():
            self._cache[key] = MasterPrompt(
                key=key,
                title=str(data["title"]),
                description=str(data["description"]),
                prompt=str(data["prompt"]),
            )
        return self._cache


def _iter_prompt_files() -> Iterator[tuple[str, dict]]:
    """Yield (key, parsed_json) for every .json file in the prompts package."""
    try:
        # importlib.resources is the correct way to locate package data files
        # in both editable installs and built distributions.
        prompts_package = resources.files("harnessiq.master_prompts.prompts")
        for item in prompts_package.iterdir():
            if item.name.endswith(".json"):
                key = item.name[: -len(".json")]
                data = json.loads(item.read_text(encoding="utf-8"))
                yield key, data
    except (TypeError, FileNotFoundError):
        # Fallback for environments where importlib.resources.files is unavailable
        prompts_dir = Path(__file__).parent / "prompts"
        for json_path in sorted(prompts_dir.glob("*.json")):
            key = json_path.stem
            data = json.loads(json_path.read_text(encoding="utf-8"))
            yield key, data


__all__ = [
    "MasterPrompt",
    "MasterPromptRegistry",
]
