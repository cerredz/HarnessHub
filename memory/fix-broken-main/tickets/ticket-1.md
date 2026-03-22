Title: Stabilize refreshed main and restore a clean pytest baseline

Issue URL: https://github.com/cerredz/HarnessHub/issues/203

PR URL: https://github.com/cerredz/HarnessHub/pull/204

Intent:
Repair all reproducible regressions currently failing on refreshed `main`, then land one reviewable PR that returns the repository to a green test baseline without changing intended product behavior.

Scope:
This ticket restores the ExaOutreach, provider-tracing, base-agent, leads-agent, ledger fallback, reasoning-tool, Knowt runtime-config, and shared-definition behaviors currently failing in tests.
This ticket does not attempt to solve external provider/account authorization issues that surface as live `403` responses outside the test harness.

Relevant Files:
- `harnessiq/shared/exa_outreach.py`: restore the correct storage backend contract and keep Exa shared definitions centralized.
- `harnessiq/cli/exa_outreach/commands.py`: normalize run identifiers for JSON emission.
- `harnessiq/shared/http.py`: restore mutable provider HTTP exceptions for traceback propagation.
- `harnessiq/agents/base/agent.py`: fix reset/prune ordering so progress-based resets still occur on terminal cycles.
- `harnessiq/agents/leads/agent.py`: repair constructor tool-registry wiring.
- `harnessiq/utils/ledger.py`: make HarnessIQ home-dir resolution resilient when user-home environment variables are absent.
- `harnessiq/shared/tools.py`: restore the intended brainstorm count bounds/presets.
- `harnessiq/tools/reasoning/injectable.py`: accept brainstorm count presets and enforce the restored max consistently.
- `harnessiq/agents/knowt/agent.py`: preserve LangSmith runtime-config fields when injecting Knowt defaults.
- `harnessiq/shared/prospecting.py`: become the shared home for prospecting prompt constants that should not live in the agent module.
- `harnessiq/agents/prospecting/agent.py`: consume moved shared prospecting constants.
- `harnessiq/agents/exa_outreach/agent.py`: consume shared ExaOutreach config/constants instead of defining them locally.
- Existing targeted tests under `tests/`: verify each repaired regression and the full package/shared-definition contract.

Approach:
First backport the already-proven ExaOutreach and provider-exception fixes from the prior branches. Then fix the remaining isolated regressions directly in the clean worktree, keeping definition ownership in `harnessiq/shared/` and behavior in the harness modules. Validate with focused suites during iteration and finish with a full `pytest -q` run.

Assumptions:
- The current red set from `pytest -q` is the authoritative scope for "everything broken."
- Shared-definition violations should be resolved by moving or re-exporting definitions through `harnessiq/shared/`, not by weakening the package smoke test.
- The simplest correct fix for the leads regression is to remove the stray constructor path that references undefined symbols, rather than reintroducing an older alternate tool-merge flow.

Acceptance Criteria:
- [ ] All currently failing pytest cases on refreshed `main` pass.
- [ ] `pytest -q` passes cleanly in the implementation worktree.
- [ ] Shared-definition violations in agent modules are eliminated without weakening package smoke coverage.
- [ ] The resulting branch is pushed and a PR targeting `main` is created.

Verification Steps:
- Static analysis: manually review touched Python modules for import hygiene and consistency because no repo linter is configured.
- Type checking: rely on existing annotations plus test execution because no repo type checker is configured.
- Unit tests: run focused failing suites while iterating.
- Integration and contract tests: rerun the affected CLI, shared-model, and package smoke tests.
- Final verification: run full `pytest -q`.

Dependencies:
- None.

Drift Guard:
This ticket must stay a stabilization pass. It must not redesign agent interfaces, alter public CLI semantics beyond fixing regressions, or broaden into unrelated cleanup that is not required to restore the green baseline and satisfy the package shared-definition contract.
