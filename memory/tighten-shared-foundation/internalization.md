### 1a: Structural Survey

- Repository shape:
  - `harnessiq/shared/` holds most canonical runtime types, constants, dataclasses, protocols, operation catalogs, and domain memory stores.
  - `harnessiq/providers/` holds provider request translation, authenticated clients, and operation-preparation logic.
  - `harnessiq/tools/` holds executable `RegisteredTool` factories and tool-runtime wiring.
  - `harnessiq/agents/` holds orchestration on top of shared models and tool/provider seams.
  - `harnessiq/cli/` is a transport layer over SDK surfaces, mostly command parsing and persistence wiring.
  - `harnessiq/utils/` holds cross-cutting runtime infrastructure such as agent-instance management, ledger/output sinks, and generic run-storage helpers.
- Technology and conventions:
  - Python 3.11+ package defined in `pyproject.toml`.
  - Tests are pytest/unittest-style modules under `tests/`.
  - The codebase relies heavily on frozen dataclasses, protocols, and explicit `as_dict()` / `from_dict()` serialization at boundaries.
  - Shared/public definitions are expected to originate from `harnessiq/shared/*`; `tests/test_sdk_package.py` already enforces a similar rule for agents/providers not redefining shared classes/constants locally.
- Dependency-direction guidance already documented in repo artifacts:
  - `artifacts/file_index.md` says configs, constants, protocols, dataclasses, memory-store types, and reusable normalization helpers should live in `harnessiq/shared/`.
  - `artifacts/future_changes_to_repo.md` states the target dependency direction is `shared -> stdlib or other shared only`, and explicitly calls out `harnessiq/shared/email.py` importing from `harnessiq.tools.resend` as debt.
- Current `shared/` behavior:
  - Most provider operation catalogs already live in `shared/*` and are consumed downward by `providers/` and `tools/`.
  - Agent domains such as LinkedIn and Prospecting already keep supported runtime-parameter constants and normalization helpers in `shared/`.
  - `shared/` still contains a few upward dependency leaks and some domain normalization logic remains stranded in `cli/`.
- Concrete inconsistencies found during survey:
  - `harnessiq/shared/email.py` imports `ResendCredentials` and `get_resend_operation` from `harnessiq.tools.resend`.
  - `harnessiq/shared/credentials.py` imports `ProviderCredentialConfig` from `harnessiq.config.models`.
  - `harnessiq/shared/exa_outreach.py` imports run-storage types from `harnessiq.utils.run_storage`.
  - `harnessiq/shared/leads.py` imports `FileSystemStorageBackend` from `harnessiq.utils.run_storage`.
  - `harnessiq/cli/leads/commands.py` defines `normalize_leads_runtime_parameters()` and a local platform normalizer even though comparable domain normalization for other agents already lives in `shared/`.
  - `harnessiq/cli/exa_outreach/commands.py` defines `normalize_exa_outreach_runtime_parameters()` instead of keeping that domain normalization with the shared outreach config/memory models.

### 1b: Task Cross-Reference

- User intent: make `shared/` a true foundation layer, remove downward leaks from higher layers, and avoid layer overlap where `providers`, `tools`, `cli`, `agents`, or SDK façades implement logic that belongs in `shared/`.
- Files directly implicated by the audit:
  - `harnessiq/shared/email.py`: fix the upward import into `tools/`.
  - `harnessiq/shared/credentials.py` and `harnessiq/config/models.py`: move the base credential config contract into a shared-owned home and leave `config/` as a façade.
  - `harnessiq/shared/exa_outreach.py`, `harnessiq/shared/leads.py`, `harnessiq/utils/run_storage.py`: move generic run-storage ownership into `shared/` and keep `utils/` as compatibility/export surface if needed.
  - `harnessiq/cli/exa_outreach/commands.py`, `harnessiq/cli/leads/commands.py`: remove CLI-owned runtime-parameter normalization that belongs beside shared domain models.
  - `harnessiq/cli/leads/__init__.py` and any public façades that re-export CLI helpers: preserve compatibility while pointing at shared-owned logic.
  - `tests/test_sdk_package.py`: add a mechanical architecture check so `shared/` cannot import non-shared Harnessiq packages again.
  - `tests/test_leads_cli.py`, `tests/test_exa_outreach_cli.py`, and possibly shared-package smoke tests: verify the re-exported runtime-parameter helpers still behave the same after ownership moves.
- Existing behavior that must be preserved:
  - Public imports used by tests and callers, especially `harnessiq.config.ProviderCredentialConfig`, `harnessiq.utils.{RunRecord,StorageBackend,FileSystemStorageBackend,RUNS_DIRNAME}`, `harnessiq.shared.exa_outreach.*`, and CLI module exports for runtime-parameter helpers.
  - Leads and outreach CLI argument parsing and coercion semantics.
  - Existing provider/tool/agent runtime behavior and tests.
- Blast radius:
  - Medium. The changes are architectural and touch multiple public import surfaces, but they are localized to foundational definitions and should be low-risk if compatibility façades remain in place.

### 1c: Assumption & Risk Inventory

- Assumption: the target state allows low-level reusable storage primitives to live in `shared/` when they are foundational and consumed by multiple domains. This is consistent with current `shared/` memory-store patterns and removes the current `shared -> utils` dependency leak.
- Assumption: preserving existing import paths via façade/re-export modules is preferable to breaking callers while tightening ownership.
- Assumption: runtime-parameter coercion for leads and exa outreach is domain normalization, not CLI-specific behavior, because the repo already treats equivalent logic that way for LinkedIn and Prospecting.
- Risk: moving foundational definitions can accidentally change `__module__` origins or public imports. Tests should explicitly guard the intended ownership and compatibility surfaces.
- Risk: a naive architecture test could forbid legitimate `shared -> shared` imports. The enforcement should only reject `shared` imports from non-shared `harnessiq.*` namespaces.
- Risk: the worktree is dirty with unrelated user changes (`README.md`, `artifacts/file_index.md`, memory artifacts, prompt files, temp files). Implementation must avoid reverting or depending on those unrelated changes.

Phase 1 complete.
