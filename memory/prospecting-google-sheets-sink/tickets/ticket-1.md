Title: Add a built-in Google Sheets output sink for ledger exports

Intent: Provide a repo-native sink that can write completed run outputs into a Google Sheet, with prospecting leads as the primary target use case.

Scope:
- Add a provider client for Google Sheets append/update behavior.
- Add a built-in sink class and register it in the ledger sink registry.
- Expose the sink through public utility exports and the ledger CLI connect surface.
- Add tests and docs.
- Do not change in-loop tool behavior for any agent.

Relevant Files:
- `harnessiq/providers/output_sink_clients.py`: add a Google Sheets API client.
- `harnessiq/providers/output_sinks.py`: re-export the client facade.
- `harnessiq/utils/ledger_sinks.py`: add the sink implementation and builder registration.
- `harnessiq/utils/ledger.py`: re-export the sink.
- `harnessiq/utils/__init__.py`: re-export the sink.
- `harnessiq/cli/ledger/commands.py`: add a `connect google_sheets` path.
- `tests/test_output_sinks.py`: add sink/client coverage.
- `docs/output-sinks.md`: document the new sink.

Approach:
- Follow the existing sink/client split already used for Notion/Linear/Supabase.
- Use a synchronous Sheets client that refreshes OAuth access tokens from client id/client secret/refresh token and writes rows through the Sheets REST API.
- Keep row flattening deterministic and sink-side; for prospecting runs, explode `outputs.qualified_leads` into rows.

Assumptions:
- The sink target is Google Sheets.
- One worksheet tab identified by `sheet_name` is sufficient for the initial implementation.

Acceptance Criteria:
- [ ] `google_sheets` is available through `list_output_sink_types()`.
- [ ] A Google Sheets sink can be built from direct config and from a persisted connection.
- [ ] Prospecting ledger outputs can be exploded into per-lead rows.
- [ ] Public exports and docs include the sink.
- [ ] Tests cover sink construction and row delivery behavior.

Verification Steps:
- Run focused sink tests.
- Verify the ledger CLI can construct the sink.
- Inspect docs/export surfaces for the new sink.

Dependencies: None.

Drift Guard:
- This ticket must not add Sheets as an in-loop tool, must not change existing sink semantics, and must not redesign the ledger framework.
