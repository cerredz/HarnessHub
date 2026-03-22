Title: Fix provider HTTP exception traceback propagation

Issue URL:
https://github.com/cerredz/HarnessHub/issues/197

Intent:
Ensure Instagram and any other provider-backed harness preserves the original `ProviderHTTPError` when a traced model call fails, instead of masking it with `TypeError("super(type, obj): obj must be an instance or subtype of type")`.

Scope:
Change the shared provider HTTP exception implementation to be safe for normal Python exception propagation, and add regression tests covering traced propagation of provider HTTP failures. Do not change Instagram search logic, Grok request semantics, or LangSmith feature scope beyond what is required to preserve the correct exception.

Relevant Files:
- `harnessiq/shared/http.py`: replace the fragile dataclass-based provider HTTP exception with a normal runtime exception implementation that preserves the existing public fields and string formatting.
- `tests/test_provider_base.py`: extend provider exception coverage to assert traceback assignment/propagation safety without weakening the existing request_json contract assertions.
- `tests/test_providers.py`: add tracing regression coverage so `trace_model_call` preserves `ProviderHTTPError` and does not surface the secondary `TypeError`.

Approach:
Implement `ProviderHTTPError` as a conventional exception class with an explicit `__init__` and stable instance attributes. Keep `provider`, `message`, `status_code`, `url`, and `body` as public attributes and preserve `__str__` output to minimize blast radius. Then add a unit test that directly exercises traceback assignment on the exception instance and a tracing-layer regression test that raises `ProviderHTTPError` inside `trace_model_call`, confirming the original exception type/message/status survive tracing.

Assumptions:
- No production code depends on dataclass-generated equality or repr for `ProviderHTTPError`.
- The correct outcome for the reproduced Grok failure is still a raised `ProviderHTTPError( provider='grok', status_code=403, ... )`.
- Existing tracing behavior of recording `run_tree.end(error=...)` should remain unchanged.

Acceptance Criteria:
- [ ] `ProviderHTTPError` instances allow normal traceback propagation and do not raise `TypeError` when Python assigns `__traceback__`.
- [ ] `request_json` still raises `ProviderHTTPError` with the same public fields and string format for HTTP and URL failures.
- [ ] `trace_model_call` preserves `ProviderHTTPError` when the wrapped provider operation fails.
- [ ] New regression tests cover both the exception object behavior and the tracing propagation path.
- [ ] The targeted provider and tracing test suites pass on the implementation branch.

Verification Steps:
1. Run static checks available for the changed Python files; if no linter is configured, verify style manually and document that no repo-wide linter is configured for this slice.
2. Run type-oriented verification available for the changed files; if no type checker is configured, verify new code is fully annotated where appropriate and document the absence of a configured checker.
3. Run `python -m unittest tests.test_provider_base tests.test_providers`.
4. Run a smoke reproduction that raises `ProviderHTTPError` and assigns `exc.__traceback__`, confirming it no longer fails.
5. If possible, rerun the Instagram Grok path far enough to confirm the masked `TypeError` is gone even if the upstream `403` remains.

Dependencies:
- None.

Drift Guard:
Do not broaden this ticket into fixing Grok authentication, LangSmith configuration, or unrelated Instagram agent behavior. The only acceptable behavioral change is that provider-backed traced failures now surface the original `ProviderHTTPError` cleanly, with regression coverage proving that outcome.
