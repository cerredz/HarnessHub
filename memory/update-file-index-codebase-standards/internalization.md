# Internalization

## 1a: Structural Survey

Repository shape:

- `artifacts/file_index.md` is the maintained architecture index for repository structure and standards-level guidance.
- `harnessiq/agents/` contains the reusable agent runtime and the concrete harnesses currently shipped by the SDK: base, email, LinkedIn, Knowt, and Exa outreach.
- `harnessiq/agents/base/agent.py` defines `BaseAgent`, the canonical long-running agent loop with context-window construction, tool execution, compaction, and reset behavior.
- `harnessiq/providers/` contains provider-specific request builders, HTTP clients, and operation catalogs for both LLM providers and third-party service APIs.
- `harnessiq/tools/` contains the runtime tool layer used by agents, including built-in deterministic tools, compaction helpers, prompt helpers, filesystem helpers, and provider-backed tool factories.
- `harnessiq/toolset/` adds a higher-level registry/catalog access layer for built-in, provider, and custom tools.
- `harnessiq/shared/` carries stable shared models and constants, including agent runtime types and durable memory-file definitions for concrete agents such as LinkedIn.
- `docs/` and `README.md` document the public SDK/runtime model and are useful as secondary confirmation for terminology already implemented in code.
- `tests/` uses `unittest` and covers runtime behavior, provider integration helpers, tool execution, and concrete agent memory behavior.

Technology and conventions:

- The repository is a Python package managed through `pyproject.toml` and uses stdlib `unittest`; no repo-level linter or standalone type checker is configured.
- Existing documentation describes architecture in terms of agents, tools, providers, durable parameter sections, and reset-aware execution rather than as ad hoc prompts with optional tools.
- `BaseAgent` is the single inheritance point for agent runtime behavior. It owns `memory_path`, durable parameter loading, transcript management, compaction handling, and automatic context reset.
- Concrete agent memory is file-backed. The LinkedIn harness in particular persists durable files such as `applied_jobs.jsonl`, `action_log.jsonl`, `runtime_parameters.json`, and `custom_parameters.json`.
- Provider access is intentionally separated from agent logic: provider packages expose clients/request builders, while tool packages expose runtime-callable `RegisteredTool` factories that agents can execute deterministically.

Observed documentation inconsistencies relevant to this task:

- `artifacts/file_index.md` already contains useful source-layout detail, but the beginning of the file currently jumps straight into directory listings without an explicit standards section.
- The file contains a few duplicated entries (`harnessiq/config/`, `harnessiq/providers/`, `harnessiq/tools/reasoning/`, and several repeated test bullets), so any new change should stay narrowly scoped to the requested standards preface rather than silently refactoring the whole artifact.

## 1b: Task Cross-Reference

User request mapping:

- "Update the beginning of our file index with more information of our codebase standards" maps directly to `artifacts/file_index.md`, specifically the introductory section before the top-level directory inventory.
- "we define agents, these agents interact with our tools and third party platforms through our providers" is grounded in `harnessiq/agents/base/agent.py`, `harnessiq/tools/`, `harnessiq/toolset/`, and `harnessiq/providers/`, plus the runtime/provider descriptions in `README.md`.
- "each agent has a memory folder" is consistent with concrete harness behavior documented in `README.md`, `docs/linkedin-agent.md`, and file definitions in `harnessiq/shared/linkedin.py`.
- "tools should be used, where applicable, to deterministically check things" is supported by the existing tool/memory architecture, especially LinkedIn durable logs such as `applied_jobs.jsonl` and `action_log.jsonl`.
- "we are building these agents for full autonomy, so it needs to take into consideration multiple context window resets" maps to `BaseAgent.run()`, `_should_reset_context()`, `reset_context()`, and the durable parameter-section model in `harnessiq/agents/base/agent.py`.
- "each agent inherits from the main base agent class, behavior can also be set through parameters, users can define these parameters" maps to `BaseAgent` inheritance plus persisted runtime and custom parameter files documented in `README.md` and modeled in `harnessiq/shared/linkedin.py`.

Concrete file impact:

- `artifacts/file_index.md`: add a concise "codebase standards" preface near the top of the document.
- `memory/update-file-index-codebase-standards/`: store internalization, clarification status, ticket, quality notes, and critique for this documentation task.

Behavior to preserve:

- Existing user edits already present in `artifacts/file_index.md` must be preserved.
- The file index should remain an architecture artifact, not become a long-form design doc.
- The new standards language must describe current repository behavior or clear repository intent already encoded in code/docs; it should not invent unimplemented runtime guarantees.

## 1c: Assumption & Risk Inventory

Assumptions:

- The requested additions are intended as architecture/standards guidance, not as a demand to implement new runtime behavior in this task.
- "Each agent has a memory folder" is meant as the project standard for autonomous harnesses and current concrete agents, even though `BaseAgent` itself supports `memory_path=None`.
- "Users can define these parameters" refers to runtime/custom parameter surfaces already present in the concrete harnesses, especially LinkedIn.

Risks and ambiguities:

- The request says agents interact with third-party platforms "through our providers." In the current codebase, provider packages and tool factories are distinct layers. The standards wording should reflect the actual path: agents use tools, and provider-backed tools/clients mediate platform access.
- The request on deterministic checks could be overstated if phrased as "all behavior must be deterministic." The safer language is that tools should be used wherever a deterministic check is possible, especially against durable memory/state.
- Not every current agent may expose the same parameter surface, so the wording should describe a shared pattern rather than imply identical configuration files for every harness.

Phase 1 complete
