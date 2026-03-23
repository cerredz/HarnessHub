## PR 239 Review Follow-Up Internalization

### 1a: Structural Survey

#### Repository shape

- `harnessiq/` is the authoritative runtime package. The generated `artifacts/file_index.md` explicitly says runtime work should land there rather than in `build/` or `src/`.
- `harnessiq/agents/base/agent.py` is the shared runtime loop. It owns request construction, tool execution, transcript handling, context reset/pruning, ledger emission, and optional runtime extensions.
- `harnessiq/tools/` is the canonical home for executable tool surfaces and registry plumbing. Most tool families expose a small package entrypoint plus narrower implementation modules beneath it.
- `harnessiq/shared/` holds cross-cutting dataclasses and constant tool keys. The context-window tool family uses `harnessiq/shared/agents.py` for runtime-state models and `harnessiq/shared/tools.py` for the tool-key catalog.
- `tests/` is the primary verification surface. `tests/test_agents_base.py` covers runtime behavior and context-tool binding, while `tests/test_context_window_tools.py` covers the context tool family itself.
- `docs/` and generated artifacts explain public package shape. `docs/context-window-tools.md` is the current reference doc for this feature area.

#### Relevant architecture

- `BaseAgent` currently binds the context tool family through a private `_BoundContextToolExecutor` wrapper and an `enable_context_tools()` opt-in method.
- `harnessiq/tools/context/__init__.py` currently mixes several concerns:
  - runtime callback dataclasses and normalization helpers
  - tool-family assembly through `create_context_tools()`
  - public re-exports of all shared context-tool constants
- Each current `harnessiq/tools/context/*.py` module defines both the registered tool metadata and the execution logic for that group.
- Existing tool-family conventions in `harnessiq/tools/` favor a thin package entrypoint that imports focused modules instead of concentrating orchestration and execution in a single file.

#### Conventions and constraints

- Tool definitions are modeled through `RegisteredTool`, `ToolDefinition`, and `ToolRegistry`.
- Public package exports are curated through `__all__` in package entrypoints.
- Review comments on PR #239 are architectural, not feature-expansion requests, so the blast radius should stay within the context-tool family, `BaseAgent`, tests, and any small doc updates needed to keep the repo coherent.

### 1b: Task Cross-Reference

User task: resolve every inline and final review comment on GitHub PR #239, sequentially, then create a new PR into `main`.

Concrete mapping of the four actionable comments:

1. Move the context-binding helper out of `BaseAgent` and into the tool layer.
   - Current location: `harnessiq/agents/base/agent.py`
   - Likely destination: a focused module under `harnessiq/tools/context/`
   - Adjacent verification: `tests/test_agents_base.py`

2. Ensure context-window tools are not auto-injected for all agents.
   - Current behavior location: `harnessiq/agents/base/agent.py`
   - Verification surface: search results show only explicit calls to `enable_context_tools()` in tests; no agent enables them by default.
   - Needed change: preserve opt-in semantics and add/adjust verification so that this contract stays explicit after the refactor.

3. Improve the descriptions for the registered transcript-injection tools.
   - Current location: `harnessiq/tools/context/injection.py`
   - Expected post-refactor location: definition modules under `harnessiq/tools/context/definitions/`

4. Split `harnessiq/tools/context/` into separate registration/definition and execution layers.
   - Current mixed files: `harnessiq/tools/context/injection.py`, `parameter.py`, `selective.py`, `structural.py`, `summarization.py`
   - Likely new shape: `definitions/` for `RegisteredTool` assembly and `executors/` for implementation logic, with a thin package/root assembly layer remaining in `harnessiq/tools/context/`

Behavior that must be preserved:

- `BaseAgent.enable_context_tools()` remains opt-in.
- `create_context_tools()` remains the public package factory.
- Existing tool keys, schemas, and outputs keep working for current tests and users.
- The context runtime state and transcript normalization helpers remain available to the tool executors after the refactor.

### 1c: Assumption & Risk Inventory

#### Assumptions

- The final review body and the three inline comments together are the complete requested scope for PR #239 follow-up work.
- The requested `definitions` / `executors` split is organizational and should not change the external API of `create_context_tools()`.
- No additional agent classes should gain automatic context-tool injection; the existing explicit `enable_context_tools()` call pattern is the intended contract.
- Expanding descriptions to 3-4 sentences is expected for the transcript-injection tool family specifically, because that is the file called out in review.

#### Risks

- Moving the bound-executor helper out of `BaseAgent` can create circular imports if the new tool-layer module reaches back into agent runtime internals too aggressively.
- Splitting the context package too mechanically can over-fragment helpers that are still shared across groups; the root package should stay as a stable composition layer.
- Import-path churn can silently break `__all__` exports or tests if the package entrypoint stops re-exporting the current public surface.
- The review request is architectural, so missing a regression test around opt-in behavior would leave the “not auto-injected” concern unguarded.

#### Clarification status

- No blocking ambiguities remain. The review comments are concrete enough to implement directly.

Phase 1 complete.
