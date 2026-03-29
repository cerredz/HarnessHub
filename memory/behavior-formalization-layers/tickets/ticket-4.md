Title: Implement recovery and safety behavior categories

Intent:
Add the categories that react to failures and prevent dangerous actions. These classes are the main consumers of the new argument-aware enforcement plumbing and are necessary to satisfy the design doc’s deterministic guardrail model.

Issue URL:
https://github.com/cerredz/HarnessHub/issues/443

Scope:
- Implement the typed category bases for error recovery and safety behavior.
- Implement `RetryStrategyBehavior`, `StuckDetectionBehavior`, `ErrorEscalationBehavior`.
- Implement `IrreversibleActionGateBehavior`, `RateLimitBehavior`, `ScopeGuardBehavior`.
- Contribute any behavior-owned helper tools needed for confirmations.
- Add category-focused tests.
- Do not implement communication-category behaviors in this ticket.

Relevant Files:
- `harnessiq/interfaces/formalization/behaviors/recovery/base.py`: `RecoveryStrategySpec` and `BaseErrorRecoveryLayer`.
- `harnessiq/interfaces/formalization/behaviors/recovery/retry.py`: `RetryStrategyBehavior`.
- `harnessiq/interfaces/formalization/behaviors/recovery/stuck.py`: `StuckDetectionBehavior`.
- `harnessiq/interfaces/formalization/behaviors/recovery/escalation.py`: `ErrorEscalationBehavior`.
- `harnessiq/interfaces/formalization/behaviors/safety/base.py`: `GuardrailSpec` and `BaseSafetyBehaviorLayer`.
- `harnessiq/interfaces/formalization/behaviors/safety/irreversible.py`: `IrreversibleActionGateBehavior`.
- `harnessiq/interfaces/formalization/behaviors/safety/rate_limit.py`: `RateLimitBehavior`.
- `harnessiq/interfaces/formalization/behaviors/safety/scope_guard.py`: `ScopeGuardBehavior`.
- `harnessiq/interfaces/formalization/behaviors/__init__.py`: Re-export new category classes.
- `tests/test_formalization_behaviors_recovery_safety.py`: Recovery and safety behavior tests.

Approach:
Build recovery tracking around normalized argument fingerprints plus consecutive failure state so the runtime can distinguish “same failing call repeated” from “same tool used for a different attempt.” Keep safety guardrails explicit by using helper tools only where they represent a true behavior-layer contract, such as irreversible action confirmation. Where a violation should block tool visibility, prefer deterministic filtering. Where a violation should pause the run, use the runtime’s existing pause signal semantics rather than inventing a parallel mechanism.

Assumptions:
- Ticket 1 has landed argument-aware enforcement plumbing.
- Tool arguments available to behavior layers are normalized enough to fingerprint repeat calls deterministically.
- Irreversible confirmation should be consumed after the protected tool executes, matching the design doc’s “one confirmed call” semantics.

Acceptance Criteria:
- [ ] Recovery category base and all three concrete recovery behaviors exist and are exported.
- [ ] Safety category base and all three concrete safety behaviors exist and are exported.
- [ ] Retry/stuck enforcement uses argument-aware tracking rather than tool-key-only heuristics.
- [ ] Irreversible confirmation, rate limits, and scope-guard blocking work deterministically.
- [ ] Tests cover repeated-call, failing-call, confirmation, rate-limit, and out-of-scope argument scenarios.

Verification Steps:
1. Run targeted static analysis on the recovery and safety modules.
2. Run `pytest tests/test_formalization_behaviors_recovery_safety.py`.
3. Run a targeted regression slice from `tests/test_agents_base.py` if pause behavior or tool-result propagation changes.
4. Manually simulate one failing repeated call, one irreversible confirmation, and one scope-guard block.

Dependencies:
- Ticket 1.

Drift Guard:
This ticket must not fold communication/reporting obligations into recovery or safety. Its only job is to detect failure patterns and enforce guardrails around dangerous actions using the runtime capabilities established earlier.
