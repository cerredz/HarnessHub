Title: Add provider-backed sinks for Notion, Confluence, Supabase, and Linear

Intent:
Support durable external-system exports for structured databases, internal knowledge bases, and task-tracking systems using provider-side transport helpers.

Scope:
Implement provider-backed sinks plus the minimal client helpers needed to create Notion pages, Confluence pages, Supabase rows, and Linear issues.

Relevant Files:
- `harnessiq/providers/output_sinks.py`: provider-side clients and model metadata extraction.
- `harnessiq/utils/ledger.py`: sink adapters that format ledger entries for each provider.
- `tests/test_output_sinks.py`: verify sink-to-client delegation and Linear explode behavior.

Approach:
Keep formatting and sink orchestration in the ledger layer while moving remote transport/auth concerns into provider helpers. This mirrors the repo’s broader provider/client separation without introducing a full operation catalog for each new sink target.

Assumptions:
- Minimal write-only clients are sufficient for the first version of these sinks.
- Linear defaults to one issue per run unless an explode field is configured.

Acceptance Criteria:
- [ ] Notion sink creates a page in a configured database.
- [ ] Confluence sink creates a page in a configured space.
- [ ] Supabase sink inserts a ledger row into a configured table.
- [ ] Linear sink creates issues from runs and supports exploded output records.

Verification Steps:
- Run focused sink tests that assert each sink delegates to the expected provider client.

Dependencies:
- Ticket 1.
- Ticket 4.

Drift Guard:
Do not implement bi-directional sync, read/query behavior, or full provider operation SDKs here. These provider helpers exist only to support the write-only sink layer.
