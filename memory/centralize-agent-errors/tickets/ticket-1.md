Title: Centralize agent exception taxonomy

Intent:
Introduce a shared application exception taxonomy for agent-layer failures so validation, missing-resource, and invalid-state errors come from one canonical module instead of being scattered across agent classes.

Scope:
- Add a shared exception module under `harnessiq/shared/`.
- Refactor agent classes to use shared exceptions where they currently raise builtin validation, not-found, and invalid-state errors.
- Keep existing messages and builtin exception-family compatibility intact.
- Add focused tests that verify the new exception types are used.

Scope Exclusions:
- Do not rewrite the entire `harnessiq/shared/` package to replace every builtin exception.
- Do not change agent behavior beyond exception typing.
- Do not change external CLI or HTTP status plumbing.

Relevant Files:
- `harnessiq/shared/exceptions.py` — new centralized application exception taxonomy.
- `harnessiq/shared/__init__.py` — export the shared exception types.
- `harnessiq/shared/providers.py` — align `ProviderFormatError` with the taxonomy.
- `harnessiq/shared/http.py` — align `ProviderHTTPError` with the taxonomy.
- `harnessiq/agents/.../agent.py` — replace ad hoc builtin raises with shared exceptions in agent classes.
- `tests/test_provider_base_agents.py` — verify provider-base agents raise shared validation errors.
- `tests/test_exa_outreach_agent.py` — verify shared validation/not-found/state errors on concrete agent boundaries.
- `tests/test_knowt_agent.py` — verify missing prompt raises the shared not-found error.
- `tests/test_linkedin_agent.py` — verify invalid runtime state raises the shared state error.

Approach:
Create a small base `AppError` hierarchy with subclasses that also inherit from builtin exception families (`ValueError`, `FileNotFoundError`, `RuntimeError`). Use that hierarchy directly in agent classes so the repo gains a central taxonomy without breaking existing tests or consumer `except ValueError` paths.

Assumptions:
- Agent-layer errors are the intended initial adoption surface.
- Existing error message text should remain stable.
- Compatibility with builtin exception categories is required.

Acceptance Criteria:
- [ ] `harnessiq/shared/exceptions.py` defines a centralized application exception hierarchy.
- [ ] Agent classes use shared exceptions for validation, missing-resource, and invalid-state failures.
- [ ] Existing custom provider exceptions align with the shared taxonomy.
- [ ] Targeted tests verify the shared exception types while preserving builtin compatibility.
- [ ] Relevant test subset passes.

Verification Steps:
1. Run the focused agent and provider-base tests covering updated exception paths.
2. Confirm the shared exception types are exported from the shared package.
3. Confirm builtin compatibility through tests that still assert `ValueError`, `FileNotFoundError`, or `RuntimeError`.

Dependencies:
- None.

Drift Guard:
This ticket must stay limited to centralized exception typing for agent classes and adjacent shared exception definitions. It must not expand into repo-wide validation rewrites, behavior changes, or broader architectural changes unrelated to error taxonomy.
