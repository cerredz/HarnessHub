Title: Centralize shared CLI agent-command helpers and JSON rendering

Intent:
Reduce repeated helper logic across the agent-oriented CLI modules so command behavior is easier to reason about, update, and test. This directly improves readability and lowers the risk of command drift when new agent CLIs are added.

Issue URL: https://github.com/cerredz/HarnessHub/issues/205

Scope:

- Add a shared CLI helper module for the repeated command patterns currently duplicated across agent command modules.
- Move shared logic for JSON emission, slugified memory-path resolution, text-or-file argument handling, and generic runtime assignment parsing into that shared helper layer.
- Update the existing command modules to use the shared helpers without changing their public command names or output shapes.
- Keep command-specific normalization logic inside each command module where it belongs.
- Do not redesign CLI UX or rename flags.

Relevant Files:

- `harnessiq/cli/common.py`: new shared helper module for JSON output, memory-path helpers, text/file resolution, and generic assignment parsing.
- `harnessiq/cli/linkedin/commands.py`: replace duplicated helper implementations with imports from the shared helper layer.
- `harnessiq/cli/instagram/commands.py`: replace duplicated helper implementations with imports from the shared helper layer.
- `harnessiq/cli/prospecting/commands.py`: replace duplicated helper implementations with imports from the shared helper layer.
- `harnessiq/cli/exa_outreach/commands.py`: replace duplicated helper implementations with imports from the shared helper layer.
- `harnessiq/cli/ledger/commands.py`: reuse the shared JSON emission helper.
- `tests/test_linkedin_cli.py`: confirm behavior is unchanged after helper extraction.
- `tests/test_instagram_cli.py`: confirm behavior is unchanged after helper extraction.
- `tests/test_prospecting_cli.py`: confirm behavior is unchanged after helper extraction.
- `tests/test_exa_outreach_cli.py`: confirm behavior is unchanged after helper extraction.
- `tests/test_ledger_cli.py`: confirm ledger CLI JSON emission still works through the shared helper.

Approach:

- Create a small, dependency-light helper module under `harnessiq/cli/`.
- Keep the abstractions narrow and concrete: pure helpers rather than new OO command wrappers.
- Provide a JSON rendering helper that uses deterministic formatting and tolerates common Path-like values safely.
- Provide a generic assignment parser that returns scalar JSON-decoded values; each CLI module will continue to run its own command-specific normalization after parsing.
- Refactor incrementally and keep command output payloads byte-for-byte compatible where reasonable.

Assumptions:

- Existing tests already capture the intended command behavior closely enough to guard the refactor.
- No external user depends on the private helper function names currently defined inside the command modules.
- Shared helpers should remain internal to the CLI package and not become top-level public SDK exports.

Acceptance Criteria:

- [ ] A new shared helper module exists under `harnessiq/cli/` for the repeated agent-command helper logic.
- [ ] The duplicated helper implementations are removed from the touched CLI modules and replaced with shared imports.
- [ ] Public command names, flags, and returned JSON payload shapes remain unchanged.
- [ ] Existing CLI tests covering the touched commands pass without requiring fixture rewrites for changed behavior.
- [ ] The new shared helper module has direct unit or usage coverage through the updated CLI tests.

Verification Steps:

- Static analysis: run `python -m compileall harnessiq tests`.
- Type checking: no configured type checker; verify the refactor keeps existing annotations coherent and does not introduce new untyped public helper signatures where obvious annotations are practical.
- Unit tests: run `.venv\Scripts\pytest.exe -q tests/test_linkedin_cli.py tests/test_instagram_cli.py tests/test_prospecting_cli.py tests/test_exa_outreach_cli.py tests/test_ledger_cli.py`.
- Integration and contract tests: run `.venv\Scripts\pytest.exe -q tests/test_sdk_package.py` if unaffected by unrelated repo-root discovery problems; otherwise note the current baseline blocker and run the touched CLI suites as the integration signal.
- Smoke/manual verification: run `.venv\Scripts\python.exe -m harnessiq.cli --help` and one representative JSON-emitting command path that does not require external credentials.

Dependencies:

- None.

Drift Guard:

This ticket must stay focused on deduplicating helper logic and stabilizing CLI implementation structure. It must not redesign command semantics, rename subcommands, change memory-store formats, or expand runtime capabilities unrelated to the helper extraction.
