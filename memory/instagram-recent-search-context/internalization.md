### 1a: Structural Survey

Top-level architecture:
- `harnessiq/` contains the shipped SDK runtime, agent harnesses, shared models, integrations, tools, CLI entrypoints, and utility infrastructure.
- `tests/` contains Python unit/integration-style coverage for the runtime and concrete agents. The project uses `unittest`-style tests that are typically run via `pytest` or `python -m pytest`.
- `artifacts/file_index.md` is the authoritative repository-shape artifact and reinforces that durable memory and parameter sections are first-class design constraints for autonomous agents.
- `memory/` holds task-local planning and other persisted agent artifacts. Existing task folders indicate this repo already uses task-scoped memory documentation.

Relevant stack and conventions:
- Language/runtime: Python 3.11+ (`pyproject.toml`).
- Packaging: `setuptools`.
- Testing: repo-local tests under `tests/`; no linter or type-checker configuration is declared in `pyproject.toml`.
- Agent pattern: concrete harnesses inherit from `harnessiq.agents.base.BaseAgent`, implement `build_system_prompt()` and `load_parameter_sections()`, and optionally refresh parameter sections after tool calls that mutate durable state.
- Context-window pattern: parameter sections are injected at the front of the model request; transcript entries follow. Tool results are serialized into the transcript as JSON strings, so verbose tool payloads directly consume context.
- Durable memory pattern: per-agent memory stores live under `harnessiq/shared/` and read/write canonical JSON or text files inside an agent memory folder.

Relevant module survey:
- `harnessiq/agents/base/agent.py` defines the shared run loop, transcript recording, context-window assembly, and reset behavior. The parameter block is authoritative durable state; tool results are appended verbatim into transcript entries.
- `harnessiq/agents/instagram/agent.py` is the concrete Instagram keyword-discovery harness. It builds the system prompt, injects durable parameter sections, registers the `instagram.search_keyword` tool, and refreshes parameter sections after each search.
- `harnessiq/agents/instagram/prompts/master_prompt.md` tells the model how to consume the Instagram parameter sections and how to choose next keywords.
- `harnessiq/shared/instagram.py` defines the Instagram config, search/lead records, durable memory store, and canonical Google query construction.
- `harnessiq/cli/instagram/commands.py` exposes CLI management and summary output for the Instagram agent. It reads persisted search history, but the current task targets the agent context window rather than CLI summary shape.
- `tests/test_instagram_agent.py` covers parameter ordering, tool behavior, persistence, and import surface for the Instagram harness.
- `tests/test_instagram_cli.py` covers CLI setup and read-model behavior; likely unaffected unless this change unintentionally alters durable memory formats.

Inconsistencies / notable observations:
- The Instagram agent currently injects both `Recent Searches` and `Recent Search Results`, while the prompt instructs the model to read both. This differs from the user’s desired minimal-memory strategy for keyword ideation.
- `recent_result_window` remains a configurable runtime parameter even though removing `Recent Search Results` from the parameter block would make it unused in the agent context path.
- The search tool currently returns `query` and `visited_urls`, which are high-token transcript payloads relative to their planning value.

### 1b: Task Cross-Reference

User request mapping:
- “Recent searches in the context window should only contain the actual keywords used by the agent for searching, not anything else” maps to `InstagramKeywordDiscoveryAgent.load_parameter_sections()` in `harnessiq/agents/instagram/agent.py`, which currently serializes full `InstagramSearchRecord.as_dict()` objects.
- “They should be separated by commas” maps to the rendering format of the `Recent Searches` parameter section in `harnessiq/agents/instagram/agent.py`. The current `_json_block(...)` output is JSON, not a comma-delimited keyword list.
- “Remove the recent search results from the context window” maps to removing the `Recent Search Results` parameter section from `load_parameter_sections()` and updating any prompt/test expectations that currently require it.
- “Same thing with the tool result” maps to `_handle_search_keyword()` in `harnessiq/agents/instagram/agent.py`. The current tool result returns `query` and `visited_urls`, which bloat the transcript. The minimal useful result should preserve status and compact counts while dropping bulky search metadata.
- “The whole point of the agent is to come up with new searches” maps to the Instagram master prompt in `harnessiq/agents/instagram/prompts/master_prompt.md`. The prompt should steer off the reduced `Recent Searches` section only, without depending on a removed `Recent Search Results` section.

Behavior that must be preserved:
- Durable search history storage in `search_history.json` must remain intact. The repo still needs canonical persisted search records for CLI visibility and offline inspection.
- Lead persistence and deduplication in `InstagramMemoryStore.merge_leads()` must remain unchanged.
- Duplicate-keyword suppression via `has_searched()` must remain unchanged.
- Parameter refresh after `instagram.search_keyword` execution must remain unchanged so the next cycle sees the updated recent keyword list.

Expected blast radius:
- Direct code changes should be limited to:
  - `harnessiq/agents/instagram/agent.py`
  - `harnessiq/agents/instagram/prompts/master_prompt.md`
  - `tests/test_instagram_agent.py`
- Read-only verification may touch:
  - `harnessiq/shared/instagram.py`
  - `tests/test_instagram_cli.py`

### 1c: Assumption & Risk Inventory

Assumptions:
- “Same thing with the tool result” means the search tool transcript payload should be minimized, not eliminated. Preserving `keyword`, `status`, counts, and merge summary is sufficient for the agent to understand search outcomes without query/url bloat.
- The user wants only the agent context window reduced, not the durable memory schema or CLI summary output changed.
- A comma-separated string is preferred over JSON for `Recent Searches`, even when there are zero or one recent keywords.
- Backward compatibility for persisted search history files matters more than removing now-unused fields/config immediately.

Risks:
- If the prompt still references removed `Recent Search Results`, the agent will be instructed to look for a section that no longer exists.
- If tests only assert loose string presence, they may miss a formatting regression in the new comma-separated rendering.
- If the tool result is reduced too aggressively, the model may lose useful feedback about search productivity. Keeping counts and merge summary mitigates this.
- `recent_result_window` may become dead configuration after this change. Removing it now would widen scope into CLI/runtime compatibility, so that should stay out of scope for this ticket.

Resolution:
- Proceed without a clarification round. The implementation can be made unambiguous by keeping durable storage unchanged, shrinking only the injected parameter content and the search tool transcript payload, and updating tests/prompt text accordingly.

Phase 1 complete.
