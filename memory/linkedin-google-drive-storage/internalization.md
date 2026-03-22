### 1a: Structural Survey

Repository shape and stack:

- The repo is a Python 3.11+ SDK package (`pyproject.toml`) built with setuptools and tested with `unittest`-style test modules executed through `pytest`.
- Production code lives under `harnessiq/` and is split into agent harnesses (`harnessiq/agents/`), CLI entrypoints (`harnessiq/cli/`), credential/config helpers (`harnessiq/config/`), provider clients and request builders (`harnessiq/providers/`), reusable shared models/constants (`harnessiq/shared/`), tool factories (`harnessiq/tools/`), and static toolset metadata/dispatch (`harnessiq/toolset/`).
- Provider HTTP traffic uses stdlib `urllib` helpers from `harnessiq/providers/http.py`; provider packages generally follow a stable pattern:
  - credentials/client dataclasses in `harnessiq/providers/<provider>/client.py`
  - API constants/header helpers in `harnessiq/providers/<provider>/api.py`
  - declarative operation catalog + MCP-style tool factory in `harnessiq/providers/<provider>/operations.py` or `harnessiq/tools/<provider>/operations.py`
  - re-exports in `__init__.py`
- Tool discovery for the public toolset is static and explicit in `harnessiq/toolset/catalog.py`; adding a new provider family requires both metadata and a lazy factory entry.

Agent runtime architecture:

- `harnessiq/agents/base/agent.py` defines `BaseAgent`, a provider-agnostic run loop that:
  - prepares durable state once per run
  - rebuilds parameter sections on reset
  - records assistant turns, tool calls, and tool results into transcript history
  - pauses only when a tool returns `AgentPauseSignal`
- Durable state is injected through `AgentParameterSection` instances from `harnessiq/shared/agents.py`.
- Agents are expected to make deterministic side effects inside tool handlers, not via post-processing after the run loop.

LinkedIn agent architecture:

- `harnessiq/agents/linkedin/agent.py` contains both `LinkedInMemoryStore` and `LinkedInJobApplierAgent`.
- The LinkedIn memory model is file-backed and append-oriented:
  - `job_preferences.md`
  - `user_profile.md`
  - `agent_identity.md`
  - `runtime_parameters.json`
  - `custom_parameters.json`
  - `additional_prompt.md`
  - `applied_jobs.jsonl`
  - `action_log.jsonl`
  - `managed_files.json`
  - `managed_files/`
  - `screenshots/`
- Successful or skipped application state is currently persisted only through internal LinkedIn tools:
  - `linkedin.append_company`
  - `linkedin.update_job_status`
  - `linkedin.mark_job_skipped`
  - `linkedin.append_action`
- `linkedin.append_company` is the current deterministic write point for a successful application; it appends a `JobApplicationRecord` to `applied_jobs.jsonl` immediately from the tool handler.

CLI architecture:

- Top-level CLI wiring is in `harnessiq/cli/main.py`; only `linkedin` and `exa_outreach` command groups are currently registered.
- `harnessiq/cli/linkedin/commands.py` manages per-agent memory folders and run-time execution.
- LinkedIn runtime overrides flow through `runtime_parameters.json` and `normalize_linkedin_runtime_parameters()`.
- There is no existing CLI for the generic credentials config store, even though `harnessiq/config/credentials.py` provides the persistence/resolution layer.

Credential/config architecture:

- `harnessiq/config/credentials.py` persists named agent credential bindings in `.harnessiq/credentials.json` and resolves real values from repo-local `.env`.
- This layer is generic and agent-oriented, not provider-family-specific. It can support “this logical agent needs these env-backed fields” without exposing secrets in checked-in config.
- `harnessiq/shared/credentials.py` currently centralizes TypedDict-style credential schemas for several non-LLM data providers.

Tests and conventions:

- Tests are concentrated in `tests/` and generally cover constructors, validation, tool factories, CLI behavior, and deterministic storage side effects.
- Existing provider tests validate:
  - credential validation
  - request preparation
  - tool factory behavior with fake executors/clients
  - clear failures when credentials are missing
- Existing LinkedIn tests validate:
  - memory bootstrap and parameter-section injection
  - append/update behavior for application state
  - CLI configure/show/run flows
- No linter or dedicated type checker is configured in `pyproject.toml`; quality gates in this repo are primarily test-driven plus idiomatic type annotations.

Observed inconsistencies or noteworthy details:

- `README.md` still documents some LinkedIn memory filenames as `.txt`, while the code uses `.md` for several files.
- `artifacts/file_index.md` mentions `harnessiq/cli/config/`, but that directory does not currently exist in the working tree; the actual CLI surface is only `linkedin` and `exa_outreach`.
- There is a stray temp file at `harnessiq/cli/main.py.tmp.18928.1773720913059`, which appears unrelated to the feature request and should not be touched unless it becomes necessary.

### 1b: Task Cross-Reference

User request decomposition:

1. Add a “google drive” provider that connects to the Google Drive API using user credentials.
   Mapping:
   - New provider package(s) under `harnessiq/providers/google_drive/` and/or `harnessiq/tools/google_drive/`
   - Credential schema extension in `harnessiq/shared/credentials.py` or a provider-local credentials module
   - Possible toolset registration in `harnessiq/toolset/catalog.py` if this provider should be available through the global toolset
   - Tests analogous to other provider families in `tests/test_google_drive_provider.py`

2. When the LinkedIn agent successfully applies for a job, store company/job information both in agent memory and in the user’s Google Drive.
   Mapping:
   - The existing deterministic local write point is `LinkedInJobApplierAgent._handle_append_company()` in `harnessiq/agents/linkedin/agent.py`
   - Shared job record structure currently lives in `harnessiq/shared/linkedin.py` as `JobApplicationRecord`, but it does not contain all requested fields (`job description`, `salary`, `location`, etc.)
   - If Google Drive persistence is required only after success, the likely implementation anchor is augmenting or replacing the logic behind `linkedin.append_company`
   - Additional durable local memory may require:
     - extending `JobApplicationRecord`
     - adding a second append-only artifact for richer job details
     - or storing richer structured files in `managed_files/`

3. “Store that company’s information (title, job description, salary, location, etc) … inside of the user google drive via a folder name.”
   Mapping:
   - Requires a deterministic remote storage contract that does not exist yet
   - Likely needs:
     - folder naming/sanitization logic
     - a canonical document/file payload for the job metadata
     - duplicate-handling semantics when the same job/company is applied to more than once
   - The current repo has no Google Drive-specific abstraction, so all of this is net-new

4. Make saving to Google Drive optional and default it to `false`.
   Mapping:
   - The LinkedIn agent already has persisted runtime parameters via `runtime_parameters.json` and normalization in `normalize_linkedin_runtime_parameters()`
   - `SUPPORTED_LINKEDIN_RUNTIME_PARAMETERS` is the current allowlist; a new `save_to_google_drive`-style runtime parameter can fit this existing mechanism
   - CLI support would need to flow through:
     - `harnessiq/cli/linkedin/commands.py`
     - docs for `linkedin configure` / `linkedin run`
     - tests in `tests/test_linkedin_cli.py`

5. “The actually saving process should be deterministic after the agent successfully applies to a job.”
   Mapping:
   - The repo’s deterministic pattern is to place side effects inside tool handlers, not in model-authored prose or in background reconciliation
   - The cleanest cross-reference is:
     - keep `linkedin.append_company` as the single “successful application committed” event
     - have that handler perform both local append and optional Drive persistence synchronously
   - This implies the handler may need access to resolved Google credentials/client configuration during agent construction

Blast radius:

- LinkedIn shared models and runtime parameter normalization
- LinkedIn agent construction and internal tool handlers
- Possibly LinkedIn CLI configure/show/run surfaces
- New provider/client/tool files for Google Drive
- Shared credential definitions/config resolution helpers if Google credentials are persisted through repo-local `.env`
- Tests for provider, agent, and CLI behavior
- Documentation and `artifacts/file_index.md` if a meaningful new structural folder is added

Behavior that must be preserved:

- Existing LinkedIn runs without Google Drive configuration must continue to behave exactly as they do today
- Local append-only job logging in `applied_jobs.jsonl` must remain deterministic
- `LinkedInJobApplierAgent.from_memory()` must still support persisted CLI state
- Existing provider/toolset families must remain untouched unless Google Drive is intentionally added to the global catalog

### 1c: Assumption & Risk Inventory

Primary unresolved assumptions:

- “User’s credentials” is ambiguous.
  - It could mean OAuth access token + refresh token for a real Google account.
  - It could mean an API key, which is insufficient for Drive writes.
  - It could mean a service account, which is not the same as the user’s own Drive unless sharing/delegation is configured.
- The repo currently has no OAuth callback flow, token refresh persistence, or browser-based Google auth helper for Drive. Building one is materially different from accepting pre-provisioned tokens from `.env`.
- “Via a folder name” is ambiguous.
  - It could mean create one folder per application and write metadata files inside it.
  - It could mean create a single folder named after the company and attach a document inside it.
  - It could mean only store the metadata in the folder name itself, which is too lossy for the requested fields.
- The requested stored fields exceed the current `JobApplicationRecord` shape. It is unclear whether the canonical local memory record should be expanded, or whether richer metadata should live in a parallel artifact.
- The moment of “successful application” is modeled today by the agent choosing to call `linkedin.append_company`. If the browser/model misuses the tool, the handler cannot independently verify LinkedIn actually submitted the application.

Implementation risks:

- If Google Drive persistence is performed directly in `linkedin.append_company`, transient Google API failures could either:
  - fail the whole tool call after the local append, creating partial success semantics
  - or be swallowed, weakening the “deterministic” requirement
- If the remote storage contract is folder-name-driven, sanitization and collision handling must be explicitly defined to avoid nondeterministic folder duplication.
- If Google OAuth refresh is required, storing long-lived refresh tokens in `.env` is feasible but needs an explicit product decision.
- If Google Drive support is added to the public toolset catalog, that widens surface area beyond the LinkedIn feature and increases maintenance scope.
- Documentation currently lags code in a few places; this feature will need disciplined doc updates to avoid increasing drift.

Recommended implementation direction based on current architecture:

- Keep the feature scoped to the LinkedIn agent first.
- Use the existing runtime-parameter path for the `save_to_google_drive` boolean.
- Keep the deterministic trigger at the successful-application tool handler.
- Resolve Google auth through the existing repo-local credential binding + `.env` pattern if the user is willing to supply OAuth tokens/client fields out of band, instead of building a full interactive OAuth flow in the first pass.

Phase 1 complete.
