### 1a: Structural Survey

Harnessiq is a Python 3.11+ SDK and CLI centered on durable, tool-using agents. The live runtime source of truth is the `harnessiq/` package; `build/`, `src/`, and packaging residue are explicitly non-authoritative per [artifacts/file_index.md](C:/Users/422mi/HarnessHub/artifacts/file_index.md). The top-level architecture splits cleanly into agents, CLI, config, providers, tools, shared data models, and utilities.

The runtime core lives in [harnessiq/agents/base/agent.py](C:/Users/422mi/HarnessHub/harnessiq/agents/base/agent.py) and [harnessiq/agents/base/agent_helpers.py](C:/Users/422mi/HarnessHub/harnessiq/agents/base/agent_helpers.py). `BaseAgent` owns the generic loop, stable `instance_id` resolution via `AgentInstanceStore`, transcript/reset bookkeeping, and terminal run emission. Terminal ledger writes happen through `_emit_ledger_entry()` in the mixin, which builds a `LedgerEntry` and dispatches it to resolved output sinks. The default sink is `JSONLLedgerSink`, so the local JSONL ledger is currently implemented as just another output sink rather than a separate persistence subsystem.

Two concrete agents, [harnessiq/agents/leads/agent.py](C:/Users/422mi/HarnessHub/harnessiq/agents/leads/agent.py) and [harnessiq/agents/instagram/agent.py](C:/Users/422mi/HarnessHub/harnessiq/agents/instagram/agent.py), override the main loop because they multiplex work across multiple ICPs and already persist their own run-state files for resume. They still terminate through `_complete_run()` / `_emit_ledger_entry()`, so post-run stats can be centralized if the hook stays below the loop layer. This is the main runtime inconsistency relevant to the design doc.

Shared runtime models live in [harnessiq/shared/agents.py](C:/Users/422mi/HarnessHub/harnessiq/shared/agents.py). `AgentRuntimeConfig` is an immutable dataclass that already carries runtime controls such as token thresholds, hooks, output sinks, and approval policy, but it does not yet carry `session_id`. `AgentModelRequest.estimated_tokens()` provides the existing estimated-token primitive; there is no first-class actual-token field on `AgentModelResponse` or `AgentRunResult`.

Ledger primitives live under `harnessiq/utils/`. [harnessiq/utils/ledger_models.py](C:/Users/422mi/HarnessHub/harnessiq/utils/ledger_models.py) defines `LedgerEntry`, its JSON serialization, and terminal statuses. [harnessiq/utils/ledger_sinks.py](C:/Users/422mi/HarnessHub/harnessiq/utils/ledger_sinks.py) defines `JSONLLedgerSink` and the other output sinks. [harnessiq/utils/ledger_exports.py](C:/Users/422mi/HarnessHub/harnessiq/utils/ledger_exports.py) loads, filters, exports, and tails the ledger. [harnessiq/utils/ledger_reports.py](C:/Users/422mi/HarnessHub/harnessiq/utils/ledger_reports.py) computes the current report surface, which is simple per-agent aggregation built directly from full ledger scans. There is no existing materialized read-model layer.

Model/provider metadata is extracted today through [harnessiq/providers/output_sink_metadata.py](C:/Users/422mi/HarnessHub/harnessiq/providers/output_sink_metadata.py), which infers `provider` and `model_name` from provider-backed model adapters. This existing metadata path should be reused for stats normalization rather than re-inferred in parallel.

Platform CLI wiring lives in [harnessiq/cli/main.py](C:/Users/422mi/HarnessHub/harnessiq/cli/main.py), [harnessiq/cli/ledger/commands.py](C:/Users/422mi/HarnessHub/harnessiq/cli/ledger/commands.py), and [harnessiq/cli/commands/platform_commands.py](C:/Users/422mi/HarnessHub/harnessiq/cli/commands/platform_commands.py). The current ledger surface is top-level commands: `logs`, `export`, and `report`. There is no `stats` command family yet. CLI handlers are thin and mostly delegate to utility modules. JSON emission conventions come from [harnessiq/cli/common.py](C:/Users/422mi/HarnessHub/harnessiq/cli/common.py).

The platform-first CLI also persists replay metadata in [harnessiq/config/harness_profiles.py](C:/Users/422mi/HarnessHub/harnessiq/config/harness_profiles.py). `HarnessRunSnapshot` captures model selection, sink specs, adapter arguments, runtime/custom parameters, `recorded_at`, and a synthetic `run_number`. It does not currently persist ledger `run_id` or any session continuity identifier. Resume therefore exists today as a CLI/profile concept, not a ledger-native session concept.

Stable agent identity already exists via [harnessiq/utils/agent_instances.py](C:/Users/422mi/HarnessHub/harnessiq/utils/agent_instances.py). `AgentInstanceStore.resolve()` deterministically computes an `instance_id` from agent name plus payload fingerprint and persists instance metadata under `memory/agent_instances.json`. This is the correct source for the design doc’s identity-scoped grouping dimension.

Testing is extensive and uses `unittest` and `pytest`. The directly relevant regression surfaces are [tests/test_agents_base.py](C:/Users/422mi/HarnessHub/tests/test_agents_base.py), [tests/test_agent_instances.py](C:/Users/422mi/HarnessHub/tests/test_agent_instances.py), [tests/test_ledger_cli.py](C:/Users/422mi/HarnessHub/tests/test_ledger_cli.py), [tests/test_platform_cli.py](C:/Users/422mi/HarnessHub/tests/test_platform_cli.py), and [tests/test_harness_profiles.py](C:/Users/422mi/HarnessHub/tests/test_harness_profiles.py). Existing tests already verify default ledger writes, CLI registration, and resume snapshot persistence, so the new stats system should extend these patterns instead of inventing a new testing style.

Codebase conventions relevant to this task:

- Runtime persistence is local-filesystem first and JSON/JSONL based.
- Utility modules own cross-cutting infrastructure; agents should stay orchestration-focused.
- Fail-open behavior is already established for output sinks: sink failures are logged and swallowed.
- JSON output and deterministic ordering are preferred in storage and CLI surfaces.
- `instance_id` is already the stable identity abstraction; there is no existing `session_id` abstraction.

Inconsistencies worth noting:

- The design doc names `agent_helpers.py` as the only terminal run path, but `LeadsAgent` and `InstagramKeywordDiscoveryAgent` own custom loops and resume state. The shared terminal path is `_emit_ledger_entry()`, not the outer loop body.
- The current CLI ledger/report surface is top-level, while the design doc introduces a new nested `stats` command family.
- The design doc assumes repo-local stats live under `.harnessiq/stats/`, but the current default ledger path resolves from the Harnessiq home directory via the ledger sink/connection helpers rather than a repo-root-only path. The implementation must reconcile repo-local snapshots with whichever root the default ledger path uses.

### 1b: Task Cross-Reference

The design doc maps onto six concrete code areas.

1. Runtime session identity and stats payload generation.
   Files: [harnessiq/shared/agents.py](C:/Users/422mi/HarnessHub/harnessiq/shared/agents.py), [harnessiq/agents/base/agent.py](C:/Users/422mi/HarnessHub/harnessiq/agents/base/agent.py), [harnessiq/agents/base/agent_helpers.py](C:/Users/422mi/HarnessHub/harnessiq/agents/base/agent_helpers.py), [harnessiq/agents/leads/agent.py](C:/Users/422mi/HarnessHub/harnessiq/agents/leads/agent.py), [harnessiq/agents/instagram/agent.py](C:/Users/422mi/HarnessHub/harnessiq/agents/instagram/agent.py), [harnessiq/providers/output_sink_metadata.py](C:/Users/422mi/HarnessHub/harnessiq/providers/output_sink_metadata.py).
   Mapping: `session_id` belongs on `AgentRuntimeConfig` or an equivalent runtime-owned field because it must be assigned at run start and survive resume. The terminal `metadata["stats"]` block belongs in `_build_ledger_metadata()` so it is emitted consistently for all statuses and all agents. Tool counters must be collected during the run; today the runtime records transcript entries but not tool-call breakdown counters, so new per-run counters will need to be accumulated on the agent instance as tool calls execute.

2. Ledger-driven session lookup and stats projection.
   Files: net-new [harnessiq/utils/stats_projector.py](C:/Users/422mi/HarnessHub/harnessiq/utils/stats_projector.py) plus likely helper exports in [harnessiq/utils/__init__.py](C:/Users/422mi/HarnessHub/harnessiq/utils/__init__.py), and reads via [harnessiq/utils/ledger_exports.py](C:/Users/422mi/HarnessHub/harnessiq/utils/ledger_exports.py).
   Mapping: the design doc’s `StatsProjector` should live in `utils` alongside ledger helpers. It needs both incremental `apply_entry(entry)` and full rebuild-from-ledger capabilities. Snapshot persistence under `.harnessiq/stats/` is net-new.

3. Stats filesystem layout and atomic writes.
   Files: net-new projector module and possibly path helpers near [harnessiq/utils/ledger_connections.py](C:/Users/422mi/HarnessHub/harnessiq/utils/ledger_connections.py) if existing path resolution is reused.
   Mapping: the four snapshot files `agents.json`, `instances.json`, `sessions.json`, and `daily.json` do not exist. Atomic write semantics should stay in the projector layer because snapshot files are explicitly read models, not general configuration.

4. CLI command surface.
   Files: [harnessiq/cli/main.py](C:/Users/422mi/HarnessHub/harnessiq/cli/main.py), net-new module such as [harnessiq/cli/stats/commands.py](C:/Users/422mi/HarnessHub/harnessiq/cli/stats/commands.py) and corresponding `__init__.py`, plus helper reuse from [harnessiq/cli/common.py](C:/Users/422mi/HarnessHub/harnessiq/cli/common.py).
   Mapping: the design doc introduces a new top-level `stats` parser subtree with `summary`, `agent`, `session`, `instance`, `rebuild`, and `export`. Existing `logs` / `export` / `report` should remain untouched unless tests or naming collisions force small wiring adjustments.

5. Tests.
   Files: [tests/test_agents_base.py](C:/Users/422mi/HarnessHub/tests/test_agents_base.py), [tests/test_ledger_cli.py](C:/Users/422mi/HarnessHub/tests/test_ledger_cli.py), [tests/test_platform_cli.py](C:/Users/422mi/HarnessHub/tests/test_platform_cli.py), and net-new targeted stats tests such as `tests/test_stats_projector.py` and `tests/test_stats_cli.py`.
   Mapping: projector rebuild vs incremental equivalence needs dedicated tests. Runtime tests must verify that ledger entries now include the normalized `metadata["stats"]` block, that `session_id` is stable across resumed runs, and that projector failures are swallowed. CLI tests must verify parser registration and outputs for `stats` commands.

6. GitHub-ticket workflow artifacts requested by the user.
   Files: `memory/harnessiq-stats-analytics-system/tickets/`.
   Mapping: ticket docs and issue creation are orthogonal to runtime code, but they must reflect the actual dependency order in the implementation: runtime stats payload first, projector/storage second, CLI/reporting third.

Behavior that must be preserved while implementing the design:

- `runs.jsonl` remains append-only and authoritative.
- Existing CLI `logs`, `export`, and `report` behavior must not regress.
- Output-sink failures remain non-fatal to agent runs.
- Existing `instance_id` stability guarantees from `AgentInstanceStore` must remain unchanged.
- Existing platform resume behavior via `HarnessRunSnapshot` must keep working even before any new stats-driven session lookup is used.

Net-new functionality required by the design:

- `session_id` assignment and reuse across pause/resume and max-cycle restarts.
- A normalized immutable `metadata["stats"]` block on every terminal ledger entry.
- Tool usage counters and breakdown tracking on each run.
- Stats snapshot reconstruction and incremental projection under `.harnessiq/stats/`.
- New `harnessiq stats ...` CLI family, including rebuild and export.

Blast radius:

- Moderate in the runtime, because all terminal runs emit ledger metadata.
- Moderate in CLI parsing, because a new top-level command is added.
- Low in providers, because model/provider metadata extraction can be reused and actual token reporting stays nullable for now.
- Moderate in tests, because new invariants affect both runtime and CLI behavior.

### 1c: Assumption & Risk Inventory

1. Assumption: the implementation should cover the design doc’s usable Phase 1 and Phase 2 surface now, while leaving actual token ingestion nullable until adapters expose usage.
   Why this matters: the doc stages work, but the user asked to implement the design doc rather than just Phase 1 MVP. The codebase currently lacks actual token telemetry in provider adapters, so “full surface” can be implemented only with nullable actual-token fields.

2. Assumption: `session_id` should be runtime-owned and auto-carried by looking up the most recent resumable ledger entry for the same `instance_id` when no explicit session is supplied.
   Why this matters: the open question in the design doc is real, but the existing codebase already has resume flows outside the ledger layer. If the implementation requires explicit caller wiring everywhere, direct Python callers and custom loops will diverge. Auto-carry is the only way to keep session continuity uniform across CLI and direct SDK usage without a second write path.

3. Risk: the current default ledger path is home-dir based, while the design doc describes repo-local `.harnessiq/`.
   Impact: if stats snapshots are written under repo root but the ledger lives elsewhere by default, the projector can drift from the ledger it is supposed to reflect. The implementation must derive stats paths from the resolved ledger location, not a hard-coded repo-root assumption.

4. Risk: tool counters do not exist today and must be accumulated during execution.
   Impact: transcript inspection after the fact is possible but fragile and needlessly expensive. The safer implementation is to add explicit counters on the agent instance and update them in the shared tool-execution path; custom loops must use the same shared helpers so they inherit this automatically.

5. Risk: `LeadsAgent` and `InstagramKeywordDiscoveryAgent` already persist their own run-state files and reuse their own logical run IDs for resume.
   Impact: the new `session_id` must not conflict with these native run-state concepts. The ledger `run_id` remains execution-scoped; the native run-state files should continue to use their existing identifiers unless explicitly tied to session continuity.

6. Risk: projector writes must be atomic and non-fatal.
   Impact: a bug in stats code must not block agent completion. The implementation must keep projector invocation below the sink-failure boundary and log failures instead of surfacing them.

7. Risk: there is no existing table-rendering helper in the CLI surface.
   Impact: the design doc shows box-drawing output for `stats summary`, but current CLI commands mostly emit JSON or plain printed text. A minimal, deterministic text table implementation may be needed unless tests accept a simpler formatted summary.

8. Risk: existing platform run snapshots do not store ledger `run_id` or `session_id`.
   Impact: if future resume logic wants exact session targeting rather than “latest resumable for instance,” the current snapshot schema is insufficient. For this implementation, ledger lookup by `instance_id` plus terminal status is the least invasive path.

9. Risk: malformed historical ledger entries are possible because `metadata["stats"]` is net-new.
   Impact: rebuild must skip legacy entries gracefully and report skipped counts, and summary commands must tolerate absent snapshot files by rebuilding or returning empty summaries.

Phase 1 complete.
