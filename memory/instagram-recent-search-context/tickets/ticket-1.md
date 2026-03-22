Title: Slim Instagram recent-search context and search tool transcript payload

Issue URL:
- https://github.com/cerredz/HarnessHub/issues/217

Intent:
Reduce Instagram agent context-window bloat so the model spends tokens on choosing the next keyword rather than rereading verbose search metadata and persisted result details.

Scope:
- Change the Instagram agent parameter sections so `Recent Searches` contains only the recently used keywords rendered as a comma-separated string.
- Remove the `Recent Search Results` parameter section from the Instagram agent context window.
- Update the Instagram master prompt so it depends on the reduced `Recent Searches` representation and no longer references the removed `Recent Search Results` section.
- Reduce the `instagram.search_keyword` tool result payload to the minimum useful summary for transcript consumption.
- Update Instagram agent tests to cover the new parameter-section shape and tool-result behavior.
- Do not change durable memory file formats, CLI summary output, lead persistence logic, or the search backend contract.

Relevant Files:
- `harnessiq/agents/instagram/agent.py`: change parameter-section rendering and slim the search tool result payload.
- `harnessiq/agents/instagram/prompts/master_prompt.md`: align prompt instructions with the reduced context structure.
- `tests/test_instagram_agent.py`: update and extend assertions for parameter ordering/content and compact tool results.
- `harnessiq/shared/instagram.py`: read-only reference for persisted record/schema behavior that must remain unchanged.

Approach:
Keep durable search history exactly as it is, but derive a lightweight presentation for the model at parameter-load time by extracting only `record.keyword` values from recent history and joining them with `, `. Remove the recent-results parameter section entirely so the agent no longer re-reads lead snippets and emails in the durable block. Slim `_handle_search_keyword()` so the transcript keeps only status, keyword, counts, and merge summary; this preserves search-outcome feedback while deleting bulky `query` and `visited_urls` fields. Update tests to assert the exact section ordering and formatting so a future refactor cannot silently reintroduce JSON-heavy context.

Assumptions:
- The user’s “same thing with the tool result” request means transcript slimming, not changing persisted durable memory.
- Keeping `merge_summary` in the searched-tool result provides enough operational signal after a search completes.
- Backward compatibility for existing `search_history.json` and CLI output matters more than cleaning up now-unused runtime parameters in this ticket.
- `Recent Searches` should render as plain text, not JSON.

Acceptance Criteria:
- [ ] `InstagramKeywordDiscoveryAgent.load_parameter_sections()` returns `ICP Profiles` and `Recent Searches` only.
- [ ] `Recent Searches` contains only the recent keywords, rendered as a comma-separated string in durable-history order.
- [ ] No persisted lead/result records are injected into the Instagram agent parameter sections.
- [ ] `instagram.search_keyword` tool results no longer include `query` or `visited_urls`.
- [ ] Search tool results still include enough compact outcome data to understand whether the search was new, skipped, and/or productive.
- [ ] Existing durable memory files and CLI summary behavior remain unchanged.
- [ ] Instagram agent tests pass with explicit coverage for the reduced parameter block and compact tool results.

Verification Steps:
1. Run targeted Instagram agent tests with `python -m pytest tests/test_instagram_agent.py`.
2. Inspect the relevant assertions to confirm parameter-section order/content now matches the reduced two-section layout.
3. Confirm the targeted test exercising tool execution observes the compact tool-result payload indirectly through the refreshed next-cycle parameter sections and directly through tool execution.

Dependencies:
- None.

Drift Guard:
This ticket must not redesign the Instagram memory schema, remove runtime parameters for CLI compatibility, or change the search backend’s canonical persisted search record. It is strictly a context-window and transcript-payload reduction task for the Instagram agent harness and its prompt/tests.
