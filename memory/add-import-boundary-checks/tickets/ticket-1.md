Title: Add repo-local import boundary enforcement and break the current top-level package cycle

Issue URL: https://github.com/cerredz/HarnessHub/issues/464
PR URL: https://github.com/cerredz/HarnessHub/pull/466

Intent:
Add mechanical import-boundary checks for the documented package architecture and remove the existing dependency leaks that would otherwise make those checks fail immediately.

Scope:
Add a repo-local AST checker, wire it into tests, update the architecture artifact, and refactor the existing `shared -> tools`, `tools -> toolset`, `shared -> utils`, and `utils -> providers` cycle-causing seams. Preserve public imports and runtime behavior.

Acceptance Criteria:

- [x] A mechanical import-boundary checker exists in the repo and is exercised by tests.
- [x] `shared` no longer imports `tools`, and the repo rejects future regressions.
- [x] `agents` importing provider families with matching tool seams is rejected.
- [x] `cli` importing lower-level provider/tool/toolset internals is rejected.
- [x] The top-level package graph is acyclic.
- [x] Public output-sink and toolset catalog import surfaces remain stable.
- [x] `artifacts/file_index.md` documents the new enforcement surface.
