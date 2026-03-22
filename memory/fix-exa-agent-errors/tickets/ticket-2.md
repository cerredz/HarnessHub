Title: Restore provider HTTP error propagation through tracing
Issue URL: https://github.com/cerredz/HarnessHub/issues/200

Intent:
Fix the provider failure path so real HTTP/provider errors remain the surfaced exception when traced model or tool calls fail. This restores debuggability for Exa/xAI and any other provider using the shared HTTP layer, instead of masking provider failures behind a secondary traceback-assignment `TypeError`.

Scope:
This ticket updates the shared provider error/tracing path and adds regression coverage for the exception propagation behavior. It does not make unauthorized credentials succeed, alter provider request payloads, or change business logic in any specific agent.

Relevant Files:
- `harnessiq/providers/http.py`: adjust `ProviderHTTPError` so it behaves correctly as an exception during re-raise and traceback handling.
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
- [ ] A targeted regression test covers the previous “provider error masked by secondary traceback TypeError” path.

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
