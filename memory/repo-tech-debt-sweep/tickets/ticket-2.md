Title: Decompose the ledger utility module behind a compatibility facade

Intent:
Break up the monolithic ledger utility module so output sinks, connection persistence, reporting, and export/query helpers are easier to navigate and modify without carrying the entire ledger subsystem in one file.

Issue URL: https://github.com/cerredz/HarnessHub/issues/207

Scope:

- Split `harnessiq/utils/ledger.py` into smaller focused modules.
- Keep `harnessiq.utils` and `harnessiq.utils.ledger` import surfaces backward compatible.
- Preserve sink behavior, connection config behavior, ledger loading/export behavior, and report rendering behavior.
- Do not change sink payload schemas or CLI command UX.

Relevant Files:

- `harnessiq/utils/ledger.py`: convert from implementation-heavy module into a compatibility facade re-exporting the decomposed implementation.
- `harnessiq/utils/ledger_models.py`: new module for ledger dataclasses, statuses, and core JSON/time helpers.
- `harnessiq/utils/ledger_sinks.py`: new module for sink implementations and sink-construction helpers.
- `harnessiq/utils/ledger_connections.py`: new module for `SinkConnection`, `ConnectionsConfig`, `ConnectionsConfigStore`, and sink-spec parsing.
- `harnessiq/utils/ledger_reports.py`: new module for report-building/rendering helpers.
- `harnessiq/utils/ledger_exports.py`: new module for ledger loading/filtering/export helpers.
- `harnessiq/utils/__init__.py`: preserve the existing public re-export surface.
- `tests/test_output_sinks.py`: confirm sinks and sink-building behavior remain unchanged.
- `tests/test_ledger_cli.py`: confirm CLI paths still work through the compatibility facade.

Approach:

- Extract cohesive clusters in small steps while leaving `ledger.py` as the stable import anchor.
- Move pure helpers with the responsibilities they serve instead of creating one new catch-all helper module.
- Keep cross-module dependencies acyclic where possible: models/helpers at the bottom, then sinks/connections/exports/reports, then the facade.
- Preserve function and class names exactly unless a helper is private and fully internal.

Assumptions:

- The ledger subsystem is used via public imports from `harnessiq.utils` and `harnessiq.utils.ledger`; preserving those names is sufficient for compatibility.
- Current ledger tests cover the important behaviors for sinks, parsing, and CLI usage.
- No external user depends on private helper function locations inside `ledger.py`.

Acceptance Criteria:

- [ ] The ledger implementation is split across focused modules with `ledger.py` remaining as a compatibility facade.
- [ ] Public imports currently used by tests continue to resolve without caller changes.
- [ ] Output sink behavior and ledger connection parsing behavior remain unchanged.
- [ ] Ledger CLI tests and sink tests pass after the refactor.
- [ ] The resulting `ledger.py` file is materially smaller and easier to scan than the current implementation-heavy version.

Verification Steps:

- Static analysis: run `python -m compileall harnessiq tests`.
- Type checking: no configured type checker; keep extracted module signatures fully annotated and verify imports remain consistent.
- Unit tests: run `.venv\Scripts\pytest.exe -q tests/test_output_sinks.py tests/test_ledger_cli.py`.
- Integration and contract tests: run `.venv\Scripts\pytest.exe -q tests/test_agents_base.py tests/test_linkedin_cli.py` to confirm the runtime and CLI still resolve ledger exports correctly.
- Smoke/manual verification: run `.venv\Scripts\python.exe -m harnessiq.cli connections list` and `.venv\Scripts\python.exe -m harnessiq.cli report --help`.

Dependencies:

- None.

Drift Guard:

This ticket is a structure-preserving refactor. It must not introduce new sink types, alter sink payload contracts, change connection file formats, or redesign the ledger CLI. The only acceptable behavior changes are compatibility-preserving fixes required to keep the refactor coherent.
