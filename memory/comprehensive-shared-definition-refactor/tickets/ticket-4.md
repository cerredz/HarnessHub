Issue URL: https://github.com/cerredz/HarnessHub/issues/180

Title: Normalize package exports, shared-module coverage, and architectural documentation after the shared-definition refactor

Intent:
Finish the refactor by reconciling package exports, registry/import surfaces, documentation, and tests so the new shared-definition architecture is coherent and enforced across the SDK.

Scope:
- Update package-level exports for any definitions moved during the prior tickets.
- Add or update tests that directly verify shared-definition ownership where valuable.
- Update architectural documentation if the shared-module structure changes meaningfully.
- Run the full targeted verification sweep across agents, providers, tools, and package exports affected by the refactor.
- Do not introduce new provider/tool capabilities or behavioral features.

Relevant Files:
- `harnessiq/shared/__init__.py`: update or preserve any necessary shared-package exports if the refactor warrants it.
- `harnessiq/providers/__init__.py`: preserve package-level provider exports after definition relocation.
- `harnessiq/agents/__init__.py`: reconcile any moved exports after agent-side normalization.
- `harnessiq/tools/__init__.py`: ensure provider-backed tool exports remain stable after provider metadata moves.
- `harnessiq/toolset/catalog.py`: verify catalog/provider wiring still imports through stable package surfaces.
- `artifacts/file_index.md`: update the architectural index if the shared-folder structure changes materially.
- `tests/test_sdk_package.py`: update package-surface assertions if exports shift internally.
- `tests/test_providers.py`: update provider package-surface assertions if exports shift internally.
- `tests/test_tools.py`: update tool-package assertions if provider metadata/export surfaces change.
- `tests/test_toolset_registry.py`: update or expand coverage if provider definition ownership affects registry expectations.

Approach:
Treat this as the integration-and-hardening ticket. The earlier tickets move definition ownership; this ticket ensures the repositoryâ€™s public surfaces, architectural docs, and regression tests accurately reflect the new shared-first layout. Where possible, favor compatibility re-exports instead of breaking import paths.

Assumptions:
- The earlier tickets may introduce new shared modules that need to be reflected in docs and package-surface tests.
- Compatibility re-exports are preferable to forcing downstream consumers to adopt new import paths immediately.

Acceptance Criteria:
- [ ] Public package exports remain coherent after the shared-definition moves.
- [ ] Architectural documentation reflects any meaningful shared-folder structure changes.
- [ ] Regression coverage exists for the most important shared-definition import surfaces.
- [ ] The targeted end-to-end verification sweep for the refactor passes, excluding any unrelated baseline failures explicitly documented during implementation.

Verification Steps:
- Run targeted package-export tests, tool tests, provider tests, and agent tests affected by the refactor.
- Run import smoke checks for `harnessiq`, `harnessiq.agents`, `harnessiq.providers`, `harnessiq.tools`, and `harnessiq.toolset`.
- Document any unrelated baseline failures still present on `origin/main`.

Dependencies:
- Ticket 1
- Ticket 2
- Ticket 3

Drift Guard:
This ticket must not add new capabilities or widen the architectural scope beyond stabilization of the shared-definition refactor. It exists to harden and document the refactor, not to bundle unrelated cleanup.

