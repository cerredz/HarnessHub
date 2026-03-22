Title: Restore ExaOutreach run storage and CLI compatibility on main
Issue URL: https://github.com/cerredz/HarnessHub/issues/199

Intent:
Fix the broken ExaOutreach execution path on refreshed `main` so the outreach harness can persist lead/email activity deterministically again, search-only mode records the expected run metadata, and the CLI `outreach run` command emits JSON robustly in both real runs and mocked test scenarios.

Scope:
This ticket updates the ExaOutreach storage contract and runtime wiring on `main`, plus the narrow CLI JSON serialization path exercised by the outreach CLI tests. It does not change external Exa/xAI credential behavior, alter the broader BaseAgent policy of swallowing tool exceptions into tool results, or redesign the outreach prompt/tool surface beyond what is required to restore the documented run-storage behavior.

Relevant Files:
- `harnessiq/shared/exa_outreach.py`: align the storage backend implementation and run-file shape with the behavior expected by the current outreach harness and tests.
- `harnessiq/agents/exa_outreach/agent.py`: make the agent use the restored storage contract consistently for prepare, dedupe checks, and deterministic event logging.
- `harnessiq/cli/exa_outreach/commands.py`: ensure the emitted run summary payload is JSON-safe even when the agent object is mocked in tests.
- `tests/test_exa_outreach_agent.py`: verify restored lead/email logging, search-only metadata, and run reconstruction behavior.
- `tests/test_exa_outreach_cli.py`: verify `outreach run` remains machine-readable and does not break on mocked agent attributes.

Approach:
Use the smallest coherent fix that restores `main` behavior without dragging in unrelated refactors from the dirty feature branch. The outreach harness and shared outreach storage module currently disagree about the backend protocol and run-file schema. The implementation should re-establish one authoritative contract across those modules and keep `ExaOutreachMemoryStore.read_run()` compatible with the files written by the default backend. The CLI should avoid assuming `agent.last_run_id` is already JSON-serializable; it should normalize the value before emitting the response payload. Tests should assert on persisted run artifacts and output payloads rather than terminal status alone.

Assumptions:
- Refreshed `main` is the intended implementation baseline.
- The broken behavior is local to the outreach runtime/CLI contract; no external API behavior needs to change to satisfy this ticket.
- Search-only behavior and the `metadata.search_only` run-file shape currently encoded in the tests represent the desired public contract for `main`.

Acceptance Criteria:
- [ ] ExaOutreach internal tool handlers no longer raise `AttributeError` against the default filesystem storage backend on `main`.
- [ ] `prepare()` writes run files whose shape matches the outreach tests, including `metadata.search_only` for both normal and search-only runs.
- [ ] Search-only outreach runs log discovered leads into the persisted run file and `ExaOutreachMemoryStore.read_run()` reconstructs them correctly.
- [ ] `harnessiq outreach run` emits valid JSON even when the injected/mock agent exposes non-JSON-native attributes.
- [ ] `tests/test_exa_outreach_agent.py` passes on refreshed `main`.
- [ ] `tests/test_exa_outreach_cli.py` passes on refreshed `main`.

Verification Steps:
1. Run the configured linter/static-analysis step for the changed Python files if one exists; otherwise document that no project linter is configured and perform manual style review.
2. Run the configured type checker for the changed files if one exists; otherwise document that no project type checker is configured and confirm any new code remains fully annotated/idiomatic.
3. Run `python -m pytest tests/test_exa_outreach_agent.py tests/test_exa_outreach_cli.py -q`.
4. Run a narrow smoke verification that constructs an `ExaOutreachAgent` on a temporary memory path, executes one deterministic lead-log path, and confirms the `runs/run_1.json` artifact contains the expected data.
5. If broader nearby regressions appear during implementation, rerun the smallest adjacent suite necessary to prove the fix did not break shared behavior.

Dependencies:
- None.

Drift Guard:
This ticket must not import the entire dirty feature-branch outreach refactor into `main`. It is limited to restoring the outreach harness, its shared storage contract, and the narrow CLI JSON payload behavior required for the observed failures. It must not redesign BaseAgent error handling, alter unrelated agents, or attempt to solve upstream provider authorization failures.


## Quality Pipeline Results
Stage 1 - Static Analysis

- No project linter or standalone static-analysis tool is configured in `pyproject.toml`.
- Manually reviewed the changed files for import hygiene, unused helpers, and local consistency with existing module style.
- Result: pass.

Stage 2 - Type Checking

- No project type checker is configured in `pyproject.toml`.
- Verified the fix preserves existing typing patterns and does not introduce untyped new interfaces.
- Result: pass.

Stage 3 - Unit Tests

- Ran `C:\\Users\\Michael Cerreto\\HarnessHub\\.venv\\Scripts\\python.exe -m pytest tests/test_exa_outreach_agent.py tests/test_exa_outreach_cli.py -q`
- Observed: `63 passed in 1.32s`
- Result: pass.

Stage 4 - Integration & Contract Tests

- Ran `C:\\Users\\Michael Cerreto\\HarnessHub\\.venv\\Scripts\\python.exe -m pytest tests/test_exa_outreach_shared.py -q`
- Observed: `38 passed in 0.31s`
- This validates the outreach shared memory contract and run reconstruction behavior adjacent to the modified runtime path.
- Result: pass.

Stage 5 - Smoke & Manual Verification

- Ran an inline smoke script that:
  - constructed `ExaOutreachAgent(search_only=True)` with a temporary memory path,
  - executed one model turn with `exa_outreach.check_contacted` and `exa_outreach.log_lead`,
  - loaded `runs/run_1.json` from disk,
  - asserted the run finished with `status="completed"`,
  - confirmed `metadata` contained `{"query": "B2B SaaS founders in New York", "search_only": true}`,
  - confirmed the event log contained one `lead` event for `https://example.com/prospect/alice`.
- Result: pass.


## Post-Critique Changes
Self-critique findings:

- The first implementation fixed behavior but left the shared outreach module description stale. After the backport, the module no longer defines its own storage backend implementation; it re-exports the generic run-storage backend. I updated the module docstring to make that contract explicit and reduce future drift.
- The first CLI change normalized `ledger_run_id` for JSON safety but still passed raw `_current_run_id` through to the human-readable summary path. I normalized `run_id` as well so the CLI is consistent if tests or callers inject a non-string mock value.

Post-critique changes made:

- Updated `harnessiq/shared/exa_outreach.py` module documentation to describe the re-exported generic storage backend.
- Normalized `run_id` to `str` in `harnessiq/cli/exa_outreach/commands.py` before summary rendering.
- Re-ran the targeted outreach test suites to confirm no regressions:
  - `63 passed` in `tests/test_exa_outreach_agent.py tests/test_exa_outreach_cli.py`
  - `38 passed` in `tests/test_exa_outreach_shared.py`

