### 1a: Structural Survey

Top-level architecture relevant to this task:
- `harnessiq/agents/`: concrete harnesses built on `BaseAgent`. The Instagram agent is a thin orchestrator that delegates model calls to an `AgentModel` and tool execution to the tool layer.
- `harnessiq/cli/`: CLI entrypoints that hydrate agent config and invoke harnesses. `cli/instagram/commands.py` wires `InstagramKeywordDiscoveryAgent` to the Grok model factory and the Playwright backend.
- `harnessiq/integrations/`: adapters that implement the `AgentModel` protocol or browser-backed integrations. `integrations/grok_model.py` wraps the Grok provider client and traces each model call through LangSmith. `integrations/instagram_playwright.py` is unrelated to the traceback bug except that it is the harness the user is running.
- `harnessiq/providers/`: provider transport and tracing infrastructure. `providers/http.py` converts `urllib` failures into `ProviderHTTPError`. `providers/langsmith.py` wraps sync and async operations in LangSmith context managers and is responsible for fail-open tracing behavior.
- `harnessiq/shared/`: reusable types and error classes. `shared/http.py` defines `ProviderHTTPError`. `shared/providers.py` holds provider-wide aliases and the simpler `ProviderFormatError` exception.
- `tests/`: unittest-based coverage. `tests/test_provider_base.py` covers `request_json` and `ProviderHTTPError` fields/string rendering. `tests/test_providers.py` covers tracing wrappers. There is currently no regression test for exception propagation when a traced operation raises `ProviderHTTPError`.

Technology stack and conventions:
- Python 3.11, stdlib `urllib` for HTTP, unittest for tests.
- Agents use protocol-typed abstractions (`AgentModel`, `AgentToolExecutor`, provider request executors) and favor dataclasses in shared config/types modules.
- Error handling pattern: provider clients raise shared typed exceptions; tracing wrappers attempt to fail open when LangSmith is unavailable or misbehaves.
- Repository boundary guidance from `artifacts/file_index.md`: shared reusable types belong in `harnessiq/shared/`, tracing/runtime behavior belongs in `harnessiq/providers/`, harnesses should stay thin.

Relevant data flow:
1. `instagram run` CLI creates a `GrokAgentModel`.
2. `BaseAgent.run()` wraps the run loop in `trace_agent_run`.
3. `GrokAgentModel.generate_turn()` wraps the HTTP call in `trace_model_call`.
4. `GrokClient` calls `request_json`.
5. `request_json` raises `ProviderHTTPError` on non-2xx responses.
6. LangSmith teardown tries to propagate the exception and Python writes `__traceback__` onto the exception object.
7. `ProviderHTTPError` currently rejects that mutation and masks the original `403` with `TypeError("super(type, obj): obj must be an instance or subtype of type")`.

Inconsistencies observed:
- `ProviderHTTPError` is implemented as a frozen, slotted dataclass subclassing `RuntimeError`, while `ProviderFormatError` is a normal exception class. The former is structurally unusual for a mutable runtime exception object.
- `providers/langsmith.py` is intended to fail open, but there is no regression coverage for exception objects that are incompatible with traceback mutation.

### 1b: Task Cross-Reference

User task: fix the Instagram agent error `TypeError('super(type, obj): obj must be an instance or subtype of type')` shown during Grok `403 Forbidden` handling.

Concrete mapping:
- `harnessiq/shared/http.py`
  Defines `ProviderHTTPError`, the concrete exception instance shown in the traceback. This is the most likely root cause because assigning `exc.__traceback__` on this exception reproduces the exact `TypeError`.
- `harnessiq/providers/http.py`
  Creates `ProviderHTTPError` instances from HTTP/URL failures. Any fix must preserve its existing fields (`provider`, `message`, `status_code`, `url`, `body`) and string rendering because provider tests and callers depend on them.
- `harnessiq/providers/langsmith.py`
  Executes operations inside `ls.tracing_context(...)` and re-raises operation exceptions. This module is the propagation boundary where the broken exception object gets exercised.
- `tests/test_provider_base.py`
  Existing contract tests for provider HTTP failures need to keep passing after the exception type is changed internally.
- `tests/test_providers.py`
  Needs new regression coverage ensuring traced model/tool/agent wrappers preserve the original `ProviderHTTPError` rather than masking it with a secondary `TypeError`.
- `harnessiq/integrations/grok_model.py`, `harnessiq/providers/grok/client.py`, `harnessiq/cli/instagram/commands.py`
  Relevant for reproducing the bug path, but they are not the structural source of the failure and should not need behavioral changes unless verification exposes something else.

What exists already:
- A shared typed provider HTTP error.
- LangSmith tracing wrappers for sync and async operations.
- Unit coverage for successful tracing and for ordinary runtime errors inside tracing.

What is missing:
- An exception implementation that is safe for normal Python traceback propagation.
- Regression tests covering `ProviderHTTPError` flowing through `trace_model_call`/`trace_agent_run`.

Behavior that must be preserved:
- Grok `403` should still surface as `ProviderHTTPError` with provider/status/body metadata intact.
- LangSmith tracing should continue to record error strings before reraising.
- Tracing helpers should continue to fail open when tracing infra is unavailable or broken.

Blast radius:
- All provider clients using `request_json`, not just Grok.
- All tracing wrappers that propagate provider exceptions.
- Tests that assert on `ProviderHTTPError` fields or `str(exc)`.

### 1c: Assumption & Risk Inventory

Assumptions:
- The reported `TypeError` is not an Instagram-specific logic bug; it is caused by the exception object used by the provider stack. This is strongly supported by isolated reproduction.
- Replacing the dataclass-based exception with a normal exception class is acceptable as long as public attributes and `__str__` behavior remain stable.
- No downstream code relies on dataclass-specific features such as `dataclasses.asdict()` for `ProviderHTTPError`.

Risks:
- Changing exception construction semantics could break tests or call sites that rely on dataclass-generated repr/equality behavior.
- Fixing only `ProviderHTTPError` but not adding regression tests would leave the tracing boundary vulnerable to future exception-type regressions.
- The real Grok `403` may still occur after this fix. That is acceptable for this ticket; the goal is to preserve the correct error instead of masking it.
- There may be a similar issue in async tracing paths; the fix and tests should cover the shared sync tracing path explicitly and evaluate whether async needs equivalent coverage.

Phase 1 complete.
