### 1a: Structural Survey

Repository shape and architecture:

- `harnessiq/agents/` contains the provider-agnostic runtime (`BaseAgent`) plus concrete harnesses (`linkedin`, `email`, `exa_outreach`, `knowt`).
- `harnessiq/shared/` contains the durable dataclasses and configuration objects each harness depends on. Existing patterns place agent-specific memory stores and typed records here when they are reused across modules.
- `harnessiq/tools/` contains executable `RegisteredTool` factories. Built-in families cover context compaction, filesystem, general-purpose transforms, prompt generation, and reasoning. Provider families expose MCP-style request tools for each external service.
- `harnessiq/providers/` contains provider-specific operation catalogs, request preparation, credentials, and clients. These are intentionally separated from agent code so harnesses depend on tool factories rather than raw HTTP logic.
- `harnessiq/toolset/` is a catalog-backed lazy registry that can resolve built-in or provider tools by family/key from metadata. This is relevant because a new leads agent can accept provider families as configuration and resolve them into tool surfaces instead of hard-coding one provider.
- `harnessiq/utils/run_storage.py` provides an existing pluggable `StorageBackend` protocol plus a default `FileSystemStorageBackend` writing per-run JSON event logs under `memory/<agent>/runs/`.
- `tests/` uses deterministic fake models and fake clients to verify agent behavior, tool registration, and memory-store side effects. Current agent tests focus on prompt assembly, parameter-section ordering, internal tool behavior, and durable state across resets.

Key runtime conventions:

- Concrete agents subclass `BaseAgent`, build a system prompt, and expose durable parameter sections via `load_parameter_sections()`.
- Durable memory is deterministic and file-backed. Mutable, long-lived state is written in internal tool handlers or memory-store helpers rather than trusted to the model transcript.
- Provider tools are injected as `RegisteredTool` instances. Concrete harnesses compose those with internal tools into a `ToolRegistry`.
- Context management is transcript-based. `BaseAgent` records assistant turns, tool calls, and tool results; when the estimated token budget exceeds `AgentRuntimeConfig.reset_token_limit`, it resets transcript state and reloads durable parameter sections.
- Compaction tools already exist (`context.remove_tool_results`, `context.remove_tools`, `context.heavy_compaction`, `context.log_compaction`) and can rewrite the context window when invoked.

Existing concrete-agent patterns:

- `LinkedInJobApplierAgent` is the closest example of a long-running operational harness with durable file-backed state and internal tools for action logging, state mutation, and pause behavior.
- `ExaOutreachAgent` is the closest example of a prospecting agent. It uses a generic `StorageBackend`, deterministic event logging, injected provider tools, and a specialized memory store. Its internal tools are small and purpose-built: dedupe check, lead logging, template retrieval, and email logging.
- `BaseEmailAgent` demonstrates how to wire a reusable provider-backed tool surface into a domain-specific agent harness without duplicating runtime logic.

Testing and packaging conventions:

- Packaging is `setuptools`-based via `pyproject.toml`; public SDK exports are kept in `harnessiq/agents/__init__.py` and package-level `__init__.py`.
- Tests primarily use `pytest` with some `unittest` modules. New agent work should add direct tests for construction, prompt/parameter assembly, internal tool side effects, and run-loop behavior.
- `artifacts/file_index.md` is maintained as the high-level architectural map and should be updated if a new meaningful agent/shared module tree is added.

Observed inconsistencies or risks in the current codebase:

- There is some duplication in docs and exports (for example repeated entries in `artifacts/file_index.md` and repeated imports in `harnessiq/tools/__init__.py`), so new work should avoid copying those inconsistencies forward.
- The repo worktree is dirty before this task (`.gitignore`, `artifacts/file_index.md`, `harnessiq/cli/linkedin/commands.py`, `harnessiq/integrations/linkedin_playwright.py`, plus multiple untracked paths). Any changes for this task must avoid reverting unrelated work.
- No existing generic “lead discovery” shared types exist beyond Exa outreach records, so a new leads agent should either extend the generic run-storage/event model or introduce a narrowly scoped shared module instead of overloading unrelated outreach abstractions.

### 1b: Task Cross-Reference

User request mapped onto the codebase:

- The requested feature is a new autonomous “leads agent” that accepts company background plus multiple ICPs, loops per ICP, uses injected provider tools (examples given: Apollo, LeadIQ, Lemlist), runs sequential searches, saves discovered leads to a configurable destination, and manages context bloat by summarizing search history on a configurable interval.
- The closest implementation anchor is `harnessiq/agents/exa_outreach/agent.py`, because it already models prospect discovery, pluggable storage, and provider tool injection. The new leads agent should follow this structural pattern instead of extending `LinkedInJobApplierAgent`.
- New agent code will likely live under `harnessiq/agents/leads/` with a harness class analogous to `ExaOutreachAgent`.
- Shared types and memory-store logic will likely need a new `harnessiq/shared/leads.py` module containing config dataclasses, ICP and lead records, search-log records, and a file-backed memory store.
- Public exports will need updates in `harnessiq/agents/__init__.py` and possibly `harnessiq/__init__.py` only if package-level exposure is required.
- Tests will likely need a dedicated `tests/test_leads_agent.py` and possibly `tests/test_leads_shared.py`.
- `artifacts/file_index.md` should be updated if `harnessiq/agents/leads/` and `harnessiq/shared/leads.py` are added.

Relevant existing modules for reuse:

- `harnessiq/agents/base/agent.py`: generic loop, transcript, reset threshold logic.
- `harnessiq/shared/agents.py`: runtime config and parameter-section types.
- `harnessiq/utils/run_storage.py`: generic run persistence and dedupe scanning.
- `harnessiq/tools/context_compaction.py`: existing compaction primitives that may support rolling search summarization.
- `harnessiq/toolset/registry.py` and `harnessiq/toolset/catalog.py`: useful if the agent should resolve provider families dynamically from config rather than receive prebuilt tools.
- Provider tool factories already in repo and directly relevant to lead discovery or downstream save/action workflows:
  - `harnessiq/tools/leadiq/operations.py`
  - `harnessiq/tools/lemlist/operations.py`
  - `harnessiq/tools/outreach/operations.py`
  - `harnessiq/tools/peopledatalabs/operations.py`
  - `harnessiq/tools/zoominfo/operations.py`

What exists versus what is missing:

- Exists:
  - Generic runtime loop and transcript-reset logic.
  - Provider tool factories and operation catalogs for multiple lead-data platforms.
  - Generic file-backed run storage with a pluggable backend protocol.
  - Prospecting precedent through `ExaOutreachAgent`.
- Missing:
  - A multi-ICP lead-discovery harness.
  - Typed memory/state objects for company background, ICP queue/state, search logs, saved leads, and dedupe strategy.
  - Internal tools for logging searches, persisting leads, deduplicating discovered people, and marking ICP progress/completion.
  - A concrete contract for configurable provider selection and save destinations tailored to this use case.
  - A deterministic mechanism that matches the user’s requested “search history summarized every N searches” behavior.

Blast radius:

- Primary blast radius is isolated to new modules plus agent exports and docs/tests.
- If the implementation requires stronger transcript-control semantics than `BaseAgent` currently exposes, there may be limited impact on the shared runtime. That should be avoided unless necessary because `LinkedInJobApplierAgent`, `KnowtAgent`, and `ExaOutreachAgent` all depend on the current behavior.

### 1c: Assumption & Risk Inventory

Open assumptions currently embedded in the task:

- The initial implementation likely should support provider injection using the platforms already present in the repo, not a full Apollo integration, because Apollo tooling is not in this codebase.
- “Save destination” may mean a generic storage abstraction with a default filesystem backend, not first-class Google Drive/database integrations in the first pass.
- “Each ICP gets an agent loop” could mean either:
  - one long-running agent with internal state that advances through ICPs, or
  - a controller that instantiates a fresh per-ICP run.
  This changes the harness boundary and memory model.
- “Reset tool calls after every iteration” cannot be expressed deterministically by the current `BaseAgent` API without either:
  - model-invoked compaction tools,
  - durable state moved out of transcript and transcript resets relied upon opportunistically, or
  - runtime changes to `BaseAgent`.
- “Summarize every 500 searches” needs a concrete definition of a “search” record and whether summarization is LLM-generated or deterministic.

Primary implementation risks:

- If the task expects a fully deterministic transcript-pruning protocol exactly matching the conversation, the current base runtime may be too limited unless shared runtime changes are introduced.
- If the task expects first-class support for arbitrary save targets like Google Drive or databases, implementing only file-backed storage would be incomplete unless the acceptance criteria explicitly allow a pluggable abstraction with one default backend.
- If multiple provider platforms are enabled simultaneously, the agent needs a clear contract for tool ordering, provider capabilities, and dedupe keys; otherwise the model may waste credits or save overlapping leads.
- If internal lead dedupe depends only on transcript memory, resets will cause repeat enrichment. Dedupe needs to live in deterministic storage or memory-store indexes.
- CLI scope is unspecified. Adding CLI commands would broaden the blast radius significantly compared with a harness-only SDK implementation.

Recommended Phase 2 clarifications:

- Define the minimal platform scope for v1.
- Define whether v1 must implement only the agent harness/SDK surface or also CLI commands/docs/examples.
- Define the expected save-destination scope for v1.
- Define the ICP orchestration boundary and stopping conditions.
- Define whether exact transcript-compaction behavior is required or whether durable search summaries loaded into parameter sections satisfy the design intent.

Phase 1 complete.
