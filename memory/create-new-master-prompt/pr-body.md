Title: Add the `cognitive_multiplexer` bundled master prompt
Issue URL: https://github.com/cerredz/HarnessHub/issues/305
Intent: Add the user-provided cognitive multiplexer master prompt to the bundled prompt catalog so it can be retrieved through the SDK, CLI, and prompt session injection workflow like the existing curated prompts.
Scope: Create one new prompt JSON asset under `harnessiq/master_prompts/prompts/`, update the prompt catalog regression tests for the new bundled key, and write workflow artifacts under `memory/create-new-master-prompt/`. Do not refactor the prompt registry, session injection helpers, CLI wiring, or unrelated prompt assets.
Relevant Files:
- `harnessiq/master_prompts/prompts/cognitive_multiplexer.json`: new bundled prompt asset containing the exact user-provided prompt body with repository-standard metadata fields.
- `tests/test_master_prompts.py`: extend the expected prompt key set and add prompt-specific assertions for `cognitive_multiplexer`.
- `memory/create-new-master-prompt/internalization.md`: Phase 1 repository survey and task mapping.
- `memory/create-new-master-prompt/clarifications.md`: recorded assumption resolution for the inferred prompt metadata.
- `memory/create-new-master-prompt/tickets/index.md`: ticket index and later issue/PR bookkeeping.
- `memory/create-new-master-prompt/tickets/ticket-1.md`: this ticket definition.
Approach: Use the existing file-driven prompt registry exactly as designed by adding a single new JSON file to the prompts package. Preserve the provided prompt body verbatim in the `prompt` field, infer only the required catalog metadata, and update `tests/test_master_prompts.py` so the new asset is part of the expected prompt catalog and receives at least one direct content assertion validating the preserved persona text.
Assumptions:
- The inferred key `cognitive_multiplexer` is acceptable for the bundled catalog.
- The title `Cognitive Multiplexer` and a concise description are sufficient metadata wrappers around the exact prompt body.
- The provided prompt text is intended to be added verbatim rather than normalized into the repoâ€™s typical `Identity` heading format.
- Existing prompt catalog tooling should pick up the new file automatically without separate registration.
Acceptance Criteria:
- [ ] `MasterPromptRegistry().list()` includes `cognitive_multiplexer`.
- [ ] `harnessiq/master_prompts/prompts/cognitive_multiplexer.json` contains non-empty `title`, `description`, and `prompt` fields.
- [ ] The `prompt` field preserves the provided prompt body exactly apart from JSON escaping.
- [ ] `tests/test_master_prompts.py` includes `cognitive_multiplexer` in the expected bundled prompt key set.
- [ ] Focused prompt tests pass for the updated catalog.
- [ ] Prompt registry and CLI surfaces continue to load the bundled catalog successfully after the addition.
Verification Steps:
- Run `python -m pytest tests/test_master_prompts.py tests/test_master_prompts_cli.py tests/test_master_prompt_session_injection.py`.
- Run `python -c "from harnessiq.master_prompts import get_prompt; prompt = get_prompt('cognitive_multiplexer'); print(prompt.title); print(prompt.prompt.splitlines()[0])"`.
- If prompt catalog docs are generated from repository structure, run the repoâ€™s docs verification command and confirm no prompt-related drift was introduced.
Dependencies: None.
Drift Guard: This ticket must stay additive. Do not refactor the prompt registry, do not rewrite existing prompt assets, do not normalize the user-provided prompt body into a different style, and do not mix unrelated dirty-worktree changes into the implementation branch.


## Quality Pipeline Results
## Stage 1 - Static Analysis

No repository linter or standalone static analysis tool is configured in [pyproject.toml](C:\Users\422mi\HarnessHub\.worktrees\issue-305\pyproject.toml) or [requirements.txt](C:\Users\422mi\HarnessHub\.worktrees\issue-305\requirements.txt). Verified by searching for `ruff`, `flake8`, `pylint`, `black`, and related tool names.

Result: No configured static-analysis step to run for this ticket.

## Stage 2 - Type Checking

No repository type checker is configured in [pyproject.toml](C:\Users\422mi\HarnessHub\.worktrees\issue-305\pyproject.toml) or [requirements.txt](C:\Users\422mi\HarnessHub\.worktrees\issue-305\requirements.txt). This ticket only adds a JSON prompt asset plus test expectations, so there is no new typed runtime Python surface beyond the updated tests.

Result: No configured type-checking step to run for this ticket.

## Stage 3 - Unit Tests

Command:

```powershell
python -m pytest tests/test_master_prompts.py
```

Observed result:

- `40 passed in 0.19s`

This validates the prompt registry, the bundled prompt catalog, and the direct prompt-specific assertions for `cognitive_multiplexer`.

## Stage 4 - Integration and Contract Tests

Command:

```powershell
python -m pytest tests/test_master_prompts.py tests/test_master_prompts_cli.py tests/test_master_prompt_session_injection.py
```

Observed result:

- `62 passed in 0.83s`

This verifies:

- Registry loading and public API retrieval for the expanded prompt catalog.
- CLI prompt commands continue to surface bundled prompt metadata correctly.
- Project-scoped session injection still renders active prompt overlays successfully with the updated catalog.

## Stage 5 - Smoke and Manual Verification

Command:

```powershell
python -c "from harnessiq.master_prompts import get_prompt; prompt = get_prompt('cognitive_multiplexer'); print(prompt.title); print(prompt.prompt.splitlines()[0]); print('â€”' in prompt.prompt)"
```

Observed output:

- `Cognitive Multiplexer`
- `Identity / Persona`
- `True`

This confirms the new bundled prompt resolves by key, exposes the expected title, preserves the `Identity / Persona` opening, and retains em-dash punctuation in the decoded prompt text.

## Additional Verification

Command:

```powershell
python scripts/sync_repo_docs.py --check
```

Observed result:

- Failed on `origin/main` baseline with `FileNotFoundError` for `harnessiq/providers/gcloud/operations.py`.

Assessment:

- This failure is unrelated to the prompt-catalog change in this ticket.
- The ticket did not modify `scripts/sync_repo_docs.py`, provider inventory code, or any `gcloud` provider files.
- I did not widen scope to fix this unrelated repository issue because it would violate the ticket's drift guard.


## Post-Critique Changes
## Self-Critique

Reviewing the change as if it came from another engineer surfaced one concrete weakness:

- The prompt-specific tests verified structure and general key phrases, but they did not explicitly guard the exact opening sentence that was most vulnerable to transcription and encoding drift during prompt-file generation.

Improvement applied:

- Added a direct regression assertion for `You are a cognitive multiplexer â€” an expert orchestration system`.
- Added a direct assertion for `Desired Persona Count (optional):` so the test suite also protects the tail end of the prompt's input contract instead of only the opening sections.

Why this improves the change:

- It makes the test suite more sensitive to prompt-fidelity regressions at both the start and end of the bundled prompt.
- It specifically protects against the encoding issue discovered during implementation, where punctuation could be degraded if the prompt is regenerated incorrectly.

