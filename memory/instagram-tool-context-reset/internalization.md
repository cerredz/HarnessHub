### 1a: Structural Survey

- `harnessiq/` is the authoritative runtime tree; `tests/` contains the Python regression suite, and `artifacts/file_index.md` documents repo-level conventions.
- `harnessiq/agents/base/agent.py` owns the shared agent loop. It records assistant content, tool calls, and tool results into a rolling transcript, then sends that transcript back on the next model turn.
- `harnessiq/agents/instagram/agent.py` is the Instagram-specific harness. It already keeps the parameter block intentionally small: `ICP Profiles`, `Recent Searches`, and optional `Custom Parameters`.
- `harnessiq/tools/instagram/operations.py` is deterministic tool logic. It validates the keyword, calls the search backend, persists search history plus leads to durable memory, and returns a compact result payload.
- `harnessiq/shared/instagram.py` defines the durable Instagram memory schema and search-history records. Successful searches are persisted; failed attempts are not.
- `harnessiq/agents/instagram/prompts/master_prompt.md` currently still tells the model to use the compact tool result between searches.
- `tests/test_instagram_agent.py` covers prompt-section rendering, durable search persistence, and run-loop behavior for the Instagram agent.

### 1b: Task Cross-Reference

- The user wants the Instagram agent to stop spending tokens on old tool calls and tool results. That maps to transcript recording in `harnessiq/agents/base/agent.py`, but the safest implementation point is an Instagram-specific override in `harnessiq/agents/instagram/agent.py`.
- The agent should keep only recent search keywords in context. That maps to `InstagramKeywordDiscoveryAgent.load_parameter_sections()`, which already renders `Recent Searches` as a comma-separated keyword list from durable search history.
- The user explicitly does not want tool results appended back into context. That maps to overriding `_record_tool_result()` for `instagram.search_keyword`.
- The user also does not want old Instagram tool calls in context. That maps to overriding `_record_assistant_response()` so Instagram search turns do not persist search tool calls or blank placeholder assistant entries.
- Because failed search attempts are currently remembered only through transcript tool results, removing transcript search state requires an Instagram-specific in-memory attempt list so the next turn still knows which keywords were already tried during this run.
- The prompt must stop depending on tool-result feedback and instead steer only from ICPs plus recent keyword history.

### 1c: Assumption & Risk Inventory

- Assumption: for the Instagram agent, the transcript does not need to retain search-tool orchestration once the keyword has been attempted and durable memory has been refreshed.
- Assumption: it is acceptable for the model to choose the next keyword based on ICPs plus recent attempted keywords, without seeing per-search `lead_count` or `merge_summary` in the context window.
- Assumption: failed search attempts should still count as “recent searches” for the duration of the run so the agent does not immediately retry them after transcript compaction.
- Risk: if failed attempts are not tracked outside the transcript, the agent can loop on the same blocked keyword because search history persists only successful executions.
- Risk: if assistant placeholder messages like `(no assistant content)` continue to be recorded, token savings will be smaller than intended even after removing search tool calls/results.
- Risk: if the master prompt keeps referencing tool-result feedback, model behavior will drift from the new low-context control flow.

Phase 1 complete
