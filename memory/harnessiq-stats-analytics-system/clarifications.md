No blocking clarification questions remain after Phase 1.

Implementation assumptions carried forward:

1. Implement the full usable surface from the design doc now:
   - Phase 1 foundation items.
   - Phase 2 snapshot/CLI surface items.
   - Actual-token fields remain nullable because current provider adapters do not expose provider-reported token usage into the runtime.

2. `session_id` continuity will be auto-carried by runtime lookup against the ledger when an explicit session is not provided and the latest run for the same `instance_id` ended in `paused` or `max_cycles_reached`.

3. Stats snapshots will follow the resolved ledger location so the read models stay colocated with the authoritative `runs.jsonl`, even if the effective root is not the repo root.

4. GitHub issue creation will be attempted after ticket drafting. If the local `gh` workflow is unavailable or unauthenticated, the markdown ticket set remains the authoritative planning artifact and the failure will be surfaced explicitly.
