Title: Add shared contracts and subcall tooling for prompt-driven harness orchestration

Intent: Establish the shared types, manifests, durable-memory helpers, and typed subcall seam that both new prompt-driven harnesses need so each concrete agent can stay focused on domain orchestration rather than re-implementing shared plumbing.

Scope:
- Add shared domain contracts for the mission-driven and spawn-subagents harness families.
- Add any shared DTOs or tooling helpers needed to run deterministic JSON-returning model subcalls.
- Register new tool constants/helpers only if required by the concrete harness implementations.
- Do not implement the full concrete orchestration behavior for either harness in this ticket.

Relevant Files:
- `harnessiq/shared/mission_driven.py` - shared config, manifest metadata, mission artifact models, and durable mission memory store.
- `harnessiq/shared/spawn_subagents.py` - shared config, manifest metadata, orchestration-state models, and durable memory store for delegation runs.
- `harnessiq/shared/dtos/*.py` - typed DTOs for instance payloads or orchestration artifacts when a layer boundary benefits from explicit serialization contracts.
- `harnessiq/shared/tools.py` - new tool keys only if a shared orchestration helper must be model-visible.
- `harnessiq/tools/*.py` - shared execution helper(s) for typed JSON subcalls or reusable orchestration support.
- `tests/test_harness_manifests.py` - manifest registration assertions for the new harnesses.
- `tests/test_tools.py` or focused new tool tests - verification for any new shared tooling.

Approach: Follow the repository’s established split: shared modules own manifests, config dataclasses, normalizers, and file-backed memory stores; concrete agents consume those contracts. Reuse the prospecting harness’s JSON subcall pattern as the baseline, extracting a small reusable seam only where both new harnesses benefit from it. Keep any new tool surface narrowly-scoped and deterministic.

Assumptions:
- The new harnesses should be first-class built-in manifests even without top-level CLI commands.
- A shared JSON subcall helper is preferable to two ad hoc implementations if the signatures align cleanly.
- `interfaces/` should remain untouched unless a genuine new reusable protocol emerges.

Acceptance Criteria:
- [ ] Shared config/memory/manifest modules exist for both new harness families under `harnessiq/shared/`.
- [ ] Any new DTOs or helper functions introduced have clear serialization boundaries and tests.
- [ ] Any new shared tooling is deterministic, minimal, and covered by focused tests.
- [ ] Both new manifests resolve through the built-in manifest registry without breaking existing manifests.
- [ ] No concrete harness orchestration logic is duplicated into the shared layer unnecessarily.

Verification Steps:
- Run `python -m pytest tests/test_harness_manifests.py`.
- Run focused shared/tool tests covering any newly added helper or tool modules.
- Smoke-check import/export paths for the new shared contracts in a Python process or equivalent test.

Dependencies: None.

Drift Guard: This ticket must stop at shared infrastructure and contracts. It must not become a partial implementation of either concrete agent’s domain logic, and it must not grow into a broad refactor of the base runtime or existing harnesses.
