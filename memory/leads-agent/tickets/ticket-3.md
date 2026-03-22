Title: Add shared leads models, memory store, and pluggable storage contracts
Intent: Define the durable leads-agent domain model so company context, multi-ICP progress, per-ICP search logs, summarized history, dedupe keys, and saved leads all persist deterministically outside the transcript.
Scope:
- Add the shared leads dataclasses for run config, run state, ICPs, searches, summaries, and leads.
- Add a file-backed leads memory store for per-ICP durable search state.
- Add a pluggable leads storage backend contract with a default filesystem implementation for saved-lead persistence and dedupe.
- Register the new shared module in the repository file index.
- Do not implement the concrete leads agent loop, provider composition, or CLI behavior in this ticket.
Relevant Files:
- `harnessiq/shared/leads.py`: canonical leads-agent domain models, memory-store helpers, and default storage backend.
- `tests/test_leads_shared.py`: coverage for shared models, per-ICP persistence, search compaction, and save-backend dedupe.
- `artifacts/file_index.md`: repository structure index updated for the new shared module and test surface.
Approach: Split durable state into two explicit layers. `LeadsMemoryStore` owns run config/state plus per-ICP search logs, summaries, and saved dedupe keys so the future agent can rotate ICP context without losing deterministic memory. `LeadsStorageBackend` owns cross-run lead persistence and dedupe, with `FileSystemLeadsStorageBackend` reusing the generic run-storage layer for run-level audit while persisting normalized lead entries in a dedicated file.
Assumptions:
- Search history must remain per-ICP and durable because transcript pruning is now deterministic.
- Cross-run dedupe belongs in storage, not in transcript-only memory or model reasoning.
- A default filesystem backend is sufficient for v1 as long as the storage contract is pluggable.
Acceptance Criteria:
- [ ] A shared leads module exists with typed records for run config/state, ICPs, searches, summaries, and leads.
- [ ] A leads memory store can prepare the memory layout, persist per-ICP search state, and replace older search blocks with summaries.
- [ ] A pluggable storage backend contract exists for saved leads, with a default filesystem backend that supports dedupe and lead listing.
- [ ] Shared tests verify round trips, dedupe behavior, per-ICP search persistence, and summary replacement behavior.
Verification Steps:
- Run `python -m py_compile harnessiq/shared/leads.py tests/test_leads_shared.py`.
- Run `python -m pytest tests/test_leads_shared.py`.
- Run `python -m pytest tests/test_exa_outreach_shared.py`.
- Smoke-check that summary compaction preserves the search tail and next search sequence, and that duplicate leads are rejected across runs.
Dependencies: Ticket 2 is available and informs the transcript-pruning requirements this durable state will support.
Drift Guard: This ticket must not add model prompting, provider-tool selection logic, or CLI UX. It is strictly the shared storage and memory layer for the later leads harness.
