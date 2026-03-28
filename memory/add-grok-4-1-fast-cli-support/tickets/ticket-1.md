Title: Add capability-aware Grok model handling for non-reasoning CLI runs

Issue URL: https://github.com/cerredz/HarnessHub/issues/405

Intent:
Enable `harnessiq run ... --model grok:grok-4.1-fast` to work across manifest-backed agents by teaching the shared Grok model adapter and request builder to distinguish reasoning-capable and non-reasoning model variants. This preserves existing reasoning Grok support while unblocking the user’s target Instagram command and any other harness using the same model-selection path.

Scope:
- Update shared Grok model capability handling in the provider-backed model abstraction.
- Ensure non-reasoning Grok models do not emit invalid `reasoning_effort` request fields.
- Add regression tests for model abstraction, provider payload generation, and the platform-first CLI path.
- Update any directly relevant docs/examples that would otherwise misrepresent supported Grok model usage.
- Do not change Instagram harness business logic, search behavior, sink behavior, or generic model-selection semantics outside Grok capability handling.

Relevant Files:
- `harnessiq/integrations/agent_models.py`: Add Grok capability detection and apply it when constructing requests and model overrides.
- `harnessiq/providers/grok/requests.py`: Keep Grok request emission aligned with the capability-aware model request contract if request shaping needs tightening there.
- `tests/test_agent_models.py`: Cover reasoning and non-reasoning Grok model behavior through the shared adapter.
- `tests/test_grok_provider.py`: Verify payload serialization omits `reasoning_effort` when not applicable.
- `tests/test_platform_cli.py`: Add or update a platform CLI flow that exercises `--model grok:grok-4.1-fast`.
- `docs/agent-runtime.md`: Adjust the model example only if it is necessary to document non-reasoning Grok support explicitly.

Approach:
Introduce one shared helper that classifies Grok model names by whether they support reasoning-specific request fields. Use that helper inside the Grok model adapter so `reasoning_effort` is forwarded only for compatible models, including when the adapter is created from persisted profiles or overridden at runtime. Keep the CLI surface unchanged; the fix should be transparent to all harness adapters because they already consume the shared `AgentModel` contract.

Assumptions:
- `grok-4.1-fast` and the existing hyphenated `grok-4-1-fast` naming should both be accepted as model names passed through the shared provider-backed path.
- Non-reasoning Grok models fail or behave incorrectly when `reasoning_effort` is included, so suppressing that field is the required compatibility change.
- Existing reasoning-capable Grok examples and profiles must remain valid.

Acceptance Criteria:
- [ ] `create_model_from_spec("grok:grok-4.1-fast", ...)` constructs a Grok-backed agent model without rejecting the model name.
- [ ] Shared Grok request generation omits `reasoning_effort` for non-reasoning model variants and preserves it for reasoning-capable variants.
- [ ] The platform-first CLI path for `harnessiq run instagram ... --model grok:grok-4.1-fast` is covered by regression tests.
- [ ] Existing Grok reasoning-path tests continue to pass or are updated without weakening their assertions.
- [ ] Documentation examples remain accurate for supported Grok usage after the change.

Verification Steps:
- Run targeted pytest modules covering shared model adapters, Grok request builders, and platform CLI execution.
- Run any fast lint/static checks configured for the touched Python files.
- Perform a CLI smoke verification that exercises the Instagram platform-first run path with a patched/static model seam or equivalent safe local harness.

Dependencies:
- None.

Drift Guard:
This ticket must not redesign model profiles, add new CLI flags, or introduce agent-specific Grok branching. The change stays in shared Grok capability handling plus the minimum tests/docs needed to prove the behavior. Any request to broaden model catalog management, normalize all provider model aliases globally, or rework provider credential resolution is out of scope for this ticket.
