Title: Establish behavior-layer runtime foundation and agent integration

Intent:
Introduce the shared behavior formalization model, the new behavior package layout, and the runtime hook expansion required for argument-aware deterministic enforcement. This ticket creates the foundation every concrete behavior layer depends on and makes `behaviors=` a first-class `BaseAgent` constructor surface.

Issue URL:
https://github.com/cerredz/HarnessHub/issues/440

Scope:
- Add the shared behavior abstractions under `harnessiq/interfaces/formalization/behaviors/`.
- Add runtime support for behavior-layer participation, including `behaviors=` ordering in `BaseAgent`.
- Expand the runtime hook contract so behavior layers can inspect a full tool call before execution and correlate it with the resulting `ToolResult`.
- Add compatibility exports for the shared behavior base types.
- Do not implement the concrete behavior-category classes beyond any minimal scaffolding needed by the shared runtime.

Relevant Files:
- `harnessiq/interfaces/formalization/behaviors/__init__.py`: Public re-exports for the behavior package.
- `harnessiq/interfaces/formalization/behaviors/base.py`: `BehaviorConstraint`, `BehaviorEnforcementMode`, and `BaseBehaviorLayer`.
- `harnessiq/agents/base/agent.py`: Add `behaviors=` and merge-order semantics.
- `harnessiq/agents/base/agent_helpers.py`: Add argument-aware hook plumbing and behavior-layer tool/result participation.
- `harnessiq/shared/tools.py`: Extend `ToolResult` or adjacent runtime models if needed to preserve call metadata safely.
- `harnessiq/interfaces/formalization/__init__.py`: Re-export behavior shared types.
- `harnessiq/interfaces/formalization.py`: Compatibility exports for the new behavior surface.
- `harnessiq/interfaces/__init__.py`: Top-level interface exports.
- `harnessiq/formalization/__init__.py`: Legacy-compatible exports where practical.
- `tests/test_agents_base.py`: Cover `behaviors=` integration and richer hook plumbing.
- `tests/test_interfaces.py`: Cover new interface exports and self-description behavior.

Approach:
Build the new behavior package on top of the decomposed interface stack rather than adding more surface to the legacy monolith. Keep `BaseBehaviorLayer` as a thin, self-documenting specialization of `BaseFormalizationLayer`, with default identity/contract/configuration derived from `BehaviorConstraint` records just as the design doc specifies. In the runtime, add a pre-execution seam that can see the concrete `ToolCall` and a correlated post-execution seam that can see both the call and the result. Wire `BaseAgent(behaviors=...)` so behavior layers are composed after stage-layer injection but before explicit `formalization_layers`, matching the requested precedence without adding new artifact constructor sugar. Preserve backward compatibility by exporting the new behavior-layer base types through both the `interfaces` and legacy formalization surfaces.

Assumptions:
- The new behavior package under `harnessiq/interfaces/formalization/behaviors/` is the canonical implementation target.
- Runtime hook expansion is acceptable and required for faithful design-doc compliance.
- Only `behaviors=` should be added to `BaseAgent` in this task.
- Legacy compatibility exports should expose behavior-layer types without requiring a full migration of the old formalization package internals.

Acceptance Criteria:
- [ ] `harnessiq/interfaces/formalization/behaviors/` exists with shared behavior base types and package re-exports.
- [ ] `BaseAgent` accepts a `behaviors=` parameter and composes behavior layers before explicit `formalization_layers`.
- [ ] The runtime exposes enough call metadata for argument-aware behavior enforcement.
- [ ] The shared behavior base auto-generates identity, contract, rules, configuration, and prompt augmentation from declared constraints.
- [ ] New behavior shared types are exported from both the `interfaces` surface and legacy-compatible exports.
- [ ] Tests cover `behaviors=` integration and the new export surface.

Verification Steps:
1. Run targeted static analysis on the changed runtime and interface files.
2. Run targeted type validation via the project’s Python test/import surface.
3. Run `pytest tests/test_agents_base.py tests/test_interfaces.py`.
4. Smoke-test a small fake behavior layer through `BaseAgent.build_model_request()` and one tool-call cycle.
5. Confirm imports work from `harnessiq.interfaces`, `harnessiq.interfaces.formalization`, and `harnessiq.formalization`.

Dependencies:
- None.

Drift Guard:
This ticket must not implement the full concrete category matrix or invent new artifact-layer constructor sugar. Its job is to create the shared behavior abstractions, the runtime enforcement plumbing, and the public API bridge that later tickets can build on without revisiting core agent orchestration.
