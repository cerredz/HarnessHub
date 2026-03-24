## Self-Critique

Primary review finding:
- If transcript compaction removed Instagram tool results without any other change, output sinks would still receive nothing useful because the Instagram agent did not previously override `build_ledger_outputs()` even though the manifest advertises `emails`, `leads`, and `search_history`.

Improvement applied:
- Added `InstagramKeywordDiscoveryAgent.build_ledger_outputs()` to export `emails`, `leads`, and `search_history` directly from durable memory at run completion.
- Added a regression test to confirm those outputs are built from persisted Instagram memory, not from transcript state.

Residual risk:
- Failed attempted keywords are remembered for the active run but are not persisted durably across runs. That matches the narrow scope of this token-cost change and avoids a search-history schema migration.
