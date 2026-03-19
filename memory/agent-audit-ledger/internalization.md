### 1a: Structural Survey

Repository shape:

- `harnessiq/` is the shipped SDK package. The runtime core lives in `harnessiq/agents/base/agent.py` and shared type/config definitions live in `harnessiq/shared/agents.py`.
- `harnessiq/agents/` contains the common `BaseAgent` plus four concrete harness families currently in the repo: LinkedIn, Exa Outreach, Knowt, and Email. Concrete agents own prompts, parameter sections, memory stores, and deterministic helper tools.
- `harnessiq/cli/` contains the package CLI. The top-level parser in `harnessiq/cli/main.py` currently registers only `linkedin` and `outreach` subcommands. There is no existing global connection-management or log-export command surface.
- `harnessiq/providers/` contains provider-facing translation/client code. It also includes cross-provider helpers such as `langsmith.py` and `http.py`. This is the natural location for provider-specific ledger metadata extraction if the ledger needs provider-aware normalization without polluting agent runtime code.
- `harnessiq/utils/` contains agent-agnostic support code. Existing contents include agent instance/id helpers and `run_storage.py`, which already establishes a precedent for reusable persistence utilities outside any single harness.
- `harnessiq/shared/` contains dataclasses, typed dicts, constants, and memory-store models used across modules. `shared/agents.py` is the current canonical home for runtime datamodels like `AgentRuntimeConfig` and `AgentRunResult`.
- `tests/` is mixed `unittest` and `pytest`. Runtime tests target public behavior rather than private implementation details. CLI tests invoke `harnessiq.cli.main.main(...)` directly and inspect stdout/stderr payloads.
- `artifacts/file_index.md` is a curated architecture index rather than a full inventory. It must be updated when new structural concepts become part of the repo’s stable architecture.

Runtime architecture:

- `BaseAgent.run()` is a tight synchronous loop. It prepares the agent, clears transcript/reset counters, refreshes parameter sections, iterates model turns, executes tool calls, handles pause signals, performs context resets, and returns `AgentRunResult`.
- `AgentRuntimeConfig` currently contains only token-budget controls (`max_tokens`, `reset_threshold`). It is the correct injection point for framework-level post-run sink configuration because it is already passed into all agents.
- `AgentRunResult` currently captures terminal outcome only: `status`, `cycles_completed`, `resets`, `pause_reason`. No durable run identifier or output payload is attached today.
- Concrete agents own durable domain state:
  - LinkedIn uses `LinkedInMemoryStore` and structured records such as `JobApplicationRecord`.
  - Exa Outreach uses `ExaOutreachMemoryStore` plus `FileSystemStorageBackend` in `utils/run_storage.py`-style form to persist run JSON files under `memory_path/runs/`.
  - Knowt persists generated content in files managed by `KnowtMemoryStore`.
  - BaseEmailAgent has no additional durable run store today beyond prompt/config state.

Existing persistence patterns:

- `harnessiq/utils/run_storage.py` defines a pluggable persistence protocol and default filesystem backend for Exa-style per-run JSON files. This is conceptually similar to the new ledger but is agent-specific and event-oriented, not framework-wide and envelope-oriented.
- LinkedIn persists durable application/action records in JSONL files inside agent memory.
- There is no shared append-only global run ledger, no shared run export/query layer, and no framework-level output sink protocol.

Conventions relevant to the task:

- Dataclasses and typed protocols live under `shared/` when they define SDK-wide contracts.
- Utilities with concrete persistence logic live under `utils/`.
- Provider-specific adaptation code lives under `providers/`.
- Public package exports are maintained explicitly in `__init__.py` files.
- Tests prefer lightweight fake models and temporary directories.
- The repo is currently in a dirty state with many unrelated user changes, so implementation must avoid reverting or refactoring adjacent code outside the ledger scope.

Inconsistencies observed:

- The design spec proposes a new framework-level ledger while the repo already has Exa Outreach run storage with overlapping intent but different shape.
- The spec uses `reset_count`; the current runtime/result model uses `resets`.
- The spec mentions statuses including `"error"` while the current `BaseAgent.run()` does not catch top-level exceptions and therefore never returns an error `AgentRunResult`.
- The spec describes globally configured sinks and connection management, but the current CLI/runtime has no global config-loading mechanism for sinks.

### 1b: Task Cross-Reference

User request mapped to codebase:

- “Build the ledger / audit trail for all agents” maps first to `harnessiq/shared/agents.py` and `harnessiq/agents/base/agent.py` because every agent passes through `BaseAgent.run()`.
- “Place this ledger's main code inside of the utils folder” maps to a new `harnessiq/utils` module for the universal ledger entry model, sink protocol, JSONL persistence, and ledger query/export helpers.
- “Provider specific code can be placed in the providers folder” maps to a new provider helper module under `harnessiq/providers/` for best-effort extraction of provider/model metadata from the injected model adapters.
- “Add the ledger information to our file index” maps to `artifacts/file_index.md`.
- The design’s Tier 1 baseline (“always-on JSONL ledger”) maps cleanly onto:
  - `AgentRuntimeConfig` gaining sink configuration and/or default sink resolution.
  - `BaseAgent.run()` constructing a ledger entry after terminal completion and dispatching sinks in failure-swallowing order.
  - New filesystem-backed JSONL sink code under `utils/`.
- The design’s universal envelope requires per-agent output extraction. That maps to new overridable hooks on `BaseAgent` plus concrete overrides in:
  - `harnessiq/agents/linkedin/agent.py`
  - `harnessiq/agents/exa_outreach/agent.py`
  - `harnessiq/agents/knowt/agent.py`
  - `harnessiq/agents/email/agent.py` (likely default envelope-only behavior for base email harnesses)
- The design’s Tier 4 CLI read/export/report maps to `harnessiq/cli/main.py` plus a new CLI module for ledger commands. Existing CLI tests establish the pattern for adding top-level command groups and JSON/markdown/csv output assertions.

Relevant existing behavior that must be preserved:

- `AgentRunResult` return shape and status semantics must remain backward-compatible for current tests and callers.
- Sink failures must never change a successful/paused/max-cycle agent result into a failed run.
- Existing per-agent persistence (LinkedIn memory files, Exa run files) must continue untouched; the ledger supplements rather than replaces them.
- CLI output for existing `linkedin` and `outreach` commands must not regress.

Net-new work implied by the request:

- Universal `LedgerEntry` model and serialization.
- `OutputSink` protocol and default JSONL sink.
- Post-run dispatch block inside `BaseAgent.run()`.
- Agent hooks for declaring tags/outputs/extra metadata.
- Provider metadata extraction helper.
- CLI commands to inspect/export/report from the ledger baseline.
- File index update reflecting the new audit-ledger architecture.

Blast radius:

- Core runtime (`shared/agents.py`, `BaseAgent`) because every agent run flows through it.
- All concrete agents because meaningful `outputs` need per-agent declarations.
- Public SDK exports because new ledger types/helpers should be importable.
- CLI parser because new top-level commands will be added.
- Tests across runtime, CLI, and concrete agents.

### 1c: Assumption & Risk Inventory

Assumptions driving implementation:

- The task is to ship the framework baseline that is viable in the current repo now: universal ledger entry model, always-on JSONL sink, and CLI read/export/report over that ledger. External sinks (`MongoDB`, Google Sheets, Obsidian, Notion, Excel) and connection management are follow-on work, not required for this task.
- “All agents” means the currently implemented harnesses in this repository, not arbitrary downstream user-defined subclasses. The framework will still support subclasses through defaults and overridable hooks.
- Provider-specific code in `providers/` should be limited to metadata normalization/extraction, not to implementing external sink integrations yet.
- The ledger should record only terminal runs (`completed`, `paused`, `max_cycles_reached`) for now because `BaseAgent` does not currently convert uncaught exceptions into an `"error"` result.

Material risks:

- Adding new fields to `AgentRuntimeConfig` can ripple through existing tests if defaults or dataclass semantics change unexpectedly.
- Adding post-run hooks inside `BaseAgent.run()` can accidentally duplicate code paths or miss paused/max-cycle returns if not centralized carefully.
- Exa Outreach already has its own run store. Poorly designed hooks could create inconsistent “outputs” between its per-run JSON files and the new ledger.
- CLI export/report output formats can sprawl quickly; scope control is important to keep the baseline maintainable.
- The repo’s dirty working tree increases merge/conflict risk, especially in already-modified files like `BaseAgent`, agent modules, and `artifacts/file_index.md`.

Open ambiguities resolved by implementation choice:

- The spec mentions an `"error"` ledger status. I will preserve the current runtime behavior and only emit statuses that the runtime actually returns today; if an exception escapes the run loop, no terminal ledger entry is written because there is no completed run to sink.
- The spec mentions framework-stamped metadata like total tokens. The current runtime can reliably stamp best-effort request metrics and provider/model identity, but not authoritative provider token usage because the model adapter contract does not expose it.
- The spec mentions a new mandatory harness-side outputs schema. For this task I will implement concrete output extraction hooks for the built-in agents instead of introducing a second declarative schema system everywhere at once.

Phase 1 complete.
