Title: Refactor CLI parameter parsing to consume harness manifests

Intent: Remove repeated supported-key tuples and coercion logic from the CLI layer by delegating runtime/custom parameter typing to the shared harness manifests.

Scope:
- Update CLI command modules and normalization helpers to use the shared manifests
- Preserve existing command-line behavior and public helper names
- Add tests for manifest-backed normalization and update docs/file index

Relevant Files:
- `harnessiq/cli/common.py`: shared CLI helpers
- `harnessiq/cli/*/commands.py`: manifest-backed runtime/custom parameter parsing
- `tests/`: CLI and manifest coverage
- `docs/agent-runtime.md`: manifest documentation
- `artifacts/file_index.md`: architecture boundary update

Approach:
- Keep public `SUPPORTED_*` constants and `normalize_*` helpers, but derive them from manifest specs
- Use shared helper functions where they meaningfully reduce per-CLI boilerplate
- Add direct tests for the new manifest registry plus regression coverage for existing normalization behavior

Assumptions:
- Runtime/custom parameter typing can be centralized without changing how each CLI persists data on disk

Acceptance Criteria:
- [ ] Existing CLI runtime/custom parameter behavior remains intact
- [ ] Runtime/custom parameter support lists derive from manifest metadata
- [ ] New manifest helpers are directly tested
- [ ] `artifacts/file_index.md` documents the new shared boundary

Verification Steps:
- Run the touched CLI/unit tests and the new manifest test module
- Manually inspect `artifacts/file_index.md` for the shared manifest entry

Dependencies:
- Ticket 1

Drift Guard: This ticket must not introduce a generic CLI scaffolder or rewrite command routing. It is limited to manifest-backed metadata/validation reuse plus documentation and tests.
