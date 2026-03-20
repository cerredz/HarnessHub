Title: Restore provider HTTP error propagation through tracing
Issue URL: https://github.com/cerredz/HarnessHub/issues/200

Intent:
Fix the provider failure path so real HTTP/provider errors remain the surfaced exception when traced model or tool calls fail. This restores debuggability for Exa/xAI and any other provider using the shared HTTP layer, instead of masking provider failures behind a secondary traceback-assignment `TypeError`.

Scope:
This ticket updates the shared provider error/tracing path and adds regression coverage for the exception propagation behavior. It does not make unauthorized credentials succeed, alter provider request payloads, or change business logic in any specific agent.

Relevant Files:
- `harnessiq/shared/http.py`: adjust `ProviderHTTPError` so it behaves correctly as an exception during re-raise and traceback handling.
- `harnessiq/providers/http.py`: confirm the shared exception import path continues to work after the fix.
- `harnessiq/providers/langsmith.py`: validate whether any defensive normalization is needed around traced exception paths after the exception-class fix.
- `tests/test_providers.py`: add or update regression coverage proving traced provider failures preserve the original provider exception type and details.

Approach:
The prior smoke run showed a provider `403` being followed by a `TypeError` during exception unwinding. `ProviderHTTPError` is currently implemented as a frozen dataclass subclassing `RuntimeError`, which is incompatible with normal traceback mutation on exceptions. The implementation should make the exception class safe for normal Python exception mechanics while preserving the current fields and string formatting. Then add regression tests at the tracing boundary so a traced provider/model call that raises `ProviderHTTPError` still surfaces `ProviderHTTPError` with the original status/message intact.

Assumptions:
- The root cause of the secondary traceback failure is exception immutability, not malformed tracing metadata.
- Existing provider callers expect `ProviderHTTPError` fields (`provider`, `message`, `status_code`, `url`, `body`) and its current `__str__` output to remain stable.
- A mocked tracing boundary in `tests/test_providers.py` is sufficient to cover the regression without calling live external APIs.

Acceptance Criteria:
- [ ] A provider failure raised from the shared HTTP layer remains a `ProviderHTTPError` when propagated through traced model/tool/agent execution.
- [ ] The original provider name, status code, and message remain available after the fix.
- [ ] No existing provider or tracing tests regress.
- [ ] A targeted regression test covers the previous provider error being masked by a secondary traceback `TypeError` path.

Verification Steps:
1. Run the configured linter/static-analysis step for the changed Python files if one exists; otherwise document that no project linter is configured and perform manual style review.
2. Run the configured type checker for the changed files if one exists; otherwise document that no project type checker is configured and confirm any new code remains fully annotated/idiomatic.
3. Run `python -m pytest tests/test_providers.py -q`.
4. Run at least one provider-focused smoke test that triggers a controlled `ProviderHTTPError` path without requiring live credentials, and confirm the surfaced exception type/message are unchanged.
5. Rerun any adjacent provider tests touched by the implementation if needed.

Dependencies:
- None.

Drift Guard:
This ticket must not change provider authentication semantics, request payload schemas, or external API integrations. It is limited to exception propagation correctness and regression coverage for the shared HTTP/tracing path.


## Quality Pipeline Results
Stage 1 - Static Analysis

- No project linter or standalone static-analysis tool is configured in `pyproject.toml`.
- Manually reviewed the changed files for exception semantics, import cleanliness, and consistency with existing tracing-test patterns.
- Result: pass.

Stage 2 - Type Checking

- No project type checker is configured in `pyproject.toml`.
- Verified the change does not introduce new untyped interfaces and preserves the existing `ProviderHTTPError` field contract.
- Result: pass.

Stage 3 - Unit Tests

- Ran `C:\\Users\\Michael Cerreto\\HarnessHub\\.venv\\Scripts\\python.exe -m pytest tests/test_providers.py -q`
- Observed: `11 passed in 0.15s`, including the new regression tests for traceback assignment and traced `ProviderHTTPError` re-raise.
- Result: pass.

Stage 4 - Integration & Contract Tests

- Ran `C:\\Users\\Michael Cerreto\\HarnessHub\\.venv\\Scripts\\python.exe -m pytest tests/test_provider_base.py -q`
- Observed: `19 passed in 0.17s`
- This validates adjacent provider error handling behavior outside the LangSmith tracing helpers.
- Additional note: `tests/test_sdk_package.py -q` still fails on refreshed `main` with pre-existing shared-definition placement violations in `harnessiq/agents/exa_outreach/agent.py` and `harnessiq/agents/prospecting/agent.py`. That failure reproduced unchanged in the untouched `main` worktree and is outside this ticket's scope.
- Result: pass for relevant adjacent provider contract coverage; unrelated baseline failure documented.

Stage 5 - Smoke & Manual Verification

- Ran an inline smoke script that:
  - constructed a real `ProviderHTTPError(provider='grok', message='Forbidden', status_code=403)`,
  - verified `exc.__traceback__ = None` no longer raises `TypeError`,
  - raised that same exception through `trace_model_call(...)` using a mocked LangSmith module,
  - confirmed the surfaced exception type remained `ProviderHTTPError`,
  - confirmed the rendered message remained `grok request failed (403): Forbidden`,
  - confirmed `status_code` remained `403`.
- Result: pass.


## Post-Critique Changes
Self-critique findings:

- The initial implementation fixed the runtime behavior and tests, but the ticket artifact still pointed at `harnessiq/providers/http.py` as the primary edit location. On refreshed `main`, `ProviderHTTPError` actually lives in `harnessiq/shared/http.py`, so the planning document needed to match the real code boundary.
- The provider regression is most convincing when both the tracing tests and the adjacent provider-base tests stay green after the change. I reran both suites after the documentation correction to make sure the final branch state still reflects that.

Post-critique changes made:

- Updated `memory/fix-exa-agent-errors/tickets/ticket-2.md` so the Relevant Files section points at `harnessiq/shared/http.py` as the actual source of the exception-class fix, while keeping `harnessiq/providers/http.py` listed as the import boundary to verify.
- Re-ran `C:\\Users\\Michael Cerreto\\HarnessHub\\.venv\\Scripts\\python.exe -m pytest tests/test_providers.py tests/test_provider_base.py -q`.
- Observed: `19 passed in 0.22s`.
