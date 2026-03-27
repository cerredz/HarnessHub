Title: Add the `harnessiq stats` CLI command family
Issue URL: https://github.com/cerredz/HarnessHub/issues/378

Intent:
Expose the new stats system to users through a dedicated CLI surface that reads materialized snapshots for display and uses rebuild/export helpers when full recomputation is required.

Scope:
This ticket registers the `harnessiq stats` command family and implements `summary`, `agent`, `session`, `instance`, `rebuild`, and `export`, including `--format json` options where the design doc requires them.
This ticket does not change the legacy top-level `logs`, `export`, or `report` commands except for shared helper reuse if necessary.

Relevant Files:
- [harnessiq/cli/main.py](C:/Users/422mi/HarnessHub/harnessiq/cli/main.py): register the new top-level `stats` command family.
- New [harnessiq/cli/stats/__init__.py](C:/Users/422mi/HarnessHub/harnessiq/cli/stats/__init__.py): export command registration.
- New [harnessiq/cli/stats/commands.py](C:/Users/422mi/HarnessHub/harnessiq/cli/stats/commands.py): argparse wiring and command handlers.
- [harnessiq/cli/common.py](C:/Users/422mi/HarnessHub/harnessiq/cli/common.py): optional shared rendering helpers if needed.
- [harnessiq/utils/__init__.py](C:/Users/422mi/HarnessHub/harnessiq/utils/__init__.py): export any projector/snapshot helpers used by the CLI.
- [tests/test_ledger_cli.py](C:/Users/422mi/HarnessHub/tests/test_ledger_cli.py): extend CLI registration coverage if appropriate.
- New [tests/test_stats_cli.py](C:/Users/422mi/HarnessHub/tests/test_stats_cli.py): command parsing and output behavior for all stats subcommands.

Approach:
Add a dedicated `stats` parser subtree rather than overloading the existing ledger commands. Handlers should read snapshot files for `summary`, `agent`, `session`, and `instance`, while `rebuild` should invoke the projector over the ledger and report processed/skipped counts. `export` should route to the projector/export helpers created in Ticket 2.

Keep output conventions consistent with the rest of the CLI:
- text/table-like output for human-readable commands by default
- deterministic JSON for `--format json`
- stdout by default, with optional `--output` path for export

For empty or missing snapshot states, return sensible zero-state output rather than crashing. If snapshots are missing but a ledger exists, handlers may rebuild explicitly only where the design doc requires it; otherwise they should surface a clear message instructing the user to run `harnessiq stats rebuild`.

Assumptions:
- Tickets 1 and 2 are complete, so valid stats blocks and projector snapshots already exist.
- The CLI can use a simple deterministic text renderer instead of reproducing the exact box-drawing example character for character, as long as the reported metrics match the design doc contract.
- Existing top-level ledger commands remain supported and should not be renamed.

Acceptance Criteria:
- [ ] `harnessiq stats summary` reports repo-wide totals derived from the snapshot set.
- [ ] `harnessiq stats agent <agent_name>`, `session <session_id>`, and `instance <instance_id>` return the expected snapshot records.
- [ ] `--format json` works on commands that the design doc marks as supporting it.
- [ ] `harnessiq stats rebuild` recomputes snapshots from the ledger and reports processed/skipped counts.
- [ ] `harnessiq stats export --format json|csv` writes to stdout by default and supports `--output`.
- [ ] CLI registration and output behavior are covered by automated tests.

Verification Steps:
- Static analysis: run repository Python quality tooling or manual style verification over new CLI modules and tests.
- Type checking: run any configured type checker if present; otherwise ensure handlers/helpers are fully annotated.
- Unit tests: run targeted CLI parser/handler tests for each stats subcommand and option.
- Integration tests: run existing CLI suites alongside the new stats CLI tests to confirm no regression in parser registration.
- Smoke verification: use a temporary ledger plus snapshots to run `harnessiq stats summary`, `agent`, `session`, `instance`, `rebuild`, and `export` end to end.

Dependencies:
- Ticket 2.

Drift Guard:
This ticket must not rewrite or remove the existing `logs`, `export`, or `report` command behaviors. Keep the new functionality isolated under `harnessiq stats`. Avoid adding visualization, live dashboards, cost estimation, or any network-backed reporting.
