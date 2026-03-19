Title: Add CLI ledger inspection/export/report commands and update the file index

Intent:
Expose the new audit ledger to users without requiring custom Python code and document the architectural addition in the repo index.

Scope:
Add top-level CLI commands for reading/exporting/reporting the JSONL ledger baseline and update `artifacts/file_index.md`.

Relevant Files:
- `harnessiq/cli/main.py`: register new ledger command group(s).
- `harnessiq/cli/`: add ledger command implementation module(s).
- `harnessiq/utils/`: add query/export/report helpers used by the CLI.
- `artifacts/file_index.md`: describe the ledger layer and where its code lives.
- CLI tests under `tests/`: cover parser registration and command behavior.

Approach:
Build the CLI directly on top of the JSONL ledger, supporting basic filtering by agent/time window and output formats that match the current repo’s CLI style. Keep export/report logic deterministic and dependency-light.

Assumptions:
- Local JSONL is the source of truth for the baseline CLI.
- CSV/JSON/JSONL/Markdown are sufficient baseline formats for this task.

Acceptance Criteria:
- [ ] The CLI exposes ledger/log/export/report commands.
- [ ] Commands read from the default ledger path and optionally support an override path.
- [ ] Export supports at least JSON, JSONL, CSV, and Markdown output.
- [ ] Report provides a cross-agent summary derived from ledger entries.
- [ ] `artifacts/file_index.md` documents the new ledger architecture accurately.

Verification Steps:
- Run focused CLI tests for parser registration and command outputs.
- Run package smoke tests if the new CLI surface affects import/package behavior.

Dependencies:
- Ticket 1.
- Ticket 2.

Drift Guard:
Do not introduce global remote connection management or external sink configuration here. This ticket is only the local query/export/report layer on top of the baseline JSONL ledger plus the architecture index update.
