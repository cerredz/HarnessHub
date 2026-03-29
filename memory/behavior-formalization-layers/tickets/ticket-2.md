Title: Implement tool and execution-pace behavior categories

Intent:
Deliver the behavior categories that primarily govern tool visibility and work cadence. These classes are the least dependent on richer post-run state evaluation and establish the main `filter_tool_keys` enforcement pattern used throughout the design.

Issue URL:
https://github.com/cerredz/HarnessHub/issues/441

Scope:
- Implement the typed category bases for tool behavior and execution pace.
- Implement `ToolCallLimitBehavior`, `ToolSequencingBehavior`, `ToolCooldownBehavior`.
- Implement `ReflectionCadenceBehavior`, `ProgressCheckpointBehavior`, `VerificationBehavior`.
- Add parameter-section rendering that surfaces pending or consumed budgets/cadence state.
- Add category-focused tests.
- Do not implement reasoning, quality, recovery, safety, or communication categories in this ticket.

Relevant Files:
- `harnessiq/interfaces/formalization/behaviors/tool/base.py`: `ToolConstraintSpec` and `BaseToolBehaviorLayer`.
- `harnessiq/interfaces/formalization/behaviors/tool/limit.py`: `ToolCallLimitBehavior`.
- `harnessiq/interfaces/formalization/behaviors/tool/sequencing.py`: `ToolSequencingBehavior`.
- `harnessiq/interfaces/formalization/behaviors/tool/cooldown.py`: `ToolCooldownBehavior`.
- `harnessiq/interfaces/formalization/behaviors/pace/base.py`: `PaceRuleSpec` and `BaseExecutionPaceLayer`.
- `harnessiq/interfaces/formalization/behaviors/pace/reflection.py`: `ReflectionCadenceBehavior`.
- `harnessiq/interfaces/formalization/behaviors/pace/checkpoint.py`: `ProgressCheckpointBehavior`.
- `harnessiq/interfaces/formalization/behaviors/pace/verification.py`: `VerificationBehavior`.
- `harnessiq/interfaces/formalization/behaviors/__init__.py`: Re-export new category classes.
- `tests/test_formalization_behaviors_tool_pace.py`: Tool and pace behavior tests.

Approach:
Implement both category bases as self-documenting `BaseBehaviorLayer` specializations that derive their rule records from typed specs and use `is_tool_allowed()` for pattern matching. Keep enforcement deterministic by using the new runtime hook plumbing from ticket 1 to track state transitions cleanly. For cadence/verification, prefer explicit pending-state flags and parameter sections so the model-visible context reflects the same state that governs tool filtering in Python.

Assumptions:
- Ticket 1 has already landed the runtime plumbing and shared base types.
- `control.*`, `artifact.*`, and reasoning tool patterns already exist in the shared tool catalog.
- Verification behavior should be expressed as a visibility gate rather than ad hoc prompt prose.

Acceptance Criteria:
- [ ] Tool behavior category base and all three concrete tool behaviors exist and are exported.
- [ ] Execution-pace category base and all three concrete pace behaviors exist and are exported.
- [ ] Tool visibility is deterministically filtered according to limits, prerequisites, cooldowns, and cadence state.
- [ ] Parameter sections expose enough state for budgets and pending cadence requirements to be inspectable.
- [ ] Tests cover happy-path and blocked-path behavior for each concrete class.

Verification Steps:
1. Run targeted static analysis on the new behavior modules.
2. Run `pytest tests/test_formalization_behaviors_tool_pace.py`.
3. Run a smaller regression slice from `tests/test_agents_base.py` if runtime interaction coverage is needed.
4. Manually instantiate one tool behavior and one pace behavior and confirm filtered tool keys change after simulated tool calls.

Dependencies:
- Ticket 1.

Drift Guard:
This ticket must stay within tool-visibility and cadence enforcement. It must not absorb reasoning-quality-safety concerns or rework the runtime foundation already established in ticket 1 except for small follow-up fixes discovered during integration.
