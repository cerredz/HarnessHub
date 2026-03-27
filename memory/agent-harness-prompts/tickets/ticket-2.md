Title: Implement the mission-driven harness and durable mission artifact memory store

Intent: Convert the `mission_driven` master prompt into a real reusable harness that creates and updates the prompt’s mission artifact as durable machine-readable and narrative state, with explicit typed stages instead of a single opaque prompt execution.

Scope:
- Add a new concrete agent package under `harnessiq/agents/mission_driven/`.
- Implement mission initialization, artifact loading, staged LLM subcalls, and durable memory updates for the mission artifact files.
- Expose ledger outputs and parameter sections that reflect current mission state.
- Add focused tests for mission initialization, resumability, staged subcalls, and artifact persistence.
- Do not implement spawn/delegation orchestration beyond what the mission-driven harness itself needs.

Relevant Files:
- `harnessiq/agents/mission_driven/__init__.py` - public package exports for the new harness.
- `harnessiq/agents/mission_driven/agent.py` - concrete `BaseAgent` subclass and mission orchestration logic.
- `harnessiq/shared/mission_driven.py` - shared mission config, memory store, artifact models, and manifest contract.
- `harnessiq/agents/__init__.py` - top-level export for the new harness.
- `harnessiq/shared/__init__.py` - shared export updates for the mission-driven contracts.
- `tests/test_mission_driven_agent.py` - focused harness tests.

Approach: Treat the master prompt as a specification, not as the runtime itself. Break the flow into explicit stages such as mission initialization, task decomposition, README/narrative regeneration, and consistency checking. Persist the canonical mission artifact files directly to disk through a dedicated memory store. Use typed JSON subcalls for artifact-generation stages and deterministic local logic for validation, write ordering, and file synchronization.

Assumptions:
- The mission-driven harness should own the full storage layout described by the prompt.
- The narrative `README.md` should be regenerated from structured state inside the harness rather than treated as the primary source of truth.
- Model subcalls can return typed JSON payloads that the harness validates before writing to disk.

Acceptance Criteria:
- [ ] `MissionDrivenAgent` exists as a reusable `BaseAgent` subclass under `harnessiq/agents/mission_driven/`.
- [ ] The harness initializes and persists the full required mission artifact layout under its memory path.
- [ ] The harness supports resuming from existing mission memory without discarding prior durable state.
- [ ] Staged subcalls produce validated artifact updates rather than one monolithic free-form output.
- [ ] Focused tests cover initialization, resume behavior, durable artifact persistence, and key staged subcall flows.

Verification Steps:
- Run `python -m pytest tests/test_mission_driven_agent.py`.
- Run `python -m pytest tests/test_harness_manifests.py` after the new manifest is wired.
- Perform a focused smoke test with a fake model to verify that mission artifact files are created and updated in the required order.

Dependencies: Ticket 1.

Drift Guard: This ticket must stay centered on the mission-driven prompt and its artifact lifecycle. It must not absorb generalized sub-agent delegation behavior, invent CLI flows, or refactor unrelated agent runtime code.
