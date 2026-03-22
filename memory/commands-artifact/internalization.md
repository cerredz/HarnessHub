### 1a: Structural Survey

- The repository is a Python SDK package with a single installed console script, `harnessiq`, declared in `pyproject.toml` and backed by `harnessiq.cli.main:main`.
- The CLI implementation is centralized in `harnessiq/cli/main.py`, which builds one root `argparse.ArgumentParser` and registers subcommands from four modules:
  - `harnessiq/cli/linkedin/commands.py`
  - `harnessiq/cli/exa_outreach/commands.py`
  - `harnessiq/cli/instagram/commands.py`
  - `harnessiq/cli/ledger/commands.py`
- The parser is source-of-truth for the public CLI surface. `README.md` and `docs/` mirror parts of the CLI, but the registered argparse commands are the authoritative interface for this task.
- Command families break down as follows:
  - Agent workflows: `linkedin`, `outreach`, `instagram`
  - Sink and ledger workflows: `connect`, `connections`, `logs`, `export`, `report`
- The CLI is tested directly with parser and runtime tests under `tests/`, especially:
  - `tests/test_linkedin_cli.py`
  - `tests/test_exa_outreach_cli.py`
  - `tests/test_instagram_cli.py`
  - `tests/test_ledger_cli.py`
- Existing artifact conventions are lightweight. `artifacts/file_index.md` is prose-first and explains repository structure at a high level rather than acting as a generated inventory.
- The working tree is already heavily dirty in unrelated files. Any implementation for this task should avoid editing existing CLI code unless a documentation gap is caused by a real parser mismatch.

### 1b: Task Cross-Reference

- User request: create a new artifact in `artifacts/` at the same folder level as `artifacts/file_index.md` that details all CLI commands and gives a short description for each.
- Files that define the command catalog:
  - `pyproject.toml`: confirms the installed entrypoint name `harnessiq`
  - `harnessiq/cli/__main__.py`: confirms `python -m harnessiq.cli` is also a valid entrypoint
  - `harnessiq/cli/main.py`: root parser and top-level command registration
  - `harnessiq/cli/linkedin/commands.py`: LinkedIn command family and subcommands
  - `harnessiq/cli/exa_outreach/commands.py`: outreach command family and subcommands
  - `harnessiq/cli/instagram/commands.py`: Instagram command family and subcommands
  - `harnessiq/cli/ledger/commands.py`: sink connection, ledger query, export, and report commands
- Supporting validation files:
  - `README.md`
  - `docs/output-sinks.md`
  - `docs/linkedin-agent.md`
  - CLI test files under `tests/`
- Net-new work required:
  - Create a new artifact file, best named `artifacts/commands.md`
  - Document every currently registered user-facing command and subcommand
  - Keep descriptions short and aligned with argparse help text so the artifact stays faithful to the implementation
- Existing behavior that must be preserved:
  - No parser changes
  - No command renames
  - No changes to README or current docs unless strictly needed for consistency
- Blast radius is low and documentation-only if implemented correctly.

### 1c: Assumption & Risk Inventory

- Assumption: "all of the cli commands" means all currently registered user-facing commands and subcommands exposed by argparse, not every flag for every command.
- Assumption: the artifact should live at `artifacts/commands.md`, since the user asked for a "commands" artifact at the same directory level as `artifacts/file_index.md`.
- Assumption: descriptions should reflect current code, even where implementation naming differs from folder naming. Example: the `exa_outreach` CLI module exposes the user-facing command `outreach`.
- Risk: README examples could lag behind the parser. Mitigation: derive the catalog from `harnessiq/cli/*.py` and confirm with `python -m harnessiq.cli ... --help`.
- Risk: the dirty worktree makes unrelated edits easy to disturb. Mitigation: add only new files for this task and do not rewrite existing modified files.
- Risk: connect sink commands are generated programmatically in `_register_connect_command`; missing one would leave the artifact incomplete. Mitigation: enumerate the registered sink types directly from `harnessiq/cli/ledger/commands.py` and verify with `python -m harnessiq.cli connect --help`.

Phase 1 complete.
