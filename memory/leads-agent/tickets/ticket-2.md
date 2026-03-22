Title: Add deterministic agent transcript pruning controls

Issue URL: https://github.com/cerredz/HarnessHub/issues/150

Intent:
Extend the shared agent runtime so long-running agents can deterministically compact transcript state on a fixed interval defined by search count or token budget, which is required for the leads agent’s rolling per-ICP search loop.

Scope:
This ticket adds shared runtime configuration and `BaseAgent` behavior for deterministic pruning/compaction scheduling.
This ticket does not add the leads-specific memory model, Apollo integration, or user-facing CLI/docs.

Relevant Files:
- `harnessiq/shared/agents.py`: add shared runtime config fields and any new transcript-pruning configuration types/constants.
- `harnessiq/agents/base/agent.py`: implement deterministic pruning hooks in the shared run loop.
- `tests/test_agents_base.py`: add coverage for interval-based pruning and token-threshold pruning interactions.
- `artifacts/file_index.md`: update the architecture index if the runtime contract meaningfully changes.

Approach:
Keep the current `BaseAgent` architecture intact and introduce an opt-in deterministic pruning contract rather than a leads-agent-specific fork. The runtime should support fixed-interval pruning triggers that are independent of the existing “reset when transcript budget is exceeded” fallback.
Design the shared config so it can represent both token-driven and event-count-driven pruning without embedding leads-specific names. The concrete leads agent can then map “search count” to the generic runtime signal while other agents remain unaffected unless they opt in.

Assumptions:
- Deterministic pruning can be added without breaking the existing `LinkedInJobApplierAgent`, `ExaOutreachAgent`, and `KnowtAgent` tests.
- The pruning mechanism may reuse existing context-compaction concepts, but the scheduler itself belongs in shared runtime code.
- Search-count-triggered pruning will be driven by explicit agent/runtime bookkeeping rather than inferred heuristically from arbitrary tool calls.

Acceptance Criteria:
- [ ] Shared runtime config supports deterministic pruning thresholds that can be reused by concrete agents.
- [ ] `BaseAgent` can deterministically compact/reset transcript state based on the configured schedule.
- [ ] Existing runtime behavior remains unchanged for agents that do not opt into the new controls.
- [ ] Base-agent tests cover fixed-interval pruning and confirm parameter sections are reloaded correctly after pruning.

Verification Steps:
- Static analysis: run the linter against `harnessiq/shared/agents.py` and `harnessiq/agents/base/agent.py`.
- Type checking: run the type checker or validate full type annotations/import safety for the touched modules.
- Unit tests: run `pytest tests/test_agents_base.py`.
- Integration and contract tests: run agent-level tests that exercise current harnesses to confirm no regression in shared runtime semantics.
- Smoke verification: run a fake-model scenario that triggers deterministic pruning and inspect the resulting requests passed to the model.

Dependencies:
- None.

Drift Guard:
This ticket must not implement any leads-domain models, storage backends, provider wiring, or CLI commands. It only establishes the shared runtime capability that the leads agent will depend on later.
