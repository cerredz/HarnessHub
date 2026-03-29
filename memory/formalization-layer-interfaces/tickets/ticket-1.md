Title: Add formalization interface contracts to the public SDK

Intent: Introduce a minimal, self-documenting formalization-layer abstraction to the public `harnessiq.interfaces` package so future harness runtime integration has a stable interface surface without requiring a broader execution-layer refactor now.

Scope: Create a new formalization interface module, export it from `harnessiq.interfaces`, add a focused subset of typed base formalization layer classes, and cover the public behavior with tests. This ticket does not integrate formalization layers into `BaseAgent` execution.

Relevant Files:
- `harnessiq/interfaces/formalization.py`: new self-documenting formalization base classes and supporting records.
- `harnessiq/interfaces/__init__.py`: export the new public contracts.
- `tests/test_interfaces.py`: verify new exports and core self-documenting behavior.
- `memory/formalization-layer-interfaces/*`: durable planning and verification artifacts for this task.

Approach: Use abstract base classes and small frozen dataclasses to model the public interface. The universal base should expose description helpers, default context rendering through `AgentParameterSection`, and no-op lifecycle hooks named after the existing runtime seams. Typed base classes should express higher-level specializations such as contracts, artifacts, hooks, stages, and state, with type-specific abstract methods feeding the inherited self-documentation path.

Assumptions:
- The user wants runtime-agnostic public contracts, not immediate runtime wiring.
- A representative subset of typed base layers is sufficient for this change.
- Reusing `AgentParameterSection` from the shared runtime layer is appropriate for the context-window contract.

Acceptance Criteria:
- [ ] `harnessiq.interfaces` exports the new formalization contracts.
- [ ] The new module defines a base self-documenting formalization layer abstraction with default prompt/context and hook methods.
- [ ] The new module includes a focused subset of typed base layers for at least contracts, artifacts, hooks, stages, and state.
- [ ] Targeted tests validate exports and at least one concrete example of the default documentation rendering.
- [ ] No existing runtime behavior changes outside the scoped interface/test files.

Verification Steps:
- Run the targeted interface test module.
- Confirm the new module stays importable from `harnessiq.interfaces`.
- Confirm the tests exercise the default self-documentation path rather than only import presence.

Dependencies: None.

Drift Guard: Do not modify `BaseAgent`, hook execution, tool execution, or reset logic in this ticket. Do not add concrete harness implementations. Do not regenerate repository-wide docs or file-index artifacts as part of this change.
