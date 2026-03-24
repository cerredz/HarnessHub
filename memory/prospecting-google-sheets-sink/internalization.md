### 1a: Structural Survey

Top-level architecture:
- `harnessiq/` is the live runtime source tree; `artifacts/file_index.md` explicitly marks `build/` and `src/` as non-authoritative generated residue.
- Agents live under `harnessiq/agents/`. They orchestrate long-running loops through `BaseAgent`, durable memory stores, tool registries, and provider-backed models.
- CLI entrypoints live under `harnessiq/cli/`. Agent-specific commands usually expose `prepare`, `configure`, `show`, and `run`, while ledger/output-sink commands live in `harnessiq/cli/ledger/commands.py`.
- Shared durable state and manifest metadata live under `harnessiq/shared/`. The prospecting harness definition, defaults, and file-backed memory store are in `harnessiq/shared/prospecting.py`.
- Providers live under `harnessiq/providers/`. Existing sink-adjacent clients are grouped in `harnessiq/providers/output_sink_clients.py`. Google integration currently exists only for Drive in `harnessiq/providers/google_drive/`.
- Tool definitions live under `harnessiq/tools/`. Prospecting exposes one deterministic evaluator tool, one planner/summarizer tool, and internal persistence tools.
- Ledger/output sink infrastructure lives under `harnessiq/utils/ledger_*.py`. Built-in sink registration is centralized in `harnessiq/utils/ledger_sinks.py`. Public exports are re-exposed via `harnessiq/utils/ledger.py` and `harnessiq/utils/__init__.py`.

Technology and runtime stack:
- Python 3.11+, setuptools packaging, unittest-style test suite, LangSmith tracing, provider-agnostic model contract.
- No external Sheets dependency is currently declared in `pyproject.toml`; existing HTTP integrations use the stdlib/request helpers and small provider clients.
- Existing sink implementations are synchronous and best-effort. Sink failures are swallowed by `BaseAgent._emit_ledger_entry`.

Data flow relevant to this task:
- CLI `prospecting run` resolves a memory store, seeds env, loads model and browser tool factories, constructs the prospecting agent from persisted memory plus ephemeral overrides, then calls `agent.run()`.
- `GoogleMapsProspectingAgent.from_memory()` reads persisted company description, runtime params, and custom params from `ProspectingMemoryStore`.
- `BaseAgent._run_loop()` refreshes parameters, makes a model call, records assistant output/tool calls, executes tools, and terminates when `response.should_continue` is false.
- Output sinks run only after completion/error through the ledger hook; they are not part of the model/tool loop.

Conventions and patterns:
- Built-in sinks are dataclasses with `on_run_complete(self, entry)` methods.
- Built-in sink registration happens in one map in `_register_builtin_sinks()`.
- Provider clients are small dataclasses using `request_json` or provider-specific raw request executors.
- Tests are direct, focused, and mostly live under `tests/test_output_sinks.py`, `tests/test_prospecting_agent.py`, and provider-specific modules.
- Durable memory defaults are created automatically by `ProspectingMemoryStore.prepare()`, including a placeholder `company_description.md`.

Observed inconsistencies:
- The prospecting CLI `run` command accepts runtime/custom overrides but not a company-description override, while the harness silently allows the placeholder company description to flow into the first model call.
- The current run path reports `"status": "completed"` even when the model returned a clarification request instead of doing any prospecting work.
- The repo has Google Drive support but no Google Sheets sink, even though the ledger sink framework is designed for provider-backed post-run exports.

### 1b: Task Cross-Reference

User request mapping:
- Diagnose why the Google Maps prospecting agent stops after one model call:
  - `harnessiq/cli/prospecting/commands.py`: determines what the CLI persisted vs. what it only overrode for one run.
  - `harnessiq/shared/prospecting.py`: defines the placeholder company description and the memory store behavior.
  - `harnessiq/agents/prospecting/agent.py`: constructs the system prompt and parameter sections from persisted memory, not from a required run-time target string.
  - `harnessiq/agents/base/agent.py`: marks the run complete when the model returns no tool calls and `should_continue` is false.
  - LangSmith trace `https://smith.langchain.com/public/5b8a9c30-08c5-473a-b943-d73b0661390b/r`: confirms the first and only model call saw the placeholder description and returned a clarification message with `finish_reason=stop`.
- Add a “google excel sink” to the repo sinks:
  - `harnessiq/utils/ledger_sinks.py`: add built-in sink implementation and registration.
  - `harnessiq/providers/output_sink_clients.py` and `harnessiq/providers/output_sinks.py`: add provider client/facade if the sink uses a dedicated API client.
  - `harnessiq/utils/ledger.py` and `harnessiq/utils/__init__.py`: re-export the new sink.
  - `harnessiq/cli/ledger/commands.py`: add `harnessiq connect ...` support for the new sink.
  - `docs/output-sinks.md`, `artifacts/file_index.md`, and possibly `README.md`: reflect the new built-in sink and CLI surface.
  - `tests/test_output_sinks.py`: validate construction and delivery behavior.

Relevant existing behavior to preserve:
- Output sinks remain post-run only and do not participate in the prospecting loop.
- Prospecting durable memory semantics must remain intact; searches, qualified leads, and run state still live under `memory/prospecting/<agent>/`.
- Sink failures must remain non-fatal to completed runs.

Net-new behavior needed:
- A built-in Google Sheets sink, implemented in the same style as the other sink clients.
- An explicit prospecting validation path that refuses to run with the placeholder target description instead of silently “completing”.

Blast radius:
- Ledger sink registry/public exports/CLI help/docs/tests.
- Prospecting CLI or agent validation path.
- No intended changes to browser tool execution or qualification logic.

### 1c: Assumption & Risk Inventory

Assumptions:
- “google excel sink” means a Google Sheets sink, not Microsoft Excel or CSV-to-Drive export.
- A synchronous Sheets append/update implementation is acceptable as a post-run sink.
- Storing Google OAuth client id/client secret/refresh token directly in the sink connection config is acceptable because existing sinks already persist raw API secrets in `connections.json`.
- The correct immediate fix for the one-cycle stop is validation, not forcing a model retry, because the trace shows the model asked for missing required input.

Risks:
- Google Sheets API access may require a different OAuth scope than the existing Drive provider default (`drive.file`). Reusing the same credential shape without widening scope handling could fail at runtime if the refresh token was minted without Sheets access.
- If the sink schema is too generic, prospecting output may land as a single blob rather than one row per qualified lead, which would be less useful than the user expects.
- If validation is added too deep in the agent loop instead of at the CLI boundary, the user may still incur a billable model call before seeing the error.
- Updating generated docs without rerunning the repo doc generator could create drift against the source tree conventions documented in `artifacts/file_index.md`.

Conclusion:
- No blocking ambiguity prevents implementation. The only non-blocking assumption is that the requested “google excel sink” should be implemented as a Google Sheets sink.

Phase 1 complete.
