### 1a: Structural Survey

Top-level architecture:
- `harnessiq/` is the authoritative runtime package. `src/` and `build/` are generated/residual and should not be edited.
- `harnessiq/agents/` contains concrete harnesses layered on `harnessiq.agents.base.BaseAgent`.
- `harnessiq/shared/` contains durable memory stores, manifest metadata, parameter coercion, and cross-agent data models.
- `harnessiq/tools/` contains deterministic tool definitions and bound handler factories used by harnesses.
- `harnessiq/cli/` and `harnessiq/cli/adapters/` expose both legacy and platform-first command surfaces over the same manifests/stores.
- `tests/` uses `unittest` and covers agents, CLI, shared models, providers, and tooling.
- `artifacts/file_index.md` is generated and establishes repo conventions; edits must follow the live `harnessiq/` tree rather than generated mirrors.

Relevant runtime conventions:
- Concrete agents assemble a static system prompt plus dynamic parameter sections and keep durable state in memory files outside the transcript.
- Shared manifests in `harnessiq/shared/*` are the source of truth for prompt path, CLI adapter path, runtime/custom parameter specs, and memory files.
- CLI `prepare/configure/show/run` flows persist data through shared memory stores, then instantiate agents from memory.
- Tests assert on parameter-section ordering/content, persisted JSON layout, and CLI JSON output.

Instagram-specific shape:
- `harnessiq/agents/instagram/agent.py` implements `InstagramKeywordDiscoveryAgent`.
- `harnessiq/shared/instagram.py` defines `InstagramMemoryStore`, persisted filenames, ICP resolution helpers, and manifest metadata.
- `harnessiq/tools/instagram/operations.py` binds the deterministic `instagram.search_keyword` tool to the memory store and backend.
- `harnessiq/cli/instagram/commands.py` and `harnessiq/cli/adapters/instagram.py` expose the Instagram harness from persisted memory.
- `tests/test_instagram_agent.py` and `tests/test_instagram_cli.py` cover the current behavior.

Observed current behavior:
- The system prompt is a multi-section markdown instruction file at `harnessiq/agents/instagram/prompts/master_prompt.md`.
- The agent currently injects the full ICP list in one `ICP Profiles` parameter section.
- Recent searches are global: `search_history.json` stores a flat list and `load_parameter_sections()` injects one comma-separated list across all ICPs.
- The search tool deduplicates globally through `InstagramMemoryStore.has_searched(keyword)` and appends global history through `append_search(record)`.
- The Instagram agent does not currently rotate one active ICP at a time the way the leads agent does.

### 1b: Task Cross-Reference

User request mapping:
- "update our Instagram leads agent" maps to the Instagram harness under `harnessiq/agents/instagram/agent.py`, not the multi-provider leads harness. The repo manifest names this harness `instagram`.
- "system prompt ... expressed more clearly in around one to three paragraphs of natural language" maps to `harnessiq/agents/instagram/prompts/master_prompt.md`.
- "if the user lists multiple icps then we should deterministically go through each one" maps to agent run-loop behavior in `harnessiq/agents/instagram/agent.py`.
- "Only input one ICP in the context window for the agent" maps to `load_parameter_sections()` in `harnessiq/agents/instagram/agent.py`.
- "have a list of recent searches for each ICP" maps to persistent storage in `harnessiq/shared/instagram.py` and tool dedupe logic in `harnessiq/tools/instagram/operations.py`.
- "loop through each ICP and the agent should only have one ICP and one ICP's recent searches in the context window" maps to adding durable per-ICP state plus run-state tracking similar to the leads harness pattern.
- "adhere to the file index" means modifying only the live `harnessiq/` tree plus matching tests/docs/artifacts generated from source if needed.
- "create a pull request into main" maps to GitHub workflow via `gh`, with a feature branch and PR base `main`.

Concrete files likely touched:
- `harnessiq/agents/instagram/agent.py` for ICP rotation, active-context injection, and run-state persistence.
- `harnessiq/shared/instagram.py` for per-ICP durable state models/store helpers and manifest memory-file updates.
- `harnessiq/tools/instagram/operations.py` for ICP-scoped dedupe and append behavior.
- `harnessiq/agents/instagram/prompts/master_prompt.md` for the prompt rewrite.
- `harnessiq/cli/instagram/commands.py` and `harnessiq/cli/adapters/instagram.py` for JSON summaries if search history shape changes.
- `tests/test_instagram_agent.py` and `tests/test_instagram_cli.py` for behavior updates and regression coverage.
- Potentially `README.md` / `docs/` if the repo expects user-facing harness docs to stay aligned with behavior.

Behavior that must be preserved:
- Search backend contract and deterministic `instagram.search_keyword` tool surface.
- Existing single-ICP runs should still work.
- Persisted leads/emails and ledger outputs should remain available.
- CLI configure/run overrides for ICPs and custom params should still work.

Blast radius:
- Medium. The change is localized to the Instagram harness, but it touches persistence shape, run orchestration, tool dedupe semantics, prompt construction, and tests.

### 1c: Assumption & Risk Inventory

Assumptions used for implementation:
- The target harness is `InstagramKeywordDiscoveryAgent`, because it is the repo's only Instagram lead-discovery harness and already owns ICP/search memory.
- Deterministic ICP traversal means preserving user-supplied order and iterating serially, one active ICP at a time, across a run.
- "Only input one ICP in the context window" means the parameter section should contain the active ICP only, not the full list.
- "One ICP's recent searches in the context window" means recent-search injection and duplicate checking should be scoped to the active ICP, not global across all ICPs.
- It is acceptable to migrate legacy `search_history.json` data into the new per-ICP structure lazily rather than forcing a breaking one-shot migration.

Risks to manage:
- Existing memory folders already contain `search_history.json`; changing storage shape could break old runs if not backward-compatible.
- The current tool layer has no notion of active ICP, so the bound handler needs an injected ICP resolver without affecting the public tool schema.
- The base Instagram agent currently uses `BaseAgent.run()`; serial ICP rotation likely requires a custom run loop similar to `LeadsAgent`.
- CLI `show` output currently assumes a flat search history list. The summary payload needs a stable, comprehensible replacement.
- Tests currently assert the old parameter title/content (`ICP Profiles`, global comma-separated searches) and will need targeted updates.

Phase 1 complete.
