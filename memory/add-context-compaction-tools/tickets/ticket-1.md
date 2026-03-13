Title: Add reusable agent-context compaction tools
Intent: Extend the current tool runtime with injectable context-window compaction behavior so future agents can deterministically remove tool noise, reset context down to parameters, and preserve conversation history through summarized logs.
Scope:
- Add a small shared context-window model for parameter entries, conversational messages, tool calls, tool results, and summaries.
- Add `remove_tool_results`, `remove_tools`, `heavy_compaction`, and `log_compaction` tool handlers and definitions.
- Export the new compaction tool surface through `src/tools/__init__.py`.
- Add unit tests covering compaction behavior and registry integration.
- Do not implement a full agent loop or provider response parser in this ticket.
Relevant Files:
- `src/shared/agents.py`: canonical agent-context typed dicts and helper aliases.
- `src/tools/context_compaction.py`: compaction helper functions and registered-tool factories.
- `src/tools/__init__.py`: public exports for the new compaction tools.
- `tests/test_context_compaction_tools.py`: coverage for the new compaction behavior.
Approach: Keep the context model explicit and minimal. Represent context entries with a required `kind` field so compaction behavior does not depend on heuristics about message text. Implement pure helper functions first, then wrap them in `RegisteredTool` factories so the behavior is usable through the existing registry. `log_compaction` will accept an injected summarizer callable and will preserve leading parameter entries before appending a synthesized summary entry.
Assumptions:
- The merged branch should gain reusable compaction primitives even though the fuller agent runtime remains unmerged.
- Parameter entries should be preserved only while they remain the leading contiguous prefix of the context window.
- A summary entry can be represented as a dedicated `summary` kind rather than overloading an assistant message.
Acceptance Criteria:
- [ ] The codebase contains a canonical context-window representation suitable for compaction tools.
- [ ] `remove_tool_results` removes only tool-result entries and preserves all other ordering.
- [ ] `remove_tools` removes tool-call and tool-result entries and preserves all other ordering.
- [ ] `heavy_compaction` preserves only the leading parameter prefix.
- [ ] `log_compaction` preserves the leading parameter prefix, appends a synthesized summary entry, and removes the remaining prior context entries.
- [ ] The compaction tools are exposed through the public tool package and covered by unit tests.
Verification Steps:
- Run `python -m unittest tests.test_context_compaction_tools -v`.
- Run `python -m unittest`.
- Smoke-check the registry by executing the new tool keys against sample context windows.
Dependencies: None.
Drift Guard: This ticket must not turn into a full agent runtime implementation, provider adapter, or transcript persistence system. The deliverable is the reusable compaction-tool surface only.
