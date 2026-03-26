Title: Add the built-in MongoDB output sink

Issue URL: https://github.com/cerredz/HarnessHub/issues/274

Intent:
Provide a first-class MongoDB output sink so HarnessIQ users can export completed agent ledger entries to MongoDB through the same programmatic, per-run, and global connection surfaces used by the existing built-in sinks.

Scope:
- Add a MongoDB delivery client and a built-in `MongoDBSink`.
- Register `mongodb` in the sink factory, CLI `connect` surface, and public compatibility exports.
- Add or update tests covering sink construction, client delegation, CLI connection flow, and sink listing.
- Update sink documentation and regenerate generated repository docs impacted by the new sink/CLI inventory.
- Add any required runtime dependency for MongoDB support.

Scope exclusions:
- No changes to agent run logic, transcript behavior, or harness manifests.
- No MongoDB-specific credential manager, schema migration layer, or upsert/deduplication workflow.
- No changes to unrelated provider packages or non-sink CLI families.

Relevant Files:
- `harnessiq/providers/output_sink_clients.py`: add the MongoDB delivery client abstraction.
- `harnessiq/providers/output_sinks.py`: re-export the MongoDB client through the provider sink facade.
- `harnessiq/providers/__init__.py`: expose the MongoDB client from the top-level provider package.
- `harnessiq/utils/ledger_sinks.py`: add `MongoDBSink`, sink factory registration, and any shared document-rendering helpers.
- `harnessiq/utils/ledger.py`: re-export `MongoDBSink` through the ledger compatibility facade.
- `harnessiq/utils/__init__.py`: expose `MongoDBSink` through the public utilities package.
- `harnessiq/cli/ledger/commands.py`: register `harnessiq connect mongodb` and its config options.
- `tests/test_output_sinks.py`: cover the new sink behavior and construction.
- `tests/test_ledger_cli.py`: cover CLI parser/connection flow for MongoDB.
- `docs/output-sinks.md`: document the new sink and connection usage.
- `pyproject.toml`: add the MongoDB runtime dependency if needed.
- `requirements.txt`: keep the lightweight dependency mirror aligned if needed.
- `README.md`: regenerated inventory output.
- `artifacts/file_index.md`: regenerated inventory output.
- `artifacts/commands.md`: regenerated CLI inventory output.

Approach:
Implement MongoDB as a provider-backed sink client plus a thin `MongoDBSink` dataclass, following the same separation used by `SupabaseSink`, `LinearSink`, and `GoogleSheetsSink`. Default document insertion will persist one full `LedgerEntry.as_dict()` payload per run. When `explode_field` is set to a list-valued ledger path, the sink will insert one document per record, carrying the run envelope plus the exploded record, mirroring the existing “explode” pattern without altering the base ledger model. CLI registration will add a dedicated `connect mongodb` command that writes a normal `SinkConnection`, and the generated docs will be refreshed from source.

Assumptions:
- The sink name should be `mongodb`.
- Standard MongoDB connectivity via a connection URI is the expected user interface.
- `pymongo` is an acceptable runtime dependency for this repository.
- Optional exploded insert behavior is desirable because other sinks already support record-level fan-out for list outputs.
- Generated docs should be updated by rerunning `python scripts/sync_repo_docs.py` rather than hand-editing generated artifacts.

Acceptance Criteria:
- [ ] `list_output_sink_types()` includes `mongodb`.
- [ ] `build_output_sink("mongodb", ...)` returns a `MongoDBSink` with the expected config fields.
- [ ] `MongoDBSink.on_run_complete()` inserts a full ledger-entry document by default through a dedicated MongoDB client abstraction.
- [ ] `MongoDBSink` supports optional `explode_field` fan-out for list-valued ledger outputs.
- [ ] `harnessiq connect mongodb --connection-uri ... --database ... --collection ...` is registered and round-trips through the existing connection store.
- [ ] Public provider and utility compatibility exports expose the new MongoDB sink/client consistently with existing sink surfaces.
- [ ] Sink docs and generated inventory artifacts mention MongoDB.
- [ ] Automated tests cover the added behavior.

Verification Steps:
1. Run the targeted sink and ledger CLI test modules covering the changed surface.
2. Run the generated-doc sync script and confirm the repo docs update cleanly.
3. Run a parser/connection smoke check for `harnessiq connect mongodb`.
4. Review the changed files for contract consistency with the existing sink architecture.

Dependencies:
- None.

Drift Guard:
This ticket must stay inside the output-sink subsystem. It must not introduce MongoDB as a general provider family, must not add agent-facing tool calls, and must not redesign ledger entry modeling. The goal is a new post-run export target that behaves like the existing sinks, not a broader database abstraction effort.
