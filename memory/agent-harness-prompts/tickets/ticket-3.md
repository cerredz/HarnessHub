Title: Implement the spawn-specialized-subagents harness and integrate both harnesses into exports and manifests

Intent: Convert the `spawn_specialized_subagents` master prompt into a reusable orchestration harness that plans bounded delegation, runs specialized worker/synthesis subcalls with explicit ownership, and persists orchestration state coherently alongside the mission-driven harness registration work.

Scope:
- Add a new concrete agent package under `harnessiq/agents/spawn_subagents/`.
- Implement orchestrator planning, worker assignment generation, result integration, and durable orchestration-memory updates.
- Register both new harnesses in public exports and the built-in manifest registry.
- Add focused tests for planning, delegation contracts, worker-result integration, and manifest/export wiring.
- Do not add a full remote multi-agent runtime; use local typed subcalls as the harness execution mechanism.

Relevant Files:
- `harnessiq/agents/spawn_subagents/__init__.py` - public package exports for the new harness.
- `harnessiq/agents/spawn_subagents/agent.py` - concrete orchestration harness implementation.
- `harnessiq/shared/spawn_subagents.py` - shared config, memory store, manifest, and orchestration artifact models.
- `harnessiq/agents/__init__.py` - top-level export updates for both new harnesses.
- `harnessiq/shared/harness_manifests.py` - built-in manifest registration.
- `harnessiq/shared/__init__.py` - shared export updates.
- `tests/test_spawn_subagents_agent.py` - focused harness tests.
- `tests/test_harness_manifests.py` - manifest registry assertions.

Approach: Model the prompt as an orchestrator harness with explicit phases: decide immediate local step, produce bounded worker assignments, run worker subcalls with minimal scoped context, and synthesize results into one coherent output. Persist the orchestration graph, worker assignments, and accepted/rejected integration outcomes through the shared memory store so the harness remains resumable and inspectable.

Assumptions:
- “Spawn sub-agents” in this repository should be implemented as structured internal model-worker stages, not as a new external process/runtime manager.
- The harness should record ownership boundaries and integration outcomes durably, because coherence and resumability are core parts of the prompt.
- Export and manifest integration for both harnesses can land alongside this ticket without needing separate CLI work.

Acceptance Criteria:
- [ ] `SpawnSpecializedSubagentsAgent` exists as a reusable `BaseAgent` subclass under `harnessiq/agents/spawn_subagents/`.
- [ ] The harness produces typed delegation artifacts with explicit ownership, deliverables, and completion conditions.
- [ ] Worker outputs are validated and integrated into a single persisted orchestration state.
- [ ] Both new harnesses are exported publicly and registered in the built-in manifest registry.
- [ ] Focused tests cover orchestration planning, worker assignment generation, integration behavior, and registry/export wiring.

Verification Steps:
- Run `python -m pytest tests/test_spawn_subagents_agent.py`.
- Run `python -m pytest tests/test_harness_manifests.py`.
- Run any focused SDK/export tests affected by new public agent exports.

Dependencies: Ticket 1.

Drift Guard: This ticket must not attempt to build a general distributed agent platform. It should stay within the repository’s existing harness pattern, using local typed model stages and durable orchestration state rather than inventing a separate execution framework.
