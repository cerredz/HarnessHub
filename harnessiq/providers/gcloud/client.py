"""Subprocess-backed gcloud execution helpers."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from typing import Any, Sequence


@dataclass(slots=True)
class GcloudError(RuntimeError):
    """Raised when a gcloud command exits unsuccessfully."""

    command: tuple[str, ...]
    exit_code: int
    stderr: str
    stdout: str = ""

    def __post_init__(self) -> None:
        command_text = " ".join(self.command)
        message = f"gcloud command failed with exit code {self.exit_code}: {command_text}"
        detail = self.stderr.strip() or self.stdout.strip()
        if detail:
            message = f"{message}\n{detail}"
        RuntimeError.__init__(self, message)


@dataclass(slots=True)
class GcloudClient:
    """Execute gcloud commands with shared project and region defaults."""

    project_id: str
    region: str
    dry_run: bool = False

    def __post_init__(self) -> None:
        self.project_id = self.project_id.strip()
        self.region = self.region.strip()
        if not self.project_id:
            raise ValueError("project_id must not be blank.")
        if not self.region:
            raise ValueError("region must not be blank.")

    def build_command(self, args: Sequence[str]) -> list[str]:
        """Return the full gcloud command with the project flag injected."""
        command = ["gcloud", *[str(arg) for arg in args]]
        if not self._has_project_flag(command[1:]):
            command.append(f"--project={self.project_id}")
        return command

    def run(self, args: Sequence[str], *, input_text: str | None = None) -> str:
        """Execute a gcloud command and return trimmed stdout."""
        command = self.build_command(args)
        if self.dry_run:
            return self.render_command(command)
        completed = subprocess.run(
            command,
            input=input_text,
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            raise GcloudError(
                command=tuple(command),
                exit_code=int(completed.returncode),
                stderr=completed.stderr,
                stdout=completed.stdout,
            )
        return completed.stdout.strip()

    def run_json(self, args: Sequence[str], *, input_text: str | None = None) -> Any:
        """Execute a gcloud command and decode JSON output."""
        command = self.build_command(args)
        if self.dry_run:
            return {
                "dry_run": True,
                "command": command,
            }
        raw = self.run(args, input_text=input_text)
        if not raw:
            raise ValueError(f"gcloud command produced no JSON output: {self.render_command(command)}")
        return json.loads(raw)

    @staticmethod
    def render_command(command: Sequence[str]) -> str:
        """Render a command list as a human-readable preview string."""
        return " ".join(str(part) for part in command)

    @staticmethod
    def _has_project_flag(args: Sequence[str]) -> bool:
        for index, arg in enumerate(args):
            if arg == "--project":
                return True
            if arg.startswith("--project="):
                return True
            if arg == "-q" and index + 1 < len(args) and args[index + 1] == "--project":
                return True
        return False
