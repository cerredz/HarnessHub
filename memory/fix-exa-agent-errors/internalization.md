### 1a: Structural Survey

Top-level architecture:

- `harnessiq/` is the shipped Python SDK. It is organized by runtime layer rather than by product surface: `agents/` for harness implementations, `cli/` for command dispatch and per-agent command families, `config/` for repo-local credential loading, `integrations/` for model/browser adapters, `providers/` for HTTP/provider clients and tracing helpers, `shared/` for cross-cutting dataclasses/protocols/constants, `tools/` for executable tool registries, `toolset/` for composable tool bundles, and `utils/` for durable infra such as run storage, agent-instance persistence, and ledger sinks.
- `tests/` is a flat pytest-style suite organized primarily by runtime surface (`test_exa_outreach_agent.py`, `test_exa_outreach_cli.py`, `test_exa_provider.py`, `test_providers.py`, etc.). The suite mixes unit tests, API-shape tests, and narrow integration-style tests against internal module boundaries.
- `docs/` and `artifacts/` document the public SDK/CLI and the intended architecture. `artifacts/file_index.md` is the repo’s structural source of truth.
- `memory/` stores planning and implementation artifacts for prior tasks. The repository already uses this directory as a durable engineering notebook, which aligns with the requested skill workflow.

Technology stack and tooling:

- Python 3.11+ package managed by `setuptools` via `pyproject.toml`.
- Runtime dependency is intentionally light in `pyproject.toml`; `langsmith` is currently the only declared dependency there.
- Test execution uses `pytest` from the local virtual environment rather than a globally installed toolchain.
- No linter or dedicated type checker is declared in `pyproject.toml`. Existing code relies on idiomatic typing and test coverage rather than enforced static tooling.

Data flow and runtime conventions:

- Agent execution is centered on `harnessiq.agents.base.BaseAgent`. A concrete harness supplies a system prompt, durable parameter sections, and a tool executor; `BaseAgent` owns the run loop, transcript, context resets, and ledger emission.
- Tools are registered through `ToolRegistry` and invoked by model-generated `ToolCall` records. Tool definitions are exposed to the model through `ToolDefinition`.
- Durable run persistence is increasingly being standardized via `harnessiq.utils.run_storage`. That module defines a generic `StorageBackend` protocol with `start_run`, `finish_run`, `log_event`, `has_seen`, and `current_run_id`, plus a filesystem implementation that writes `RunRecord` JSON files under `memory_path/runs/`.
- Exa outreach durable memory is split: `harnessiq.shared.exa_outreach` owns the agent’s memory files (`query_config.json`, `agent_identity.txt`, `additional_prompt.txt`) and reconstructs outreach-specific views (`OutreachRunLog`) from the generic `RunRecord` event log written by `run_storage`.
- Provider wrappers are intentionally thin. `harnessiq.providers.http.request_json` centralizes HTTP execution and raises `ProviderHTTPError` on HTTP/transport failures. Provider-specific clients such as `harnessiq.providers.exa.client.ExaClient` and `harnessiq.providers.grok.client.GrokClient` build request payloads and delegate transport to `request_json`.
- LangSmith tracing is wrapped by `harnessiq.providers.langsmith`. Runtime layers call `trace_agent_run`, `trace_model_call`, and `trace_tool_call` around sync/async operations.

Test strategy and conventions:

- Unit tests assert on concrete behavior and serialized artifacts, not just object construction.
- Exa outreach tests cover construction, tool registration, tool-handler behavior, persistence on disk, CLI behavior, and public exports.
- Provider/tracing tests in `tests/test_providers.py` mock the LangSmith boundary to verify trace metadata and error reporting without making network calls.
- Tests commonly use `MagicMock`-based fakes rather than elaborate fixtures, which keeps most behavioral seams explicit in each test file.

Naming, error-handling, and interface conventions:

- Shared dataclasses and protocols live under `harnessiq.shared.*` or `harnessiq.utils.*`; concrete harnesses and clients are thin wrappers around those contracts.
- Methods that perform deterministic writes are expected to do so directly in tool handlers rather than relying on model behavior.
- Public CLI commands emit machine-readable JSON to stdout.
- The codebase prefers small helper functions over deep inheritance trees outside the agent base class.

Relevant inconsistencies observed during survey:

- The target implementation baseline is refreshed `main`, not the user’s dirty feature branch. On `main`, `harnessiq.shared.exa_outreach` still defines an outreach-specific `StorageBackend` with methods such as `is_contacted`, `log_lead`, and `log_email_sent`, while `harnessiq.agents.exa_outreach.agent` calls `has_seen` and `log_event`. That contract drift is the direct cause of the ExaOutreach failures observed on `main`.
- `ProviderHTTPError` in `harnessiq.providers.http` is a frozen dataclass subclassing `RuntimeError`. Exception instances need mutable traceback assignment during propagation; freezing exception state is risky and can corrupt error handling during re-raise/unwind.
- `BaseAgent._execute_tool()` converts any tool exception into a `ToolResult(output={"error": ...})`. This is a deliberate resilience choice, but it also means agent runs can report `completed` while important deterministic side effects never occurred. Tests therefore need to assert on persisted artifacts, not just terminal status.

### 1b: Task Cross-Reference

User request:

- “fix the errors described above” after the prior investigation established:
  - `main` was up to date.
  - ExaOutreach tests on `main` were failing because the harness and storage contract diverged.
  - A provider failure path involving Grok/LangSmith/HTTP surfaced a `TypeError` during exception unwinding instead of preserving the original provider error.
  - External Exa/xAI credentials returned upstream `403` responses, which is an environment/account issue rather than an internal code defect.

Concrete code surfaces touched by this task on refreshed `main`:

- `harnessiq/agents/exa_outreach/agent.py`
  - Internal tool handlers `_handle_check_contacted`, `_handle_log_lead`, and `_handle_log_email_sent` currently talk directly to the generic run-storage backend API.
  - `prepare()` seeds run metadata. That metadata must remain compatible with `ExaOutreachMemoryStore.read_run()` and the CLI/test expectations.
  - This module is the primary source of the ExaOutreach regressions previously observed.
- `harnessiq/shared/exa_outreach.py`
  - Owns the outreach-specific memory store and still carries the stale outreach-specific `StorageBackend`/`FileSystemStorageBackend` implementation on `main`.
  - Any fix must either realign this module to the generic run-storage contract or realign the agent to this local contract; the earlier failures show the current hybrid state is broken.
- `harnessiq/utils/run_storage.py`
  - Provides the generic backend contract used by newer code in the dirty feature branch. It is a strong reference point for the correct target shape even if `main` has not yet fully adopted it.
- `harnessiq/providers/http.py`
  - Defines `ProviderHTTPError`, which surfaced the traceback-assignment `TypeError` when provider calls failed.
- `harnessiq/providers/langsmith.py`
  - Relevant to the provider failure path because tracing wraps provider/model/tool calls. The most likely fix is in exception mutability, but this module is part of the blast radius and should be regression-tested.
- `tests/test_exa_outreach_agent.py`
  - Must be updated or validated to match the intended ExaOutreach/storage contract.
  - This test file already exercises the exact regressions reported earlier.
- `tests/test_exa_outreach_cli.py`
  - Guards the CLI path that constructs and runs `ExaOutreachAgent`.
  - Important because the previous smoke run showed “completed” status can mask tool-side persistence failures.
- `tests/test_providers.py`
  - Existing LangSmith tracing tests are the right place to add coverage for provider exception propagation if a regression test is needed.

Behavior that must be preserved:

- ExaOutreach still needs deterministic lead/email logging inside tool handlers.
- ExaOutreach memory layout (`query_config.json`, identity/additional prompt files, `runs/run_N.json`) must remain stable.
- The CLI `outreach run` command must keep emitting structured JSON and continue accepting factory-based dependency injection.
- Provider HTTP failures must still raise `ProviderHTTPError`; the fix must preserve the original status code/message rather than replacing them.

Behavior that does not appear fixable in code alone:

- Direct Exa and xAI `403 Forbidden` responses from the current `.env` credentials. The code can preserve and surface these errors correctly, but it cannot make invalid or unauthorized external credentials succeed.

Blast radius:

- Moderate and well-bounded.
- ExaOutreach changes are localized to the outreach harness, its shared memory contract, and the outreach tests/CLI tests.
- The provider error fix is cross-cutting because `ProviderHTTPError` is shared by multiple providers, so any change to its class shape should be validated against existing provider and tracing tests.

### 1c: Assumption & Risk Inventory

Assumptions:

- The user wants code defects fixed on the branch that was explicitly verified earlier: refreshed `main`. Credential rotation and external account debugging are out of scope.
- The dirty feature branch is not the implementation baseline. It already contains partial refactors beyond `main`, so implementation should happen in fresh worktrees created from updated `main`.
- The skill workflow’s GitHub issue/PR steps are expected to be executed if local context allows it. The repo has an authenticated `origin`, but that still depends on `gh` authentication succeeding.

Risks:

- ExaOutreach has active in-flight refactors in this dirty worktree. Implementing directly on the current branch would risk mixing unrelated user changes with this task. The safe path is to plan in the current tree, then implement in a fresh issue worktree from updated `main`.
- `BaseAgent._execute_tool()` intentionally swallows tool exceptions into error payloads. Fixing the ExaOutreach storage mismatch alone will restore deterministic logging, but it will not change the broader design choice that silent tool failures can still produce `completed` runs. Expanding scope to alter that policy would be a separate behavioral change.
- Changing `ProviderHTTPError` mutability affects every provider wrapper. The safest fix is the smallest one that restores normal exception behavior while preserving the existing fields and string representation.
- The local test suite is large. Running the full suite is ideal for final verification, but focused subsets will be needed during implementation to keep iteration fast.
- Existing tests may reflect older assumptions. If a test encodes stale behavior, the implementation must first determine whether the code or the test is wrong before changing either.

No blocking ambiguities remain for implementation planning. The scope can be decomposed without guessing.

Phase 1 complete
