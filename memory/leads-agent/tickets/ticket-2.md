Title: Add deterministic agent runtime pruning controls
Intent: Extend the shared agent runtime so long-running agents can prune transcript state on a deterministic interval based on durable progress or an explicit token ceiling, which is required for the leads-agent search-loop design.
Scope:
- Add shared runtime configuration fields and defaults for deterministic pruning.
- Add base-agent support for interval-driven pruning and explicit prune token limits.
- Keep the existing reset-on-budget behavior intact as a separate fallback.
- Add runtime tests covering config validation and both pruning triggers.
- Do not implement leads-specific storage, ICP orchestration, or provider logic in this ticket.
Relevant Files:
- `harnessiq/shared/agents.py`: shared runtime config surface and validation.
- `harnessiq/agents/base/agent.py`: pruning hooks, loop orchestration, and reset behavior.
- `tests/test_agents_base.py`: targeted coverage for deterministic pruning behavior.
Approach: Add optional `prune_progress_interval` and `prune_token_limit` fields to `AgentRuntimeConfig`, with positive-value validation. Update `BaseAgent` to track a pruning-progress baseline and expose an overridable `pruning_progress_value()` hook so domain agents can map pruning to durable work such as saved searches instead of raw transcript length. Evaluate deterministic pruning only when another model turn is needed, then fall back to the existing reset-threshold logic.
Assumptions:
- Deterministic pruning should be opt-in so current agents retain existing behavior by default.
- Progress-based pruning needs an overridable hook because different agents count “progress” differently.
- A terminal turn should not trigger transcript pruning because no future context window needs to be preserved.
Acceptance Criteria:
- [ ] `AgentRuntimeConfig` exposes optional deterministic pruning controls and rejects invalid values.
- [ ] `BaseAgent` can prune on a configurable progress interval without breaking the existing reset-threshold path.
- [ ] `BaseAgent` can prune on an explicit prune token limit distinct from the global max-token reset limit.
- [ ] Deterministic pruning does not fire after a terminal response.
- [ ] Existing agent tests that rely on the shared runtime continue to pass.
Verification Steps:
- Run `python -m py_compile harnessiq/shared/agents.py harnessiq/agents/base/agent.py tests/test_agents_base.py`.
- Run `python -m pytest tests/test_agents_base.py`.
- Run `python -m pytest tests/test_linkedin_agent.py`.
- Run `python -m pytest tests/test_knowt_agent.py`.
Dependencies: None.
Drift Guard: This ticket must not add leads-agent orchestration, search summarization, storage backends, or CLI plumbing. It only establishes the reusable runtime pruning controls those later tickets will consume.
