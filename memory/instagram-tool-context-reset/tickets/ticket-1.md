Title: Trim Instagram search transcript state to recent keyword memory only

Intent: Reduce model token usage for the Instagram discovery harness by removing Instagram search tool chatter from the rolling transcript while preserving deterministic lead persistence and enough state to avoid repeating attempted keywords.

Scope:
- Update the Instagram agent to stop carrying Instagram search tool calls/results forward in the transcript.
- Ensure pure Instagram search turns do not leave behind blank assistant placeholders or redundant assistant search commands.
- Track attempted Instagram keywords outside the transcript for the active run so failed attempts still appear in `Recent Searches`.
- Update the Instagram master prompt to rely on recent keyword memory instead of tool-result feedback.
- Add targeted tests for successful-search compaction and failed-search attempt memory.
- Do not change the durable Instagram memory schema or the shared base-agent behavior for other harnesses.

Relevant Files:
- `harnessiq/agents/instagram/agent.py`: add Instagram-specific transcript compaction and attempted-keyword tracking.
- `harnessiq/agents/instagram/prompts/master_prompt.md`: remove tool-result dependency from prompt instructions.
- `tests/test_instagram_agent.py`: add regressions for transcript compaction and failed-attempt memory.

Approach: Keep the optimization local to the Instagram harness. Successful searches continue to persist through the deterministic tool layer. The agent overrides transcript-recording hooks so `instagram.search_keyword` activity is not carried into the next model request. A lightweight in-memory attempted-keyword list supplements durable search history so failed attempts remain visible in the `Recent Searches` parameter section for the current run. The prompt is then aligned to the new control flow.

Assumptions:
- The Instagram agent can operate correctly from ICPs plus recent attempted keywords without seeing prior search result payloads.
- Failed attempted keywords only need to survive for the active run, not as a durable schema change.

Acceptance Criteria:
- [ ] The next Instagram model turn does not receive prior `instagram.search_keyword` tool-call entries.
- [ ] The next Instagram model turn does not receive prior `instagram.search_keyword` tool-result entries.
- [ ] Pure Instagram search turns do not leave `(no assistant content)` placeholders in transcript.
- [ ] Failed attempted keywords still appear in `Recent Searches` during the run so the agent does not retry them immediately.
- [ ] Instagram prompt instructions no longer depend on tool-result feedback.
- [ ] Targeted Instagram agent tests pass.

Verification Steps:
- Static analysis: inspect the changed files for local convention alignment.
- Type checking: run `python -m compileall harnessiq/agents/instagram/agent.py tests/test_instagram_agent.py`.
- Unit tests: run `python -m pytest tests/test_instagram_agent.py`.
- Integration tests: none configured beyond the targeted agent tests for this scope.
- Smoke verification: reason through the provided conversation-state example and confirm the next turn would be driven by `Recent Searches` only.

Dependencies: None

Drift Guard: Do not widen this change into a base-agent transcript policy change, a CLI change, or a durable-memory schema migration. This ticket is specifically about reducing Instagram-agent context usage while preserving deterministic persistence outside the model loop.
