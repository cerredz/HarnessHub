Title: Rename the source package to harnessiq and stabilize the SDK import surface
Issue URL: Not created; `gh` is unavailable in this environment.

Intent: Establish `harnessiq` as the real Python package namespace so external users can import the SDK directly without relying on the repository-internal `src.*` path.

Scope:
- Rename the production package root from `src` to `harnessiq`.
- Update internal imports throughout the codebase to use `harnessiq.*`.
- Preserve and curate the public package exports for agents and tools.
- Update tests to consume the renamed package namespace.
- Do not add packaging metadata or documentation beyond what is required to validate the new import root.

Relevant Files:
- `src/` -> `harnessiq/`: rename the production package root to the SDK package namespace.
- `harnessiq/agents/*.py`: update imports and preserve first-class agent exports.
- `harnessiq/tools/*.py`: update imports and preserve first-class tool exports.
- `harnessiq/providers/**/*.py`: update imports required by agent/tool/provider interactions.
- `harnessiq/shared/*.py`: update shared import paths.
- `tests/*.py`: switch tests from `src.*` imports to `harnessiq.*`.

Approach:
- Perform a real package-root rename so the repository’s import model matches the intended SDK identity.
- Update all absolute imports from `src.*` to `harnessiq.*`.
- Keep the existing package-level `__init__.py` export pattern, using those modules as the curated SDK surface for agents and tools.
- Preserve provider modules in the distribution because concrete agents and tools depend on them, but keep the SDK messaging centered on agents/tools.

Assumptions:
- The user wants the actual import root to be `harnessiq`, not a wrapper around `src`.
- Existing agents such as `LinkedInJobApplierAgent` and `BaseEmailAgent` remain first-class SDK exports.
- Backward compatibility for `src.*` imports is not required in this pass.

Acceptance Criteria:
- [ ] The production code lives under a `harnessiq/` package root instead of `src/`.
- [ ] No production module imports `src.*`.
- [ ] No test imports `src.*`.
- [ ] `harnessiq.agents` exposes the current first-class agent/runtime surface.
- [ ] `harnessiq.tools` exposes the current first-class tool/runtime surface.
- [ ] The existing automated tests pass after the import-root rename.

Verification Steps:
- Static analysis: search the repo for lingering `src.` imports and remove them.
- Type checking: no configured type checker; validate imports and signatures through the test suite and manual review.
- Unit tests: run the full test suite after the rename.
- Integration and contract tests: verify provider/client tests still pass through the renamed import root.
- Smoke/manual verification: import `harnessiq`, `harnessiq.agents`, and `harnessiq.tools` from a Python shell in the repo and confirm the expected exports resolve.

Dependencies: None.

Drift Guard: This ticket must not introduce packaging metadata, publishing configuration, or broad documentation work. Its job is to make `harnessiq` the real import namespace while preserving current behavior.
