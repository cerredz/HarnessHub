Title: Refactor the context tool family to resolve PR #239 review comments
Issue URL: https://github.com/cerredz/HarnessHub/issues/241

Intent:
Resolve the architectural and usability feedback left on PR #239 by moving context-tool binding out of `BaseAgent`, separating tool definitions from execution logic, preserving explicit opt-in activation, and improving the tool descriptions that agents see.

Scope:
- Refactor `harnessiq/tools/context/` into a thin composition layer plus dedicated `definitions/` and `executors/` subpackages.
- Move the context-tool executor wrapper currently embedded in `BaseAgent` into the `harnessiq/tools/context/` package.
- Preserve the public `create_context_tools()` factory and current tool-key/schema behavior.
- Add or update tests that prove the context tools remain opt-in and still behave correctly after the refactor.
- Do not redesign the context runtime data model or change unrelated tool families.

Relevant Files:
- `harnessiq/agents/base/agent.py`: remove the embedded context-tool binding helper and import the tool-layer binder.
- `harnessiq/tools/context/__init__.py`: keep the public composition/export layer stable while routing through the refactored modules.
- `harnessiq/tools/context/definitions/*`: hold `RegisteredTool` assembly and descriptive metadata for each context tool group.
- `harnessiq/tools/context/executors/*`: hold execution logic for each context tool group.
- `harnessiq/tools/context/*`: add any small shared runtime/binding helpers required by the split.
- `tests/test_agents_base.py`: verify context-tool binding stays opt-in and runtime behavior still works.
- `tests/test_context_window_tools.py`: verify the refactored context tool family still executes correctly.
- `docs/context-window-tools.md`: update only if the architectural description becomes stale after the refactor.

Approach:
Keep `harnessiq/tools/context/__init__.py` as the stable public package boundary, but pull mixed concerns apart underneath it. Shared runtime callbacks and normalization helpers stay in focused root modules, definition modules create `RegisteredTool` objects with richer descriptions, and executor modules own the logic that mutates context windows or runtime state. `BaseAgent` should delegate binding to a tool-layer helper so the agent runtime remains an orchestrator rather than a home for tool-family-specific registry glue.

Assumptions:
- The public API consumers care about `create_context_tools()` and shared constants, not the current internal file layout.
- The context binding helper can depend on `ToolRegistry` and `AgentToolExecutor`-compatible behavior without introducing a new abstraction.
- The existing explicit `enable_context_tools()` method is the right activation model and should remain unchanged externally.

Acceptance Criteria:
- [ ] No context-tool-specific executor wrapper remains defined inside `harnessiq/agents/base/agent.py`.
- [ ] `harnessiq/tools/context/` contains separate definition and execution subpackages for the context tool family internals.
- [ ] Context injection tool descriptions are expanded into clearer multi-sentence descriptions.
- [ ] Agents still do not receive context tools unless `enable_context_tools()` is explicitly called.
- [ ] Existing context-tool tests and `BaseAgent` integration tests pass after the refactor.

Verification Steps:
- Run `python -m unittest tests.test_context_window_tools tests.test_agents_base -v`.
- Run `python -m compileall harnessiq\\tools\\context harnessiq\\agents\\base\\agent.py tests\\test_context_window_tools.py tests\\test_agents_base.py`.
- Manually inspect the exported tool definitions for the injection group to confirm the descriptions are expanded and the keys remain stable.

Dependencies:
- None.

Drift Guard:
This ticket must not change the public tool keys, introduce automatic context-tool injection into unrelated agents, or redesign the broader agent runtime. The work is limited to addressing the concrete PR #239 review feedback while preserving the existing behavior of the shipped feature.
