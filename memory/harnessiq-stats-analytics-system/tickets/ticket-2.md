Title: Add stats projector snapshots and rebuild/export infrastructure
Issue URL: https://github.com/cerredz/HarnessHub/issues/377

Intent:
Turn the append-only ledger into efficient read models by projecting terminal-run stats into reconstructible snapshot files. This ticket creates the storage contract and the single allowed write path for all stats materialization.

Scope:
This ticket adds the `StatsProjector`, snapshot schemas for agents/instances/sessions/daily views, atomic writes, incremental post-ledger projection, and full rebuild/export support over the ledger.
This ticket does not add user-facing `harnessiq stats` CLI command parsing or presentation formatting beyond utility surfaces needed by the future CLI.

Relevant Files:
- New [harnessiq/utils/stats_projector.py](C:/Users/422mi/HarnessHub/harnessiq/utils/stats_projector.py): projector implementation, snapshot schema assembly, rebuild flow, and atomic writes.
- [harnessiq/agents/base/agent_helpers.py](C:/Users/422mi/HarnessHub/harnessiq/agents/base/agent_helpers.py): invoke the projector after ledger append and swallow projector failures.
- [harnessiq/utils/ledger_exports.py](C:/Users/422mi/HarnessHub/harnessiq/utils/ledger_exports.py): add any shared helpers needed to stream or flatten per-run stats for export.
- [harnessiq/utils/__init__.py](C:/Users/422mi/HarnessHub/harnessiq/utils/__init__.py): export the new projector/read helpers.
- New tests under [tests/test_stats_projector.py](C:/Users/422mi/HarnessHub/tests/test_stats_projector.py): verify projector math, incremental-vs-rebuild equivalence, malformed-entry skipping, and export behavior.
- Existing runtime/CLI tests as needed for post-write integration.

Approach:
Implement `StatsProjector` as the sole writer to `.harnessiq/stats/`, with a small path-resolution helper that colocates snapshot files with the resolved ledger. The projector should accept either a single `LedgerEntry` for incremental application or a streamed list of entries for rebuild. It should ignore entries missing `metadata["stats"]` or containing an unsupported stats schema version, while counting and reporting skips during rebuild.

Maintain four in-memory dictionaries keyed exactly as the design doc specifies: agent name, instance ID, session ID, and UTC date. Derive every aggregate from the immutable per-run stats block rather than from other snapshots. Keep estimated and actual token sums separate, and represent actual totals as `null` when no contributing runs had actual usage.

Expose utility functions needed by the later CLI:
- load snapshots safely
- rebuild snapshots from a ledger path
- export nested JSON snapshot payloads
- export flat per-run CSV derived from ledger stats

The runtime integration point should remain below ledger append success. If projector application throws, log at error level and continue without failing the agent caller.

Assumptions:
- Ticket 1 has already established a stable stats block on each terminal ledger entry.
- Snapshot location should be derived from the resolved ledger path so the read models follow the authoritative ledger.
- Daily aggregation buckets by UTC date of `run_started_at`, matching the design doc’s snapshot examples and keeping the metric deterministic.

Acceptance Criteria:
- [ ] A new `StatsProjector` can incrementally apply one valid ledger entry and update all four snapshot datasets.
- [ ] A full rebuild from `runs.jsonl` produces the same snapshot outputs as applying the same entries incrementally in order.
- [ ] Snapshot files are written atomically via temporary-file replacement.
- [ ] Legacy or malformed ledger entries without a valid stats block are skipped without breaking rebuild.
- [ ] The runtime invokes the projector only after ledger append succeeds and treats projector errors as non-fatal.
- [ ] Export helpers can emit a nested JSON snapshot payload and a flat per-run CSV derived from ledger stats.

Verification Steps:
- Static analysis: run repository Python quality tooling or manual style verification over the new utility module and tests.
- Type checking: run any configured type checker if present; otherwise ensure projector/export helpers are fully annotated.
- Unit tests: run new projector tests covering aggregation formulas, token-source separation, session duration logic, and malformed-entry handling.
- Integration tests: run runtime tests that verify post-ledger projector invocation and rebuild equivalence from realistic ledger lines.
- Smoke verification: create a temporary ledger with multiple resumed runs, rebuild snapshots, and inspect the generated `agents.json`, `instances.json`, `sessions.json`, and `daily.json`.

Dependencies:
- Ticket 1.

Drift Guard:
This ticket must not add the public `stats` CLI command family or presentation-layer formatting. Keep the implementation centered on projection, storage, rebuild, and export primitives. Do not introduce a second stats write path, mutable ledger backfills, or any source of truth other than `runs.jsonl`.
