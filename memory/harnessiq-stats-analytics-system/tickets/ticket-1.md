Title: Add runtime session and stats metadata to terminal ledger entries
Issue URL: https://github.com/cerredz/HarnessHub/issues/376

Intent:
Implement the write-side foundation for the stats system so every terminal run emits a normalized, immutable `metadata["stats"]` block. This creates the source-of-truth payload that every later projection and CLI command depends on.

Scope:
This ticket adds `session_id` ownership to the runtime, collects per-run counters needed by the design doc, writes the normalized stats block into ledger metadata, and ensures the shared terminal run path can resolve or carry session continuity across resume cases.
This ticket does not add snapshot files, projector rebuild logic, or any `harnessiq stats` CLI commands.

Relevant Files:
- [harnessiq/shared/agents.py](C:/Users/422mi/HarnessHub/harnessiq/shared/agents.py): extend `AgentRuntimeConfig` with session continuity fields needed by runtime-owned `session_id`.
- [harnessiq/agents/base/agent.py](C:/Users/422mi/HarnessHub/harnessiq/agents/base/agent.py): initialize runtime stats/session state at run start and ensure custom loops can share it.
- [harnessiq/agents/base/agent_helpers.py](C:/Users/422mi/HarnessHub/harnessiq/agents/base/agent_helpers.py): build the normalized `metadata["stats"]` block, collect tool counters, and reuse ledger-based session lookup.
- [harnessiq/agents/leads/agent.py](C:/Users/422mi/HarnessHub/harnessiq/agents/leads/agent.py): align custom loop with shared session/stats initialization.
- [harnessiq/agents/instagram/agent.py](C:/Users/422mi/HarnessHub/harnessiq/agents/instagram/agent.py): align custom loop with shared session/stats initialization.
- [harnessiq/providers/output_sink_metadata.py](C:/Users/422mi/HarnessHub/harnessiq/providers/output_sink_metadata.py): normalize provider/model extraction for stats payload consumption if needed.
- [tests/test_agents_base.py](C:/Users/422mi/HarnessHub/tests/test_agents_base.py): add runtime coverage for stats metadata emission and session continuity.
- New stats-focused runtime tests if needed, likely under `tests/test_stats_projector.py` later, but runtime assertions should live here first.

Approach:
Add an explicit runtime initialization step that assigns a fresh run ID, resolves `session_id`, and resets per-run stats counters before the loop starts. The shared tool execution path already centralizes most tool activity, so incrementing `tool_calls`, `distinct_tools`, and `tool_call_breakdown` there avoids transcript re-parsing and automatically covers custom agent loops that use the same helpers.

Build the `metadata["stats"]` payload inside `_build_ledger_metadata()` so the ledger entry stays the only authoritative write. Populate `repo_id` from the resolved repo root name, `instance_id` from the existing instance store, `session_id` from runtime state, provider/model data from existing metadata extraction, estimated token totals from the accumulated request estimate, actual-token fields as nullable, and timing/counter fields from terminal run state.

For session continuity, prefer an explicit runtime-config session override when present. Otherwise, inspect the most recent ledger entries for the same `instance_id` and reuse the latest `session_id` when the previous run ended in `paused` or `max_cycles_reached`; otherwise generate a new `sess_...` identifier. Keep this logic inside the runtime layer so direct SDK callers and CLI-driven callers behave the same way.

Assumptions:
- Provider adapters do not currently expose provider-reported token usage into `AgentModelResponse`, so actual-token fields remain `null` and `source` remains `"estimated"` for now.
- `instance_id` from `AgentInstanceStore` is the correct identity grouping key for resume lookup.
- Reusing session continuity for the latest same-instance paused/max-cycle run is acceptable even though platform snapshots do not yet persist `session_id`.

Acceptance Criteria:
- [ ] Every terminal ledger entry emitted by the generic runtime includes a `metadata["stats"]` object with the schema defined by the design doc.
- [ ] `stats.version` is `1`, `stats.session_id` is present, and `stats.instance_id` matches the resolved instance record.
- [ ] Tool counters include total call count, distinct-tool count, and a deterministic per-tool breakdown.
- [ ] The runtime reuses `session_id` for resumed same-instance runs when the latest matching ledger entry ended in `paused` or `max_cycles_reached`.
- [ ] Fresh same-instance runs that do not continue a paused/max-cycle session get a new `session_id`.
- [ ] Runtime stats emission works for both `BaseAgent` and the custom leads/instagram loop paths.

Verification Steps:
- Static analysis: run the repository’s configured Python quality tooling against changed runtime/test files; if no linter is configured, perform manual style verification.
- Type checking: run any configured type checker if present; otherwise ensure new runtime helpers are fully annotated.
- Unit tests: run targeted runtime tests covering base-agent completion, pause, error, and session carry-forward behavior.
- Integration tests: run the broader agent/runtime suite that exercises custom loops and default ledger sink behavior.
- Smoke verification: execute a small local harness run and inspect the emitted ledger line to confirm the `metadata["stats"]` block is written exactly once at run termination.

Dependencies:
- None.

Drift Guard:
This ticket must not add snapshot files, projector logic, or user-facing stats CLI commands. It is strictly the runtime write-side foundation that makes later read models possible. Do not mix in cost estimation, live/in-progress stats, or provider-specific actual-token plumbing beyond nullable schema placeholders.
