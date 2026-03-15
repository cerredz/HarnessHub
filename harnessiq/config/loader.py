"""Credential loader for resolving environment variables from a repo .env file."""

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
    """

    def __init__(self, env_path: str | None = None) -> None:
        self._env_path = env_path or os.path.join(os.getcwd(), ".env")

    def load(self, key: str) -> str:
        """Return the value of *key* from the ``.env`` file.

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


__all__ = ["CredentialLoader"]
