Title: Append Instagram recent-search progress to the context window

Intent: Make the Instagram discovery loop expose search progress in the live context window after each `instagram.search_keyword` call so successive search turns visibly build on prior search attempts.

Scope:
- Update the Instagram agent to append a compact transcript/context entry after each Instagram search tool execution.
- Preserve the existing durable `Recent Searches` parameter refresh and the suppression of raw Instagram search tool call/result transcript noise.
- Add regression tests for sequential search cycles and refreshed transcript state.
- Do not change the Instagram memory schema, CLI contract, or raw search tool payload shape.

Relevant Files:
- `harnessiq/agents/instagram/agent.py`: append a compact search-progress context entry after each Instagram search tool execution.
- `tests/test_instagram_agent.py`: cover multi-search context growth and updated transcript expectations.

Approach: Keep the durable parameter block as the source of truth and add a lightweight `entry_type="context"` transcript note after each Instagram search finishes. The note should include the active ICP, the tool-call outcome status, the just-attempted keyword, and the current merged recent-search window. This gives the model and any runtime graph an append-only, low-noise record of progress without reintroducing full raw tool payloads.

Assumptions:
- The user-visible problem is lack of transcript/context-window progression, not incorrect persistence in `InstagramMemoryStore`.
- A compact context snapshot is preferable to re-enabling full Instagram tool call/result transcript entries.

Acceptance Criteria:
- [ ] After one Instagram search, the next model request includes a transcript context entry describing the recent-search window.
- [ ] After multiple sequential Instagram searches in the same ICP, later model requests include cumulative recent-search state in transcript context entries.
- [ ] Raw `instagram.search_keyword` tool call/result entries remain suppressed from the transcript.
- [ ] Existing single-search and failed-search flows still refresh `Recent Searches` correctly.

Verification Steps:
- Static analysis: inspect changed files for consistency with existing agent conventions.
- Type checking: run `python -m compileall harnessiq/agents/instagram/agent.py tests/test_instagram_agent.py`.
- Unit tests: run `python -m pytest tests/test_instagram_agent.py`.
- Integration tests: none beyond the targeted harness regression coverage for this change.
- Smoke verification: run a small in-process fake-model reproduction and inspect the emitted request transcript.

Dependencies: None

Drift Guard: This ticket must not redesign Instagram search persistence, touch unrelated agents, or expose bulky Instagram tool payloads back into the transcript. The change is limited to making recent-search progress visible in the context window between search turns.
