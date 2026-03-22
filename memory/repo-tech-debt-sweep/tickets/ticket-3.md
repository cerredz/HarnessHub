Title: Split the Resend tooling module into focused API, catalog, and facade layers

Intent:
Reduce the cognitive load of working in `harnessiq/tools/resend.py` by separating the Resend credential/client logic, operation catalog, and tool-factory surface into smaller modules while preserving the current public API.

Issue URL: https://github.com/cerredz/HarnessHub/issues/206

Scope:

- Decompose the current `harnessiq/tools/resend.py` implementation into focused modules.
- Preserve the public names currently imported from `harnessiq.tools` and `harnessiq.tools.resend`.
- Keep the operation catalog, request preparation rules, and tool definition behavior unchanged.
- Do not add new Resend API operations as part of this ticket.

Relevant Files:

- `harnessiq/tools/resend.py`: convert into a smaller compatibility facade re-exporting the decomposed implementation.
- `harnessiq/tools/resend_client.py`: new module for `ResendCredentials`, `ResendPreparedRequest`, and `ResendClient`.
- `harnessiq/tools/resend_catalog.py`: new module for `ResendOperation`, catalog construction, operation lookup, and catalog-specific validators/builders.
- `harnessiq/tools/resend_tool.py`: new module for the tool-definition and `create_resend_tools()` factory surface.
- `harnessiq/tools/__init__.py`: preserve public exports against the new internal module layout.
- `tests/test_resend_tools.py`: confirm the public Resend surface and behavior remain unchanged.
- `tests/test_tools.py`: confirm package-level exports still resolve correctly if needed.

Approach:

- Keep `resend.py` as the stable import surface while moving implementation details into focused sibling modules.
- Separate concerns cleanly:
  - client/credentials/request preparation
  - operation catalog metadata
  - tool-definition/factory wiring
- Preserve stable constants and public class/function names to avoid API churn.
- Add or update tests only where needed to prove import compatibility and unchanged behavior.

Assumptions:

- Existing Resend tests capture the important supported behaviors for request preparation and tool execution.
- No external caller depends on private helper function locations inside `resend.py`.
- The current `harnessiq.tools` export surface should continue to expose the same Resend symbols after the refactor.

Acceptance Criteria:

- [ ] The Resend implementation is split into smaller focused modules with `harnessiq/tools/resend.py` remaining as a compatibility facade.
- [ ] Existing public imports for Resend classes, constants, and factory functions continue to work.
- [ ] The Resend operation catalog size and supported operation names remain unchanged.
- [ ] The Resend tool test suite passes after the refactor.
- [ ] The new structure makes it possible to edit catalog/client/tool-factory concerns independently without opening one large file.

Verification Steps:

- Static analysis: run `python -m compileall harnessiq tests`.
- Type checking: no configured type checker; keep the extracted modules fully annotated and verify re-export imports remain coherent.
- Unit tests: run `.venv\Scripts\pytest.exe -q tests/test_resend_tools.py tests/test_tools.py`.
- Integration and contract tests: run `.venv\Scripts\pytest.exe -q tests/test_sdk_package.py` if the unrelated repo-root packaging baseline is not blocking; otherwise document the baseline issue and run the touched tool suites.
- Smoke/manual verification: run a short `.venv\Scripts\python.exe` snippet that imports the Resend public API from `harnessiq.tools` and `harnessiq.tools.resend`.

Dependencies:

- None.

Drift Guard:

This ticket is about module decomposition and readability, not feature expansion. It must not expand the supported Resend API surface, rename public symbols, or alter how callers construct credentials, clients, or the request tool.
