Title: Implement the multi-ICP leads agent harness

Issue URL: https://github.com/cerredz/HarnessHub/issues/152

Intent:
Build the actual leads agent that runs one agent loop across multiple ICPs, rotates ICP context per iteration, calls injected provider tools sequentially, persists searches and leads deterministically, and uses the new runtime pruning controls to keep context bounded.

Scope:
This ticket adds the concrete leads harness, its prompt construction, internal tools, provider composition logic, and agent-level tests.
This ticket does not add CLI commands or the final docs pass beyond code-level exports required to instantiate the agent from the SDK.

Relevant Files:
- `harnessiq/agents/leads/__init__.py`: export the leads agent harness.
- `harnessiq/agents/leads/agent.py`: implement the leads agent loop and tool composition.
- `harnessiq/agents/__init__.py`: export the new public agent type.
- `tests/test_leads_agent.py`: add harness-level tests for prompt sections, ICP rotation, deterministic search persistence, dedupe, and save behavior.
- `harnessiq/shared/leads.py`: integrate any final harness-facing helpers needed by the agent.

Approach:
Model the leads harness after `ExaOutreachAgent` and `LinkedInJobApplierAgent`, not as a one-off runtime. The agent should:

- load company background plus the current ICP into parameter sections
- expose internal tools for persisting search attempts, summaries, dedupe checks, and lead saves
- compose provider tools based on configured platforms
- run a single agent instance that advances through ICPs in deterministic order
- reload parameter sections so only the active ICP’s context sits in the durable prompt block at any given iteration

The agent should not rely on transcript memory for search history. Instead, it should write per-ICP search entries through deterministic internal tools and inject the relevant summary/tail back into the context window when parameters refresh.

Assumptions:
- The runtime pruning controls from Ticket 2 are available for the agent to use.
- The Apollo provider from Ticket 1 is available as one of the injectable platforms.
- The shared leads models/storage from Ticket 3 are the source of truth for durable state.

Acceptance Criteria:
- [ ] The leads agent can be instantiated from the SDK with company background, multiple ICPs, selected platforms, and a storage backend.
- [ ] The harness exposes the current ICP in parameter sections and rotates to the next ICP through deterministic state updates.
- [ ] Searches are persisted per ICP through internal tools, and summarized/replaced according to the configured pruning policy.
- [ ] Duplicate leads are detected through deterministic state rather than transcript memory alone.
- [ ] Agent tests cover construction, prompt/parameter ordering, ICP rotation, search persistence, pruning interactions, and save behavior.

Verification Steps:
- Static analysis: run the linter against the new leads agent modules.
- Type checking: run the type checker or validate annotations/import safety for the new harness.
- Unit tests: run `pytest tests/test_leads_agent.py`.
- Integration and contract tests: run agent/runtime/provider tests that touch the new harness and shared runtime behavior.
- Smoke verification: execute a fake-model leads run over multiple ICPs with fake provider tools and inspect the persisted memory artifacts.

Dependencies:
- Ticket 1.
- Ticket 2.
- Ticket 3.

Drift Guard:
This ticket must not expand into CLI UX design, markdown docs polishing, or unrelated provider additions. Its responsibility is the SDK harness and its deterministic runtime behavior.
