Title: Restore ExaOutreach run storage and CLI compatibility on main
Issue URL: https://github.com/cerredz/HarnessHub/issues/199
PR URL: https://github.com/cerredz/HarnessHub/pull/201

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
