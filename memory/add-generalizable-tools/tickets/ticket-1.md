Title: Add a general-purpose built-in tool suite for text, records, and human escalation
Intent: Expand HarnessHub's default tool layer with a compact set of broadly reusable tools that future agents can rely on for common text cleanup, record manipulation, and structured pause behavior.
Scope:
- Add 10 new provider-agnostic built-in tools to the repository.
- Implement the tools as pure helpers plus a tool factory module under `src/tools/`.
- Expose the new tool keys and public exports through the shared/tool package surfaces.
- Add tests that cover helper behavior and built-in registry integration.
- Update the repository file index to reflect the broader tool-layer responsibility.
- Do not add provider-specific tool payload builders, external service integrations, or domain-specific agent logic.
Relevant Files:
- `memory/add-generalizable-tools/internalization.md`: Phase 1 internalization for this task.
- `memory/add-generalizable-tools/clarifications.md`: record that no blocking clarifications were needed.
- `memory/add-generalizable-tools/brainstorm.md`: capture the selected 10-tool set and rationale.
- `src/shared/tools.py`: add canonical keys for the new tools.
- `src/tools/general_purpose.py`: implement the new helper functions and registered tools.
- `src/tools/builtin.py`: include the new tool family in the built-in registry.
- `src/tools/__init__.py`: export the new public helpers and tool-factory surface.
- `tests/test_tools.py`: update registry expectations and built-in execution checks.
- `tests/test_general_tools.py`: add focused behavior coverage for the new tool family.
- `artifacts/file_index.md`: update the architectural description of the tool layer.
Approach: Follow the existing `context_compaction` pattern: define small pure helpers with explicit type checks, wrap them in `RegisteredTool` definitions through a factory, then append that family into `BUILTIN_TOOLS`. Choose orthogonal operations rather than a complex mini-language so agents can compose several simple tools predictably. Reuse `AgentPauseSignal` for the escalation tool so the base runtime can already honor the result without further changes.
Assumptions:
- The built-in registry is the right default home for highly reusable cross-agent tools.
- Deterministic list/text transformations provide more immediate value in this repo than networked integrations.
- First-seen ordering should be preserved whenever tools reduce or deduplicate record lists.
Acceptance Criteria:
- [ ] Ten new built-in tools exist with stable canonical keys and JSON-friendly metadata.
- [ ] The tools cover text cleanup, record shaping/filtering, aggregation, and human-pause control flow.
- [ ] `create_builtin_registry()` exposes the new tools in deterministic order.
- [ ] The pause-control tool returns `AgentPauseSignal` and is compatible with the existing base agent loop.
- [ ] Unit tests cover the new helper behavior, edge cases, and registry execution path.
- [ ] The file index reflects the expanded role of the tool layer.
Verification Steps:
- Run `python -m unittest tests.test_general_tools tests.test_tools tests.test_agents_base`.
- Run the full suite with `python -m unittest`.
- Inspect the built-in registry keys and confirm the new ordering is stable and intentional.
Dependencies: None.
Drift Guard: This ticket must not introduce domain-specific business logic, external API dependencies, or a generic query DSL. The goal is a small, obvious, reusable tool suite that strengthens the current runtime scaffold.
