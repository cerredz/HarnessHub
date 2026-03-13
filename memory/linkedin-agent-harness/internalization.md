### 1a: Structural Survey

Repository shape:

- `src/` contains the production Python package. Today it is organized around two core concerns:
- `src/tools/` defines canonical tool metadata (`ToolDefinition`), runtime bindings (`RegisteredTool`), and deterministic execution/validation via `ToolRegistry`.
- `src/providers/` contains provider-agnostic message normalization plus provider-specific request/client helpers for OpenAI, Grok, Anthropic, and Gemini.
- `tests/` contains `unittest` coverage for tool registry behavior, provider request builders, provider clients, and LangSmith tracing wrappers.
- `artifacts/file_index.md` is the maintained repository architecture artifact and should be updated when the top-level structural layout changes.
- `memory/` stores planning, ticket, critique, and verification artifacts from prior tasks.

Technology and execution model:

- Plain Python package layout with standard-library testing via `python -m unittest`.
- The codebase uses dataclasses, protocols, and small pure helper functions rather than framework-heavy abstractions.
- There is no visible formatter, lint, or static type checker configuration at the repository root.
- There is no existing agent runtime, conversation loop, memory-store abstraction, or model response normalization layer.

Current architecture conventions:

- Public API surfaces are curated through package-level `__init__.py` exports.
- Shared reusable types live under `src/shared/`.
- Runtime tools are represented canonically as `ToolDefinition` metadata plus executable `RegisteredTool` handlers.
- Tool execution validation is intentionally lightweight and deterministic.
- Provider helper modules are designed to be testable without live network calls by injecting fake executors.

Relevant existing capabilities:

- `src/providers/langsmith.py` already exposes tracing helpers intended for custom agent runs, model calls, and tool calls.
- `src/providers/openai/client.py` and `src/providers/grok/client.py` provide thin clients, but there is still no provider-independent model execution contract for a higher-level agent harness.
- The tool layer is the closest existing primitive to what an agent runtime would need for local memory/control tools.

Notable gaps and inconsistencies:

- The repository name and prior LangSmith work imply future agent support, but there is no `src/agents/` package yet.
- Provider-facing message types currently cover only `system`, `user`, and `assistant` roles; a future agent loop with tool calls/results cannot directly reuse them as-is without a higher-level transcript abstraction.
- The repository already has tracing utilities for agents before it has an agent framework, so a new agent layer should align with those helpers instead of bypassing them.

### 1b: Task Cross-Reference

User request mapping:

- "create the agent class in our source folder and a base agent class" maps to a new `src/agents/` package with reusable runtime abstractions rather than extending the existing provider or tool packages.
- "implement our harness around the LinkedIn agent" maps to a generic loop that can:
- assemble a system prompt and parameter block,
- maintain a rolling transcript of assistant/tool activity,
- execute tool calls,
- monitor context budget,
- clear and re-inject persistent parameters when the budget is exhausted,
- pause cleanly for human intervention,
- continue running until explicitly stopped or paused.
- "define a custom `LinkedInJobApplierAgent` with the custom harness described in the conversation" maps to a LinkedIn-specific subclass/configuration layer that owns:
- memory file layout under a configurable `memory_path`,
- system prompt assembly using identity, goal, input description, tool array, and behavioral rules,
- LinkedIn-specific durable state files (`job_preferences.md`, `user_profile.md`, `agent_identity.md`, `applied_jobs.jsonl`, `action_log.jsonl`),
- LinkedIn-specific tool definitions and harness-provided memory/control tools.

Concrete code locations likely affected:

- `src/agents/__init__.py`: export the new public agent runtime surface.
- `src/agents/base.py`: define core agent protocols, data models, loop orchestration, transcript reset behavior, and a provider-agnostic model interface.
- `src/agents/linkedin.py`: define LinkedIn memory management, the LinkedIn tool catalog, and the concrete `LinkedInJobApplierAgent`.
- `tests/`: add agent-focused tests covering runtime behavior and LinkedIn-specific defaults.
- `artifacts/file_index.md`: update the source layout to include the new `src/agents/` package once added.

Relevant existing code that should be preserved or reused:

- Reuse `ToolDefinition`, `RegisteredTool`, `ToolCall`, `ToolResult`, and `ToolRegistry` from `src/shared.tools` / `src.tools`.
- Preserve the codebase convention of small explicit dataclasses and injected runtime collaborators instead of hard-coding external services.
- Keep the agent layer provider-agnostic so it can sit above `src/providers/` rather than entangling itself with a specific model client.
- Leave provider request builders and clients unchanged unless a small compatibility export becomes necessary.

Blast radius:

- Mostly additive. The primary risk is introducing an agent runtime that conflicts with the existing tool abstractions or future provider integrations.
- Tests will expand, but current provider/tool behavior should remain untouched.
- The new package becomes a new top-level production concern in the repository and therefore needs a clean, stable public surface.

### 1c: Assumption & Risk Inventory

Implementation assumptions:

- The requested deliverable is a reusable local agent harness plus a concrete LinkedIn specialization, not a fully live LinkedIn automation stack.
- The harness should define how a model is called through an abstract interface, but it should not implement provider-specific response parsing or bind directly to one provider client in this task.
- Browser interaction tools are part of the LinkedIn tool array, but actual Playwright/MCP execution can remain injectable via registered tool handlers supplied at runtime.
- Harness-owned memory/control tools should be implemented locally because they are explicitly part of the spec and do not require external infrastructure.
- Context reset can be implemented with deterministic token estimation rather than provider-exact token counting, because no tokenizer dependency exists in the repository.

Risks and edge cases:

- The LinkedIn spec mixes "append-only" `applied_jobs.jsonl` semantics with an `update_job_status` tool. If implemented naively by in-place mutation, it would violate the append-only durability claim.
- A provider-agnostic agent loop still needs a concrete response shape from the model. If the abstraction is too narrow, future provider adapters will be awkward; if too broad, the initial implementation will be over-engineered.
- Browser tool support is only useful if the caller can inject executable handlers. The harness should make that dependency explicit rather than pretending browser automation is implemented locally.
- A fully unbounded `while True` loop is hard to test safely. The runtime needs a guard or max-iteration option for deterministic verification without undermining the keep-alive design.
- The existing provider message types do not model tool-call/result turns, so the agent layer needs its own transcript types instead of forcing a bad fit.

Phase 1 complete
