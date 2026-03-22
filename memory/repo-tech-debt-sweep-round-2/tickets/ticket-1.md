Title: Decompose the shared Resend metadata module behind a compatibility facade

Intent:
Reduce the cognitive load of working in `harnessiq/shared/resend.py` by separating shared Resend models, path-builder helpers, and operation-catalog construction into focused modules while keeping the current shared import surface stable for downstream tool and agent code.

Issue URL: https://github.com/cerredz/HarnessHub/issues/211

Scope:

- Split `harnessiq/shared/resend.py` into smaller focused modules.
- Keep `harnessiq.shared.resend` as the stable import anchor for the existing public names.
- Preserve the Resend operation catalog contents, operation names, shared constants, and `__module__` contracts relied on by package tests.
- Do not expand the supported Resend API surface or change request-validation semantics in the tool layer.

Relevant Files:

- `harnessiq/shared/resend.py`: convert from implementation-heavy module into a compatibility facade re-exporting decomposed shared pieces.
- `harnessiq/shared/resend_models.py`: new module for `ResendCredentials`, `ResendOperation`, `ResendPreparedRequest`, and stable shared constants.
- `harnessiq/shared/resend_paths.py`: new module for reusable path-builder helpers used by catalog entries.
- `harnessiq/shared/resend_catalog.py`: new module for catalog construction, `_RESEND_OPERATION_CATALOG`, `build_resend_operation_catalog()`, and `get_resend_operation()`.
- `tests/test_resend_tools.py`: confirm public Resend behavior still resolves through the shared facade.
- `tests/test_sdk_package.py`: preserve package-surface module ownership expectations.
- `tests/test_email_agent.py`: confirm the email agent continues to work against the stable shared Resend definitions.

Approach:

- Move shared models/constants into one module, path-building helpers into another, and catalog assembly / lookup into a third.
- Keep `harnessiq.shared.resend` as a thin re-export layer so existing imports continue to resolve without caller changes.
- Avoid moving shared classes away from the `harnessiq.shared.resend` public surface in a way that would break `__module__` expectations checked by package tests.
- Preserve operation ordering and names exactly by moving the current catalog data largely verbatim rather than rewriting it.

Assumptions:

- External callers depend on the existing `harnessiq.shared.resend` names but not on private helper function locations.
- `tests/test_sdk_package.py` is the authoritative guard for shared-definition module ownership.
- The current Resend operation catalog on `origin/main` is the source of truth and should remain unchanged in size and naming.

Acceptance Criteria:

- [ ] The shared Resend implementation is split across focused modules with `harnessiq.shared.resend` remaining the stable compatibility surface.
- [ ] Public shared Resend imports continue to resolve without caller changes.
- [ ] The Resend operation catalog size and operation names remain unchanged.
- [ ] Package tests that assert shared-definition ownership continue to pass for the Resend shared types.
- [ ] The resulting `harnessiq/shared/resend.py` file is materially smaller and easier to scan than the current monolith.

Verification Steps:

- Static analysis: run `python -m compileall harnessiq tests`.
- Type checking: no configured type checker; keep extracted modules fully annotated and preserve stable shared type signatures.
- Unit tests: run `.venv\Scripts\pytest.exe -q tests/test_resend_tools.py tests/test_email_agent.py`.
- Integration and contract tests: run `.venv\Scripts\pytest.exe -q tests/test_sdk_package.py` and document any unrelated baseline failure if present.
- Smoke/manual verification: run a short `.venv\Scripts\python.exe` snippet that imports the shared Resend surface from `harnessiq.shared.resend` and confirms the catalog length.

Dependencies:

- None.

Drift Guard:

This ticket is a structure-preserving shared-module refactor. It must not add new Resend operations, change operation metadata, redesign the tool layer, or widen into package-export cleanup beyond what is necessary to preserve the existing shared Resend surface.
