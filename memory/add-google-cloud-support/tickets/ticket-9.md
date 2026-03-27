Title: Add `GcpContext` and package exports
Issue URL: https://github.com/cerredz/HarnessHub/issues/296
PR URL: https://github.com/cerredz/HarnessHub/pull/314

Intent:
Compose the growing GCP provider tree behind one shared context so later CLI and integration code can use a single entry point instead of instantiating providers individually.

Scope:
Add `GcpContext`, grouped provider namespaces, and package exports across `harnessiq/providers/gcloud/`. This ticket does not add the credential bridge or CLI handlers.

Relevant Files:
- `harnessiq/providers/gcloud/context.py`: Add the shared context class and provider namespaces.
- `harnessiq/providers/gcloud/__init__.py`: Export the public GCP provider surface.
- `tests/test_gcloud_context.py`: Verify context construction and namespace composition.

Approach:
Follow the design docâ€™s single-entry-point pattern while adapting it to the repositoryâ€™s explicit dataclass style. `GcpContext` should own one `GcloudClient` and one `GcpAgentConfig`, construct each provider exactly once, and expose factory methods for saved-config and init-time construction.

Assumptions:
- All provider tickets landing first means `GcpContext` can remain a thin composition layer rather than a partial/stub context.
- Package exports should be curated so later CLI code can import from `harnessiq.providers.gcloud` directly where useful.

Acceptance Criteria:
- [ ] `GcpContext` composes the deploy, credentials, infra, storage, and observability namespaces cleanly.
- [ ] `GcpContext.from_config()` loads saved config and constructs a shared client.
- [ ] `GcpContext.from_init()` supports init-time construction before config persistence.
- [ ] Package exports expose the intended public surface without wildcard leakage.
- [ ] Tests verify namespace composition and factory behavior.

Verification Steps:
- Static analysis: No configured linter; manually review imports and ensure no cyclic package dependencies are introduced.
- Type checking: No configured type checker; keep context and namespace dataclasses fully annotated.
- Unit tests: Run `pytest tests/test_gcloud_context.py`.
- Integration and contract tests: Mock config loading and provider constructors as needed.
- Smoke and manual verification: Construct a `GcpContext` in a shell and inspect the available namespaces.

Dependencies:
Ticket 5, Ticket 6, Ticket 7, Ticket 8.

Drift Guard:
Do not add credential syncing or CLI orchestration in this ticket. The goal is only shared provider composition and package-surface cleanup.

