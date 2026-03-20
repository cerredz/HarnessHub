### Clarifying Questions

1. Sink architecture: should I preserve the repo’s current post-run sink model, or should I extend the framework to support an in-loop `POST_TO_SINK` tool for per-lead delivery?
- Ambiguity: the design doc requires `POST_TO_SINK` during execution, but `artifacts/file_index.md` and the existing ledger implementation explicitly prohibit sinks from participating in the execution loop.
- Why this matters: this is the biggest architectural fork in the task. One path is a repo-native harness; the other is a framework change affecting sink semantics and possibly docs/tests across the SDK.
- Options:
  - Preferred repo-native path: keep current ledger/output-sink semantics and record qualified leads in durable memory + ledger outputs for post-run export.
  - Design-doc-literal path: add a new in-loop `POST_TO_SINK` tool and intentionally expand framework behavior.
  - Hybrid path: keep ledger sinks post-run, but add a separate non-ledger “lead destination” abstraction used only by the prospecting agent.

2. Memory contract: do you want me to implement generic `READ_AGENT_MEMORY` / `WRITE_AGENT_MEMORY` tools, or should I follow existing agent patterns and keep prospecting memory in a dedicated `ProspectingMemoryStore` that the agent reads/writes directly?
- Ambiguity: the design doc treats memory read/write as explicit tools, while every current agent uses direct file-backed stores plus parameter refresh on reset.
- Why this matters: adding generic memory tools is a shared-runtime change; using a domain store fits current conventions and is much smaller blast radius.
- Options:
  - Preferred repo-native path: dedicated `ProspectingMemoryStore` only.
  - Framework-expansion path: add generic memory tools and wire the agent to use them.
  - Hybrid path: use `ProspectingMemoryStore` now, but structure it so generic memory tools can wrap it later.

3. Google Maps browser surface: should I build a real Playwright-backed Google Maps integration in this task, or just the harness/tool contracts plus stub/injectable browser tools?
- Ambiguity: the design doc assumes Google Maps navigation and extraction are runnable, but the repo currently has no Maps browser integration and no generic browser tool set beyond LinkedIn’s agent-local pattern.
- Why this matters: a real Playwright implementation is materially larger and riskier than adding the harness surface alone.
- Options:
  - Full implementation: add a Playwright-backed Google Maps browser integration and wire it into `prospecting run`.
  - Harness-first: add agent, memory, CLI, shared models, and deterministic tool scaffolding, but leave browser tools injectable/stubbed for a later integration pass.
  - Middle path: add agent-local stub definitions now and a minimal integration module with only the fields required for an MVP.

4. Sub-LLM tools: for `EVALUATE_COMPANY` and `SEARCH_OR_SUMMARIZE`, should these be reusable shared tools under `harnessiq/tools/`, or should they be prospecting-agent internal tools/helpers for the first implementation?
- Ambiguity: the design doc positions them as reusable registry tools, but the current codebase often keeps domain-specific deterministic behavior inside the harness unless it is clearly reusable today.
- Why this matters: shared-tool placement changes public SDK surface, constants, exports, docs, and tests. Internal helpers keep scope tighter.
- Options:
  - Public shared tools now, matching the design doc.
  - Prospecting-internal tools/helpers now, generalize later if another agent needs them.
  - Shared `SEARCH_OR_SUMMARIZE`, internal `EVALUATE_COMPANY`, since search summarization looks more cross-agent reusable.

### Responses

1. Sink architecture
- Decision: keep the repo’s current sink behavior.
- Additional requirement: this agent should still default to exporting qualified leads through the ledger/output-sink path when the user has configured sinks, rather than treating export as a niche optional behavior.
- Implementation implication: do not add in-loop `POST_TO_SINK`. Instead, make `qualified_leads` a first-class ledger output for this agent so configured sinks receive those records by default at run completion.

2. Memory architecture
- Decision: keep current agent conventions.
- Implementation implication: build a dedicated `ProspectingMemoryStore` and persist deterministic state there; do not add generic `READ_AGENT_MEMORY` / `WRITE_AGENT_MEMORY` tools.

3. Browser/Maps execution scope
- Decision: full Playwright integration.
- Additional requirement: prefer toolset-backed browser interactions, and add public shared tools to the toolset if needed.
- Implementation implication: add a real Playwright-backed Google Maps/browser integration plus the tool definitions/factories required to drive it from the agent and CLI.

4. Shared tool placement
- Decision: `EVALUATE_COMPANY` and `SEARCH_OR_SUMMARIZE` should be public shared tools.
- Implementation implication: define them in the shared/public tool layer, export them from `harnessiq.tools`, and import them explicitly when wiring the prospecting agent.

### Follow-On Implications

- The design doc’s sink intent will be adapted into repo-native ledger outputs rather than a new in-loop sink tool.
- The design doc’s explicit memory tools will be adapted into a durable memory store plus parameter-section refresh on resets.
- A new public browser tool family is now justified, because the current repo does not expose a generic Playwright-backed browser surface suitable for Google Maps.
- The implementation should make `qualified_leads` easy for output sinks to consume, likely by emitting a structured list in `build_ledger_outputs()` and keeping stable record schemas in shared types.
