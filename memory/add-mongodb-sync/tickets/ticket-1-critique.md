## Post-Critique Changes

Self-review findings:
- The MongoDB client tests covered the multi-document `insert_many` path but not the single-document `insert_one` path.
- The sink tests verified explode behavior, but the default full-entry document shape deserved a direct assertion.
- The lazy-import error message for missing `pymongo` support could be more actionable.

Improvements implemented:
- Added a unit test that verifies `MongoDBClient` uses `insert_one` when only one document is supplied.
- Added a unit test that verifies `MongoDBSink` persists the default full ledger entry shape when `explode_field` is not configured.
- Updated the missing-driver runtime error to tell the user to install `pymongo` explicitly.
