"""Credential loader for resolving environment variables from a repo .env file."""
"""Environment-variable credential loader backed by a repo-local .env file."""

from __future__ import annotations

import os
from typing import Sequence


class CredentialLoader:
    """Reads named environment variables from a repo-local ``.env`` file.

    The loader re-reads the file on every call so that test code that writes
    temporary ``.env`` files sees the correct values without needing to
    reinstantiate the loader.

    Args:
        env_path: Absolute or relative path to the ``.env`` file.  Defaults
            to ``.env`` in the current working directory.
    """Loads credential values from a ``.env`` file in the repository root.

    The ``.env`` file is read fresh on every :meth:`load` call so that changes
    made to the file during a session are reflected immediately and no stale
    cache accumulates across calls.

    Format rules for the ``.env`` file:

    - One ``KEY=VALUE`` pair per line.
    - Lines that are blank or start with ``#`` (after stripping leading
      whitespace) are treated as comments and ignored.
    - Values may be wrapped in single or double quotes; the quotes are stripped
      from the returned string.
    - Inline comments (e.g. ``KEY=value  # comment``) are **not** stripped —
      the full value after ``=`` (minus surrounding quotes) is returned. This
      matches the behaviour of most ``.env`` parsers.

    Args:
        env_path: Path to the ``.env`` file.  Defaults to ``".env"`` in the
            current working directory.

    Raises:
        FileNotFoundError: If the ``.env`` file does not exist at the
            configured path when :meth:`load` or :meth:`load_all` is called.
        KeyError: If a requested key is absent from the ``.env`` file.
    """

    def __init__(self, env_path: str | None = None) -> None:
        self._env_path = env_path or os.path.join(os.getcwd(), ".env")

    def load(self, key: str) -> str:
        """Return the value of *key* from the ``.env`` file.

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load(self, key: str) -> str:
        """Return the value of *key* from the ``.env`` file.

        Args:
            key: The environment-variable name to look up (case-sensitive).

        Returns:
            The string value associated with *key*.

        Raises:
            FileNotFoundError: If the ``.env`` file does not exist.
            KeyError: If *key* is not present in the ``.env`` file.
        """
        env_vars = self._parse_env_file()
        if key not in env_vars:
            raise KeyError(f"Environment variable '{key}' not found in {self._env_path}")
        return env_vars[key]

    def load_all(self, keys: Sequence[str]) -> dict[str, str]:
        """Return a mapping of *keys* to their values from the ``.env`` file.

        Raises:
            FileNotFoundError: If the ``.env`` file does not exist.
            KeyError: On the first key that is not present in the ``.env`` file.
        """
        env_vars = self._parse_env_file()
        result: dict[str, str] = {}
        for key in keys:
            if key not in env_vars:
                raise KeyError(f"Environment variable '{key}' not found in {self._env_path}")
            result[key] = env_vars[key]
        return result

    def _parse_env_file(self) -> dict[str, str]:
        """Parse the ``.env`` file and return a mapping of keys to values.

        Raises:
            FileNotFoundError: If the ``.env`` file does not exist.
        """
        if not os.path.isfile(self._env_path):
            raise FileNotFoundError(
                f".env file not found at '{self._env_path}'. "
                "Create a .env file with your credentials before using CredentialLoader."
            )
        env_vars: dict[str, str] = {}
        with open(self._env_path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
        env = self._parse_env_file()
        if key not in env:
            raise KeyError(
                f"Credential key '{key}' not found in {self._env_path!r}. "
                "Ensure the key is defined in your .env file."
            )
        return env[key]

    def load_all(self, keys: Sequence[str]) -> dict[str, str]:
        """Return a mapping of all *keys* resolved from the ``.env`` file.

        Keys are resolved in the order given.  The first missing key raises
        ``KeyError`` — subsequent keys are not evaluated.

        Args:
            keys: Sequence of environment-variable names to resolve.

        Returns:
            Dictionary mapping each key to its resolved value.

        Raises:
            FileNotFoundError: If the ``.env`` file does not exist.
            KeyError: If any key in *keys* is absent from the ``.env`` file.
        """
        env = self._parse_env_file()
        result: dict[str, str] = {}
        for key in keys:
            if key not in env:
                raise KeyError(
                    f"Credential key '{key}' not found in {self._env_path!r}. "
                    "Ensure the key is defined in your .env file."
                )
            result[key] = env[key]
        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _parse_env_file(self) -> dict[str, str]:
        """Read and parse the ``.env`` file into a key-value mapping."""
        if not os.path.exists(self._env_path):
            raise FileNotFoundError(
                f"Credential .env file not found at {self._env_path!r}. "
                "Create a .env file with your provider API keys before loading credentials."
            )

        env: dict[str, str] = {}
        with open(self._env_path, encoding="utf-8") as fh:
            for raw_line in fh:
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                key, _, raw_value = line.partition("=")
                key = key.strip()
                value = raw_value.strip()
                # Strip surrounding single or double quotes from the value.
                if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
                    value = value[1:-1]
                if key:
                    env_vars[key] = value
        return env_vars
                value = _strip_quotes(raw_value.strip())
                if key:
                    env[key] = value
        return env


def _strip_quotes(value: str) -> str:
    """Remove matching surrounding single or double quotes from *value*."""
    if len(value) >= 2:
        if (value[0] == '"' and value[-1] == '"') or (value[0] == "'" and value[-1] == "'"):
            return value[1:-1]
    return value


__all__ = ["CredentialLoader"]
