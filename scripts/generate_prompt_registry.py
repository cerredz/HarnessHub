from __future__ import annotations

import argparse
import json
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROMPTS_DIR = ROOT / "artifacts" / "prompts"
REGISTRY_PATH = PROMPTS_DIR / "registry.json"
DESCRIPTION_LIMIT = 160


@dataclass(frozen=True, slots=True)
class PromptRegistryEntry:
    name: str
    description: str
    updated_at: str

    def as_dict(self) -> dict[str, str]:
        return {
            "name": self.name,
            "description": self.description,
            "updated_at": self.updated_at,
        }


def build_registry(*, prompts_dir: Path = PROMPTS_DIR) -> dict[str, list[dict[str, str]]]:
    entries = [
        _build_entry(path)
        for path in sorted(prompts_dir.glob("*.md"))
        if path.is_file()
    ]
    return {"harnesses": [entry.as_dict() for entry in entries]}


def render_registry(*, prompts_dir: Path = PROMPTS_DIR) -> str:
    return json.dumps(build_registry(prompts_dir=prompts_dir), indent=2, sort_keys=False) + "\n"


def write_registry(*, prompts_dir: Path = PROMPTS_DIR, registry_path: Path = REGISTRY_PATH) -> str:
    content = render_registry(prompts_dir=prompts_dir)
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(content, encoding="utf-8")
    return content


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate artifacts/prompts/registry.json from prompt Markdown files.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify that registry.json matches the generated content without rewriting it.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    content = render_registry()
    if args.check:
        if not REGISTRY_PATH.exists() or REGISTRY_PATH.read_text(encoding="utf-8") != content:
            print("Prompt registry is out of date.")
            return 1
        print("Prompt registry is in sync.")
        return 0
    write_registry()
    print(f"Updated {REGISTRY_PATH.relative_to(ROOT).as_posix()}")
    return 0


def _build_entry(path: Path) -> PromptRegistryEntry:
    return PromptRegistryEntry(
        name=path.stem,
        description=_derive_description(path.read_text(encoding="utf-8")),
        updated_at=_resolve_updated_at(path),
    )


def _derive_description(prompt_text: str) -> str:
    normalized = prompt_text.replace("\r\n", "\n").strip()
    if not normalized:
        return "HarnessHub master prompt"
    paragraphs = [segment.strip() for segment in normalized.split("\n\n") if segment.strip()]
    first_block = next(
        (segment for segment in paragraphs if not _looks_like_heading_only_block(segment)),
        normalized,
    )
    first_block = re.sub(r"\s+", " ", first_block)
    sentence_match = re.search(r"(.+?[.!?])(?:\s|$)", first_block)
    description = sentence_match.group(1) if sentence_match else first_block
    if len(description) <= DESCRIPTION_LIMIT:
        return description
    truncated = description[: DESCRIPTION_LIMIT - 3].rstrip()
    return f"{truncated}..."


def _looks_like_heading_only_block(block: str) -> bool:
    stripped = block.strip()
    if not stripped:
        return True
    if stripped == "---":
        return True
    if stripped.startswith("#"):
        return True
    collapsed = stripped.lower().replace("*", "").replace("_", "")
    return collapsed in {
        "identity",
        "identity / persona",
        "goal",
        "checklist",
        "things not to do",
        "success criteria",
        "artifacts",
        "inputs",
    }


def _resolve_updated_at(path: Path) -> str:
    try:
        relative = path.relative_to(ROOT)
    except ValueError:
        relative = None
    try:
        completed = None
        if relative is not None:
            completed = subprocess.run(
                ["git", "log", "-1", "--format=%cI", "--", str(relative)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
    except OSError:
        completed = None
    if completed is not None:
        timestamp = completed.stdout.strip()
        if timestamp:
            return timestamp
    modified = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    return modified.isoformat().replace("+00:00", "Z")


if __name__ == "__main__":
    raise SystemExit(main())
