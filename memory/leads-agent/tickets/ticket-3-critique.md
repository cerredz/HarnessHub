# Ticket 3 Critique

## Findings
- A single persistence mechanism was not enough for this agent design: per-ICP search memory and cross-run lead saving have different lifecycles and would have created awkward coupling if they shared one flat store.
- Search summarization needed more than a free-form note. Without sequence tracking and tail reconstruction, the later harness would not be able to resume numbering searches or rebuild a compact prompt window deterministically.

## Improvements Applied
- Split the durable state into `LeadsMemoryStore` for run config plus per-ICP progress, and `LeadsStorageBackend` for saved-lead persistence and cross-run dedupe.
- Added `LeadSearchSummary.last_sequence`, `LeadsMemoryStore.next_search_sequence()`, and `LeadsMemoryStore.read_search_context()` so later harness code can prune history without losing deterministic sequencing.
- Reused the generic `FileSystemStorageBackend` internally for run-level audit rather than forking a second run-log implementation.
