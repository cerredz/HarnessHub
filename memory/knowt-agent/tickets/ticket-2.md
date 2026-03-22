# Ticket 2: Knowt Shared Types and Memory Store

## Title
Add `harnessiq/shared/knowt.py` with `KnowtMemoryStore`, config types, and filename constants

## Intent
The Knowt agent needs a file-backed memory store to persist the current script and avatar description across runs (same pattern as `LinkedInMemoryStore`). This ticket establishes all shared types and the memory store used by both the Knowt tool layer (ticket 3) and the agent harness (ticket 4). Centralizing these in `harnessiq/shared/` follows the existing LinkedIn convention.

## Scope
**In scope**:
- `harnessiq/shared/knowt.py` with: filename constants, `KnowtMemoryStore` (file-backed), `KnowtAgentConfig` (frozen dataclass), `KnowtCreationLogEntry` (frozen dataclass)

**Out of scope**:
- Any tool implementations
- The agent harness itself
- CLI commands

## Relevant Files
| File | Change |
|------|--------|
| `harnessiq/shared/knowt.py` | New — all Knowt shared types |

## Approach

### Filename constants
```python
CURRENT_SCRIPT_FILENAME = "current_script.md"
CURRENT_AVATAR_DESCRIPTION_FILENAME = "current_avatar_description.md"
CREATION_LOG_FILENAME = "creation_log.jsonl"
```

### KnowtMemoryStore
```python
@dataclass(slots=True)
class KnowtMemoryStore:
    memory_path: Path

    def prepare(self) -> None: ...          # mkdir + ensure files exist
    def write_script(self, content: str) -> Path: ...
    def read_script(self) -> str | None: ...
    def is_script_created(self) -> bool: ...
    def write_avatar_description(self, content: str) -> Path: ...
    def read_avatar_description(self) -> str | None: ...
    def is_avatar_description_created(self) -> bool: ...
    def append_creation_log(self, entry: dict[str, Any]) -> None: ...
    def write_file(self, filename: str, content: str) -> Path: ...
    def edit_file(self, filename: str, content: str) -> Path: ...
    def read_file(self, filename: str) -> str: ...
```

`is_script_created()` returns True iff `current_script.md` exists and has non-empty content.
`is_avatar_description_created()` returns True iff `current_avatar_description.md` exists and has non-empty content.

`write_file` / `edit_file` both resolve to `memory_path / filename` with path-traversal guard (same pattern as LinkedIn's `read_memory_file`).

### KnowtAgentConfig
```python
@dataclass(frozen=True, slots=True)
class KnowtAgentConfig:
    memory_path: Path
    max_tokens: int = DEFAULT_AGENT_MAX_TOKENS
    reset_threshold: float = DEFAULT_AGENT_RESET_THRESHOLD
```

### KnowtCreationLogEntry
```python
@dataclass(frozen=True, slots=True)
class KnowtCreationLogEntry:
    timestamp: str
    action: str        # "create_script", "create_avatar_description", "create_video"
    summary: str

    def as_dict(self) -> dict[str, str]: ...

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "KnowtCreationLogEntry": ...
```

## Assumptions
- `DEFAULT_AGENT_MAX_TOKENS` and `DEFAULT_AGENT_RESET_THRESHOLD` are imported from `harnessiq.shared.agents`
- File-backed memory follows the same conventions as LinkedIn (UTF-8, trailing newline, path guard)

## Acceptance Criteria
- [ ] `harnessiq/shared/knowt.py` exists with all three constants, `KnowtMemoryStore`, `KnowtAgentConfig`, `KnowtCreationLogEntry`
- [ ] `KnowtMemoryStore.prepare()` creates the memory directory and ensures the three files exist (empty by default)
- [ ] `is_script_created()` returns False when file is missing or empty, True when it has content
- [ ] `is_avatar_description_created()` same as above for avatar description file
- [ ] `write_file` / `edit_file` raise `ValueError` if the resolved path escapes `memory_path`
- [ ] `KnowtCreationLogEntry.as_dict()` / `from_dict()` round-trip correctly
- [ ] `KnowtAgentConfig` is frozen, slots=True
- [ ] All types are fully annotated with no `Any` leakage in public signatures
- [ ] No linter or type errors

## Verification Steps
1. `ruff check harnessiq/shared/knowt.py`
2. `mypy harnessiq/shared/knowt.py`
3. Manual smoke: instantiate `KnowtMemoryStore` with a temp path, call `prepare()`, write script, verify `is_script_created()` returns True, read back and assert content matches.

## Dependencies
Ticket 1 (for import order clarity, but no hard code dependency).

## Drift Guard
This ticket must not add any tool definitions, tool handlers, agent classes, or CLI commands. It must not modify any existing shared file.
