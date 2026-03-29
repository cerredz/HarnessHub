Title: Implement reasoning and quality behavior categories

Intent:
Add the behavior categories that force explicit reasoning before action and gate completion against declared quality criteria. These layers carry the strongest prompt-plus-code duality in the design doc and depend on the runtime foundation being stable.

Issue URL:
https://github.com/cerredz/HarnessHub/issues/442

Scope:
- Implement the typed category bases for reasoning behavior and quality behavior.
- Implement `PreActionReasoningBehavior`, `SelfCritiqueBehavior`, `HypothesisTestingBehavior`.
- Implement `ScopeEnforcementBehavior`, `QualityGateBehavior`, `CitationRequirementBehavior`.
- Contribute any behavior-owned helper tools required by the quality category, such as a scope-violation reporting tool.
- Add category-focused tests.
- Do not implement recovery, safety, or communication categories in this ticket.

Relevant Files:
- `harnessiq/interfaces/formalization/behaviors/reasoning/base.py`: `ReasoningRequirementSpec` and `BaseReasoningBehaviorLayer`.
- `harnessiq/interfaces/formalization/behaviors/reasoning/pre_action.py`: `PreActionReasoningBehavior`.
- `harnessiq/interfaces/formalization/behaviors/reasoning/self_critique.py`: `SelfCritiqueBehavior`.
- `harnessiq/interfaces/formalization/behaviors/reasoning/hypothesis.py`: `HypothesisTestingBehavior`.
- `harnessiq/interfaces/formalization/behaviors/quality/base.py`: `QualityCriterionSpec` and `BaseQualityBehaviorLayer`.
- `harnessiq/interfaces/formalization/behaviors/quality/scope.py`: `ScopeEnforcementBehavior`.
- `harnessiq/interfaces/formalization/behaviors/quality/gate.py`: `QualityGateBehavior`.
- `harnessiq/interfaces/formalization/behaviors/quality/citation.py`: `CitationRequirementBehavior`.
- `harnessiq/interfaces/formalization/behaviors/__init__.py`: Re-export new category classes.
- `tests/test_formalization_behaviors_reasoning_quality.py`: Reasoning and quality behavior tests.

Approach:
Use the behavior base model to keep reasoning and quality rules declarative while enforcing them through deterministic filtering or `control.mark_complete` interception. For quality gates, centralize agent-state assembly so criteria can be evaluated predictably without burying task-specific checks inside the runtime loop. For scope enforcement, contribute a lightweight behavior-owned tool that records explicit scope-violation signals while keeping the layer’s main contract focused on declared in-scope and out-of-scope boundaries.

Assumptions:
- Ticket 1 has delivered the runtime hooks needed to correlate action tools and reasoning prerequisites.
- The existing control-tool family remains the canonical completion signal surface.
- Citation requirements are enforced against structured outputs the runtime can observe, not against arbitrary natural-language prose.

Acceptance Criteria:
- [ ] Reasoning category base and all three concrete reasoning behaviors exist and are exported.
- [ ] Quality category base and all three concrete quality behaviors exist and are exported.
- [ ] Reasoning-triggered action tools are hidden until the required reasoning step occurs.
- [ ] `control.mark_complete` is blocked when declared quality criteria fail.
- [ ] Scope and citation enforcement expose deterministic, inspectable state and helper tools where needed.
- [ ] Tests cover both compliant and blocked flows for each concrete class.

Verification Steps:
1. Run targeted static analysis on the reasoning and quality modules.
2. Run `pytest tests/test_formalization_behaviors_reasoning_quality.py`.
3. Run targeted regression coverage from `tests/test_agents_base.py` if the completion path changes.
4. Smoke-test one reasoning-gated write flow and one quality-gated completion flow.

Dependencies:
- Ticket 1.
- Ticket 2 for shared pattern consistency, but not as a hard runtime dependency.

Drift Guard:
This ticket must not implement generic retry/guardrail/communication machinery. It should keep reasoning and quality enforcement self-contained and avoid turning the quality layer into a grab bag for all remaining runtime rules.
