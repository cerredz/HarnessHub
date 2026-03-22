Title: Add shared leads models, memory store, and pluggable storage contracts

Issue URL: https://github.com/cerredz/HarnessHub/issues/151

Intent:
Define the durable domain model for the leads agent so multi-ICP runs, per-ICP search logs, dedupe state, saved leads, and run metadata are persisted deterministically outside the transcript and can survive context pruning.

Scope:
This ticket adds the shared leads dataclasses, a file-backed memory store, and the leads-specific pluggable storage contract/default backend.
This ticket does not add the Apollo provider, the concrete leads agent loop, or CLI/docs.

Relevant Files:
- `harnessiq/shared/leads.py`: define leads-agent domain models, memory-store helpers, configuration objects, and default file-backed storage.
- `harnessiq/utils/run_storage.py`: extend or reuse generic run storage only if needed for leads-specific events without breaking existing consumers.
- `tests/test_leads_shared.py`: add focused coverage for leads shared types, dedupe lookup, per-ICP search persistence, and storage backend behavior.
- `artifacts/file_index.md`: register the new shared module if added.

Approach:
Follow the successful `shared.exa_outreach` pattern, but adapt it to this use case instead of forcing the leads agent into outreach-specific abstractions. The shared model should represent:

- company background and run configuration
- ICP definitions and per-ICP progress/state
- search log entries and summarized search history
- discovered/saved lead records with deterministic dedupe keys
- a pluggable save/storage backend for durable lead persistence

Keep search history durable and per-ICP so the leads agent can rotate ICP context in and out of parameter sections while preserving what has already been tried.

Assumptions:
- The user wants a default filesystem-backed persistence layer plus a pluggable storage interface for future non-filesystem backends.
- Dedupe must live in deterministic storage/memory, not in transcript-only state.
- The default backend should be able to answer “have we already seen this person?” and “what searches have been run for this ICP?” efficiently enough for test and SDK usage.

Acceptance Criteria:
- [ ] A new shared leads module exists with typed records for ICPs, leads, searches, summaries, and run configuration.
- [ ] A leads memory store can prepare the memory directory structure and read/write per-ICP durable state.
- [ ] A pluggable storage backend contract exists for saving leads, with a default filesystem implementation.
- [ ] Shared tests verify round trips, dedupe behavior, per-ICP search history persistence, and summary replacement behavior.

Verification Steps:
- Static analysis: run the linter against `harnessiq/shared/leads.py` and any touched storage helpers.
- Type checking: run the type checker or validate annotations/import safety for the new shared module.
- Unit tests: run `pytest tests/test_leads_shared.py`.
- Integration and contract tests: run shared storage tests alongside any existing run-storage coverage affected by the change.
- Smoke verification: create a temporary leads memory directory, write per-ICP searches/leads, summarize a search block, and confirm reload behavior.

Dependencies:
- Ticket 2 if the shared model needs to align with the new pruning config names; otherwise independent.

Drift Guard:
This ticket must not implement model prompting, provider-tool selection, or CLI behavior. It is strictly the durable data/storage layer the concrete leads harness will depend on.
