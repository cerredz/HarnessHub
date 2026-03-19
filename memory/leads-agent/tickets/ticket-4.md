Title: Implement the multi-ICP leads agent harness
Intent: Build the concrete leads agent that rotates one agent instance across multiple ICPs, injects provider tools by platform family, persists searches and leads deterministically, and uses durable search progress as the runtime pruning counter.
Scope:
- Add the concrete leads agent harness and prompt file.
- Compose provider tools from the configured platform list or accept injected tools for controlled tests.
- Persist search attempts, compaction summaries, dedupe checks, and saved leads through internal tools plus the shared leads storage layer.
- Export the new agent from the SDK surface and add agent-level tests.
- Register the new agent structure in the repository file index.
- Do not add CLI commands or broader docs in this ticket.
Relevant Files:
- `harnessiq/agents/leads/agent.py`: multi-ICP harness implementation and internal tool handlers.
- `harnessiq/agents/leads/prompts/master_prompt.md`: system prompt template for the leads harness.
- `harnessiq/agents/leads/__init__.py`: leads-agent package exports.
- `harnessiq/agents/__init__.py`: public SDK export for `LeadsAgent`.
- `tests/test_leads_agent.py`: harness-level coverage for construction, rotation, deterministic persistence, and pruning behavior.
- `artifacts/file_index.md`: repository structure index updated for the new agent package and tests.
Approach: Keep the orchestration boundary deterministic in Python rather than asking the model to switch ICPs itself. `LeadsAgent.run()` owns the outer ICP loop; when the model ends a turn with `should_continue=false`, the harness marks the current ICP complete, resets transcript state, refreshes the parameter sections, and advances to the next ICP automatically. Internal tools handle search logging, manual compaction, dedupe checks, and lead saving against the shared `LeadsMemoryStore` and `LeadsStorageBackend`.
Assumptions:
- The shared leads storage contract from Ticket 3 is the source of truth for durable lead and search state.
- The deterministic pruning controls from Ticket 2 are available and should be driven by durable search counts rather than transcript length.
- Provider-family factories are consistent enough to compose generically through the static toolset catalog.
Acceptance Criteria:
- [ ] The leads agent can be instantiated from the SDK with company background, multiple ICPs, selected platforms, and a storage backend.
- [ ] The harness exposes the active ICP in parameter sections and automatically rotates to the next ICP when the current ICP run segment completes.
- [ ] Search logging and lead saving happen through deterministic internal tools backed by the shared leads memory/storage layer.
- [ ] Transcript pruning is tied to durable search progress rather than transient transcript growth.
- [ ] Agent tests cover construction, prompt/parameter ordering, ICP rotation, search persistence, dedupe, and pruning behavior.
Verification Steps:
- Run `python -m py_compile harnessiq/agents/leads/agent.py harnessiq/agents/leads/__init__.py tests/test_leads_agent.py`.
- Run `python -m pytest tests/test_leads_agent.py`.
- Run `python -m pytest tests/test_leads_shared.py tests/test_agents_base.py`.
- Run `python -m pytest tests/test_linkedin_agent.py`.
- Run `python -m pytest tests/test_knowt_agent.py`.
Dependencies: Tickets 1, 2, and 3.
Drift Guard: This ticket must not expand into CLI command design, docs polish, or new provider implementations. Its responsibility is the SDK harness and its deterministic runtime behavior.
