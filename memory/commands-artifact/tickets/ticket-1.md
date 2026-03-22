Title: Add a CLI command catalog artifact

Intent: Create a repository artifact that gives contributors and users a single source-of-truth overview of the full user-facing HarnessIQ CLI surface without requiring them to inspect argparse registration code.

Scope:
- Create a new artifact under `artifacts/` that lists every current CLI command and subcommand with a short description.
- Base the catalog on the registered parser and current help text.
- Keep the change documentation-only.
- Do not modify CLI behavior, parser registration, tests, or README examples unless a blocking inconsistency is discovered.

Relevant Files:
- `artifacts/commands.md` - New artifact containing the CLI command catalog.
- `harnessiq/cli/main.py` - Source of truth for top-level command registration.
- `harnessiq/cli/linkedin/commands.py` - Source of truth for LinkedIn commands.
- `harnessiq/cli/exa_outreach/commands.py` - Source of truth for outreach commands.
- `harnessiq/cli/instagram/commands.py` - Source of truth for Instagram commands.
- `harnessiq/cli/ledger/commands.py` - Source of truth for sink and ledger commands.

Approach:
- Read the root parser registration and each command module to enumerate the full command tree.
- Validate command names and help text with `python -m harnessiq.cli ... --help`.
- Write a concise Markdown artifact grouped by command family so the document is easy to scan and maintain.
- Use user-facing command names exactly as registered by argparse, even if internal module names differ.

Assumptions:
- The artifact should be named `artifacts/commands.md`.
- The requested level of detail is command-level, not flag-level.
- Existing parser help strings are acceptable as the baseline wording for short descriptions.

Acceptance Criteria:
- [ ] `artifacts/commands.md` exists in the repo root artifact folder.
- [ ] The artifact documents every currently registered top-level command.
- [ ] The artifact documents every currently registered subcommand under `linkedin`, `outreach`, `instagram`, `connect`, and `connections`.
- [ ] Each documented command has a short description aligned with the current CLI behavior.
- [ ] No existing CLI code or runtime behavior changes.

Verification Steps:
- Run `python -m harnessiq.cli --help`.
- Run `python -m harnessiq.cli linkedin --help`.
- Run `python -m harnessiq.cli outreach --help`.
- Run `python -m harnessiq.cli instagram --help`.
- Run `python -m harnessiq.cli connect --help`.
- Run `python -m harnessiq.cli connections --help`.
- Run `python -m harnessiq.cli logs --help`.
- Run `python -m harnessiq.cli export --help`.
- Run `python -m harnessiq.cli report --help`.
- Cross-check the artifact entries against `harnessiq/cli/*.py`.

Dependencies: None.

Drift Guard: This ticket must stay strictly documentation-only. It must not rename commands, add aliases, expand help text in code, or turn into a broader CLI redesign or README refresh.
