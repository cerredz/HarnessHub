### 1a: Structural Survey

- The repository is a Python package under `harnessiq/` with agent-specific harnesses in `harnessiq/agents/`, shared domain models and file-backed memory stores in `harnessiq/shared/`, tool definitions and handlers in `harnessiq/tools/`, CLI adapters/builders in `harnessiq/cli/`, and regression coverage in `tests/`.
- `harnessiq/agents/base/agent.py` owns the generic request loop. It builds each model request from durable parameter sections plus the rolling transcript, processes tool calls, records transcript entries, and supports compaction-class context updates.
- `harnessiq/agents/base/agent_helpers.py` defines how context windows are materialized. `entry_type="context"` transcript entries are first-class citizens and render into the transcript zone as `[CONTEXT: ...]` blocks.
- `harnessiq/agents/instagram/agent.py` specializes the base loop for the Instagram keyword harness. It persists ICP-scoped search history through `InstagramMemoryStore`, refreshes the `Recent Searches` parameter section after each `instagram.search_keyword` call, and intentionally suppresses raw Instagram search tool calls/results from the transcript.
- `harnessiq/shared/instagram.py` contains the persistent Instagram memory model. ICP states keep their own `searches` lists, and `read_recent_searches()` already returns the expected per-ICP tail used by the agent’s parameter sections.
- `harnessiq/tools/instagram/operations.py` defines `instagram.search_keyword`. The handler validates input, checks duplicate searches for the active ICP, persists a search record on success, and returns a compact status payload.
- `tests/test_instagram_agent.py` already covers parameter refresh after one search, failed-search fallback behavior, ICP scoping, and transcript suppression of raw Instagram tool calls/results. It does not currently assert that the context window shows incremental search progress across multiple search cycles.

### 1b: Task Cross-Reference

- The user-reported bug maps to the boundary between durable parameter refresh and transcript/context-window visibility inside `harnessiq/agents/instagram/agent.py`.
- The `Recent Searches` parameter section is built from `_recent_search_keywords_for_context()` and is refreshed inside `_execute_tool()` after every Instagram search. A direct reproduction confirms that request 2 sees the first keyword and request 3 sees both first and second keywords.
- The visible gap is that `_record_assistant_response()` and `_record_tool_result()` both suppress `instagram.search_keyword` events, leaving the transcript empty during search-only cycles. As a result, the context window does not append any search-progress artifact even though the parameter section is refreshed.
- The least invasive fix surface is `harnessiq/agents/instagram/agent.py`: keep suppressing noisy raw tool payloads, but append a compact transcript-level context snapshot after each Instagram search tool execution so the next request and any trace graph show evolving search history.
- `tests/test_instagram_agent.py` needs new regression coverage for sequential search cycles and updated expectations for post-search transcript state.

### 1c: Assumption & Risk Inventory

- Assumption: the user wants the context window itself to show incremental Instagram search progress, not merely the durable parameter block to be refreshed invisibly.
- Assumption: preserving suppression of raw `instagram.search_keyword` tool calls/results is still desirable because full tool payloads are noisy; a compact context snapshot is the intended compromise.
- Risk: appending a transcript snapshot after every search increases token usage. The snapshot must stay small and deterministic.
- Risk: changing transcript behavior will invalidate existing tests that assert the transcript remains empty after a search. Those expectations need to be updated deliberately rather than silently loosened.
- Risk: if the snapshot is appended before parameter refresh or before attempted-keyword bookkeeping, failed searches would still look stale. The new entry must be created only after the agent refreshes its recent-search state.

Phase 1 complete
