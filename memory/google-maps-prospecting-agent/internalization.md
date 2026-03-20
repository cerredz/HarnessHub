### 1a: Structural Survey

Repository shape:
- `harnessiq/` is the shipped SDK package.
- `docs/` contains lightweight product/runtime docs.
- `artifacts/file_index.md` defines architectural expectations and contribution standards.
- `tests/` uses `unittest` and `pytest` for package, runtime, CLI, and agent coverage.

Core runtime architecture:
- [`harnessiq/agents/base/agent.py`](C:\Users\Michael Cerreto\HarnessHub\harnessiq\agents\base\agent.py) defines `BaseAgent`, the shared loop runtime.
- `BaseAgent` owns system-prompt injection, parameter-section refresh, transcript accumulation, tool execution, reset detection, agent instance registration, and post-run ledger emission.
- Reset behavior is transcript reset only. There is no built-in persisted memory tool surface. Durable state today is carried by agent-owned files/stores that `load_parameter_sections()` rereads after resets.
- `AgentRuntimeConfig` in [`harnessiq/shared/agents.py`](C:\Users\Michael Cerreto\HarnessHub\harnessiq\shared\agents.py) currently supports `max_tokens`, `reset_threshold`, `output_sinks`, and `include_default_output_sink`. It does not support `max_cycles`, `storage_provider`, or `storage_config`.

Concrete agent conventions:
- Each agent has a focused harness class under `harnessiq/agents/<agent>/agent.py`.
- Shared constants, typed records, runtime-parameter normalization, and durable file memory stores live under `harnessiq/shared/<domain>.py`.
- Agents generally implement:
  - `prepare()`
  - `build_system_prompt()`
  - `load_parameter_sections()`
  - `build_ledger_outputs()/tags()/metadata()`
  - internal deterministic tools via `RegisteredTool`
  - optional `from_memory()` constructor for CLI rehydration
- Existing agents:
  - LinkedIn: browser-driven harness with internal durable-memory tools and optional Google Drive sync.
  - Instagram: deterministic search backend with one internal search tool and JSON memory files.
  - ExaOutreach: provider-backed search/email tools plus deterministic run logging.
  - Knowt: prompt-file-driven content pipeline backed by memory files and tool factories.

Tool architecture:
- Public tool metadata and constants live in [`harnessiq/shared/tools.py`](C:\Users\Michael Cerreto\HarnessHub\harnessiq\shared\tools.py).
- Runtime tool execution lives in [`harnessiq/tools/registry.py`](C:\Users\Michael Cerreto\HarnessHub\harnessiq\tools\registry.py) and `harnessiq/tools/*`.
- Built-in tools are reusable registries/factories, not agent-specific prompt glue.
- Provider-backed tools follow a single-request-tool pattern by provider.
- Agent-specific deterministic tools currently live inside the agent harness class rather than under `harnessiq/tools/`.

CLI architecture:
- Top-level parser is in [`harnessiq/cli/main.py`](C:\Users\Michael Cerreto\HarnessHub\harnessiq\cli\main.py).
- Each agent with CLI support gets a dedicated subpackage under `harnessiq/cli/<agent>/commands.py`.
- Existing CLI flows consistently expose `prepare`, `configure`, `show`, and `run`.
- CLI config is persisted into each agent’s memory folder; `run` reloads from memory and optionally injects ledger sinks via runtime config.

Ledger and sink architecture:
- [`harnessiq/utils/ledger.py`](C:\Users\Michael Cerreto\HarnessHub\harnessiq\utils\ledger.py) implements the framework-wide audit ledger plus post-run output sinks.
- Output sinks are write-only post-run integrations attached via `AgentRuntimeConfig.output_sinks`.
- Current sink behavior is intentionally outside the model execution loop. The file index explicitly states sinks must never participate in execution, transcript mutation, or `AgentRunResult`.

Instance and memory conventions:
- [`harnessiq/utils/agent_instances.py`](C:\Users\Michael Cerreto\HarnessHub\harnessiq\utils\agent_instances.py) persists stable SDK-level instance records under `memory/agent_instances.json`.
- Concrete agents fingerprint meaningful payload and memory inputs to derive stable/reused instance ids.
- Durable memory is file-backed, agent-owned, and read into parameter sections at the start of each context window.

Testing conventions:
- Agent tests use fake models that record `AgentModelRequest`.
- CLI tests exercise actual parser/main entrypoints and inspect JSON stdout.
- SDK/package tests assert agent exports from `harnessiq.agents` and command registration from `harnessiq.cli`.
- Sink and ledger tests focus on post-run behavior, not in-loop tool invocation.

Observed inconsistencies and important repo realities:
- `README.md`, `docs/agent-runtime.md`, and `artifacts/file_index.md` are partially ahead of or divergent from implementation detail. The code is the source of truth.
- The design doc’s runtime fields (`storage_provider`, `storage_config`, `max_cycles` inside runtime config) do not exist in current code.
- The design doc’s in-loop `POST_TO_SINK` conflicts directly with the file index and ledger implementation, which make sinks post-run concerns.
- The design doc assumes explicit `READ_AGENT_MEMORY` / `WRITE_AGENT_MEMORY` tools, but current agents persist memory directly in internal stores and rely on parameter refresh after reset.
- There is no existing generic browser tool surface for Google Maps. Only the LinkedIn agent defines browser-tool stubs plus a Playwright integration.

### 1b: Task Cross-Reference

User goal:
- Add a new “google maps prospecting agent” harness that fits the repo’s agent architecture, shared definitions, CLI ergonomics, SDK exports, audit logging, memory model, and file index standards.

Codebase surfaces directly touched by this request:

Agent harness:
- Net-new likely location: `harnessiq/agents/prospecting/agent.py`
- Companion export module: `harnessiq/agents/prospecting/__init__.py`
- SDK export updates: [`harnessiq/agents/__init__.py`](C:\Users\Michael Cerreto\HarnessHub\harnessiq\agents\__init__.py)
- Package smoke coverage: [`tests/test_sdk_package.py`](C:\Users\Michael Cerreto\HarnessHub\tests\test_sdk_package.py)

Shared types/config/defaults/memory:
- Net-new likely location: `harnessiq/shared/prospecting.py`
- This should hold:
  - default prompts/constants
  - typed config dataclasses
  - memory schema records
  - runtime/custom parameter normalization
  - memory-store implementation
  - sink-record/evaluation/search record models
- This follows the repo pattern established by `shared/linkedin.py`, `shared/instagram.py`, and `shared/exa_outreach.py`.

Prompt assets:
- Net-new likely location: `harnessiq/agents/prospecting/prompts/master_prompt.md`
- Existing prompt-file pattern is used by Instagram, Knowt, and ExaOutreach.

Tooling:
- The design doc asks for three reusable tools:
  - `EVALUATE_COMPANY`
  - `SEARCH_OR_SUMMARIZE`
  - `POST_TO_SINK`
- Candidate locations per design doc:
  - `harnessiq/tools/eval/evaluate_company.py`
  - `harnessiq/tools/search/search_or_summarize.py`
  - `harnessiq/tools/sink/post_to_sink.py`
- Required shared/public surfacing if built this way:
  - update [`harnessiq/shared/tools.py`](C:\Users\Michael Cerreto\HarnessHub\harnessiq\shared\tools.py) with public key constants
  - update [`harnessiq/tools/__init__.py`](C:\Users\Michael Cerreto\HarnessHub\harnessiq\tools\__init__.py)
- Important architecture mismatch:
  - `EVALUATE_COMPANY` and `SEARCH_OR_SUMMARIZE` fit the codebase’s deterministic tool model.
  - `POST_TO_SINK` does not fit the current repo’s sink contract unless we intentionally expand the architecture.
  - `READ_AGENT_MEMORY` / `WRITE_AGENT_MEMORY` do not exist as general tools and would be net-new architecture, not just a new harness.

Browser / Maps interaction:
- There is no existing Google Maps browser integration.
- If we follow the LinkedIn pattern, we would likely need either:
  - agent-local browser-tool definitions plus runtime-injected handlers, or
  - a new integration module under `harnessiq/integrations/` for Playwright-backed Google Maps tools.
- The design doc names generic browser tools (`BROWSER_NAVIGATE`, `BROWSER_EXTRACT_CONTENT`, `BROWSER_SCREENSHOT`) that do not exist in the current registry.

CLI:
- Net-new likely location: `harnessiq/cli/prospecting/commands.py`
- Must be registered in [`harnessiq/cli/main.py`](C:\Users\Michael Cerreto\HarnessHub\harnessiq\cli\main.py)
- Based on existing agent CLIs, expected commands would be:
  - `prepare`
  - `configure`
  - `show`
  - `run`
- The design doc’s example command uses `harnessiq prospecting configure`, which aligns with current CLI patterns.

Ledger / audit expectations:
- The user asked to “keep audits/use the ledger to save logs.”
- Existing code already emits one `LedgerEntry` per terminal run from `BaseAgent`.
- The correct repo-native implementation path is to expose run outputs, counts, and metadata through `build_ledger_outputs()/metadata()`, plus rely on configured output sinks for post-run exports.
- If per-lead sink posting is required during execution, that is a framework behavior change, not just a new agent addition.

Tests likely required:
- Net-new agent tests analogous to:
  - [`tests/test_instagram_agent.py`](C:\Users\Michael Cerreto\HarnessHub\tests\test_instagram_agent.py)
  - [`tests/test_linkedin_agent.py`](C:\Users\Michael Cerreto\HarnessHub\tests\test_linkedin_agent.py)
  - [`tests/test_exa_outreach_agent.py`](C:\Users\Michael Cerreto\HarnessHub\tests\test_exa_outreach_agent.py)
- Net-new CLI tests analogous to:
  - [`tests/test_instagram_cli.py`](C:\Users\Michael Cerreto\HarnessHub\tests\test_instagram_cli.py)
  - [`tests/test_linkedin_cli.py`](C:\Users\Michael Cerreto\HarnessHub\tests\test_linkedin_cli.py)
  - [`tests/test_ledger_cli.py`](C:\Users\Michael Cerreto\HarnessHub\tests\test_ledger_cli.py)
- Tool registry/export tests may need updates in:
  - [`tests/test_toolset_registry.py`](C:\Users\Michael Cerreto\HarnessHub\tests\test_toolset_registry.py)
  - [`tests/test_tools.py`](C:\Users\Michael Cerreto\HarnessHub\tests\test_tools.py)

File-index impact:
- New agent package under `harnessiq/agents/prospecting/`
- Potential new reusable tool folders under `harnessiq/tools/search/`, `harnessiq/tools/eval/`, and `harnessiq/tools/sink/`
- If these folders are added, [`artifacts/file_index.md`](C:\Users\Michael Cerreto\HarnessHub\artifacts\file_index.md) should be updated because the meaningful package structure changes.

### 1c: Assumption & Risk Inventory

1. Sink semantics are unresolved.
- The design doc requires in-loop `POST_TO_SINK`.
- The codebase standard says sinks are post-run only.
- Implementing the design doc literally would change framework architecture, not just add an agent.

2. Memory semantics are unresolved.
- The design doc requires `READ_AGENT_MEMORY` / `WRITE_AGENT_MEMORY` tools and a crash-safe consolidation protocol.
- Current runtime relies on agent-owned files plus parameter refresh; no general memory tools exist.
- Building new memory tools may be unnecessary duplication or may indicate a desired framework evolution.

3. Browser surface is unresolved.
- The repo has no Google Maps browser tool definitions or Playwright integration.
- The design doc’s named browser tools are not present in `docs/tools.md` or code.
- We need either new agent-local stub tools, a reusable browser abstraction, or a separate integration module.

4. Sub-LLM tooling contract is unresolved.
- `EVALUATE_COMPANY` and `SEARCH_OR_SUMMARIZE` both require deterministic internal LLM calls.
- The current tool layer does not define a generic “tool with injected AgentModel/model factory” pattern for arbitrary sub-calls.
- We need to decide whether these tools receive a model/client explicitly, are implemented as agent-internal helpers instead of shared tools, or rely on a provider-specific implementation.

5. Runtime config in the design doc does not match implementation.
- `storage_provider`, `storage_config`, and `max_cycles` inside runtime config do not exist.
- If those are required, the runtime abstraction needs extension.
- If not, the design doc needs adaptation to the actual SDK surface.

6. “Warm leads posted to the user’s configured sink” may be intended as durable CRM-style lead export, not merely ledger logging.
- The current ledger/output-sink system emits one run envelope after execution.
- That is materially different from per-qualified-lead delivery.
- We need a decision on whether lead export should ride the ledger, a new deterministic tool, or both.

7. Actual Google Maps extraction requirements are underspecified for the current repo.
- The design doc assumes deterministic extraction of rating, review count, review recency, owner responses, posts, Q&A, photos, chain indicators, maps rank, competitor review counts, and website quality.
- Some of these signals require significant browser-specific scraping or a website-inspection layer not present today.

8. The requested implementation scope may implicitly include framework changes wider than one agent.
- Reusable tools, sink semantics, memory tools, and browser abstractions would touch shared architecture.
- If the goal is a fast repo-native harness, a narrower first implementation is possible.
- If the goal is full literal adherence to the design doc, the change becomes multi-ticket framework work.

Phase 1 complete.
