## Dynamic Tool Selection Clarifications

### Questions

1. Initial metadata coverage
   - Ambiguity: the design introduces `ToolProfile`-style retrieval metadata, but the repository has a large built-in and provider-backed tool surface.
   - Why it matters: this decides whether V1 is a narrowly scoped, production-quality opt-in for one or two agents, or a repo-wide metadata retrofit touching a much larger blast radius.
   - Options:
     - A. V1 should fully cover the entire current tool catalog before any agent can opt in.
     - B. V1 should cover only the first opt-in agents and the tool families they actually use, leaving the rest on the static path until later.
     - C. V1 should provide generic fallback profiles for uncovered tools and allow selective manual enrichment over time.

2. Embedding backend strategy
   - Ambiguity: the design mentions a lightweight embedding model, but the current package dependency surface is intentionally small.
   - Why it matters: this determines packaging, implementation complexity, and whether V1 can ship as a self-contained SDK feature or only as an interface with a pluggable backend.
   - Options:
     - A. Add a local default dependency such as `sentence-transformers` and ship a working default selector in V1.
     - B. Keep V1 dependency-light and require an injected embedding backend; ship the interface and default selection flow without bundling a local model.
     - C. Use a provider-backed embedding API as the default backend if credentials are available, with injection still supported.

3. CLI scope for V1
   - Ambiguity: the runtime can support this feature purely through Python construction, or through CLI configuration as well.
   - Why it matters: adding CLI support touches shared parsing, persisted runtime config flows, and multiple command modules, which is a significantly larger change than Python-only support.
   - Options:
     - A. V1 must include CLI flags and persisted runtime config support for dynamic tool selection.
     - B. V1 should be Python-construction only; CLI support can come in a follow-up ticket.
     - C. V1 should add shared CLI/runtime-config support, but only expose it on the first opt-in harnesses rather than every agent command surface.

4. First opt-in agents
   - Ambiguity: the design is intentionally opt-in, but it does not yet name which agents should adopt the feature first.
   - Why it matters: prompt alignment, metadata authoring, and verification scope all depend on the first concrete adopters.
   - Options:
     - A. Start with `LeadsAgent` only.
     - B. Start with `LeadsAgent` and provider-backed base agents.
     - C. Implement the feature end-to-end but leave every agent disabled by default with no first adopter wired in yet.

5. GitHub workflow artifact lifecycle
   - Ambiguity: the skill workflow creates temporary implementation issues and deletes them after PR creation, but some teams prefer keeping those issues as historical artifacts.
   - Why it matters: this affects whether I follow the skill literally or adapt the workflow to your repo preferences.
   - Options:
     - A. Follow the skill literally: create implementation issues, create PRs, then delete the temporary issues.
     - B. Create the issues and PRs, but keep the issues open or closed rather than deleting them.
     - C. Create only local ticket documents in `memory/dynamic-tool-selection/tickets/` and skip GitHub issue creation.

### Responses

1. Initial metadata coverage
   - Response: build the feature on top of the existing tool catalog and do not change the catalog model itself.
   - Implementation implication: introduce a separate retrieval-profile layer that maps onto the current catalog and registered tools rather than extending or mutating `ToolEntry`.

2. Embedding backend strategy
   - Response: default to a provider-backed embedding API and add the embedding surface into the providers layer.
   - Implementation implication: the dynamic selector should depend on an embedding interface, and the default backend should be implemented through a provider/integration path rather than a bundled local embedding dependency.

3. CLI scope for V1
   - Response: CLI support should allow users to enable dynamic tooling and specify candidate tools using strings for existing tools; support for custom tools with custom functions should remain available through the Python API surface.
   - Implementation implication: CLI work should focus on enablement and catalog-backed tool-key selection. Custom callable tools are a Python-construction concern, not a shell-supplied function concern.

4. First opt-in agents
   - Response: build the feature end to end but leave all agents on the static path by default.
   - Implementation implication: wire the runtime, docs, and scaffolding completely, but do not enable dynamic selection by default for any built-in harness.

5. GitHub workflow artifact lifecycle
   - Response: proceed with the GitHub-skill workflow for tickets and implementation.
   - Implementation implication: I will create GitHub issues for the ticket suite and follow the skill workflow. Because you did not request preserving temporary issues, I will follow the skill's default lifecycle unless repository policy blocks deletion.

### Follow-on Implications

- `ToolProfile` should be a parallel model layered over the existing catalog, not a change to `ToolEntry`.
- The concrete selector should index a resolved candidate pool built from:
  - catalog-backed existing tools selected by string keys
  - additive custom `RegisteredTool` objects provided through Python construction
- The provider layer needs a new embedding-capable seam before the selector can ship with a default backend.
- Agent constructors and runtime config should expose opt-in scaffolding, but built-in harness defaults must remain static.
