## Phase 1 - Codebase Internalization

### 1a: Structural Survey

- The repo is a Python SDK centered on `harnessiq/` with top-level runtime packages for `agents`, `cli`, `config`, `integrations`, `providers`, `shared`, `tools`, `toolset`, and `utils`.
- `tests/` already contains package-level architecture checks in addition to behavior tests, which makes repo-local AST enforcement a natural fit.
- `artifacts/file_index.md` and `artifacts/future_changes_to_repo.md` define the intended dependency direction for the monolith.
- Initial AST inspection showed a top-level SCC across `providers`, `shared`, `tools`, `toolset`, and `utils`.

### 1b: Task Cross-Reference

- `harnessiq/shared/email.py` leaked `shared -> tools`.
- `harnessiq/tools/leads/operations.py` leaked `tools -> toolset`.
- `harnessiq/utils/ledger_sinks.py` plus provider output-sink internals contributed to `utils -> providers`.
- `harnessiq/shared/agents.py` and shared run-storage ownership also had to be tightened to make full top-level acyclicity pass.
- New mechanical enforcement belongs in the test suite, with `artifacts/file_index.md` updated to document it.

### 1c: Assumption & Risk Inventory

- Assumed the user wanted the repo green after enforcement, not a checker that lands red.
- Assumed a repo-local AST checker was preferable to adding `import-linter`/`grimp` because no architecture-lint dependency stack is configured.
- Main risk was that whole-graph cycle detection would expose existing debt; implementation therefore had to remove the current SCC first.

Phase 1 complete.
