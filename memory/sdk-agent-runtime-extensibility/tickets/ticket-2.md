Title: Standardize agent tool injection and shared runtime helpers

Intent:
Make the SDK's tool and memory-oriented customization story coherent across the base runtime and concrete harnesses so users can inject custom tools without learning harness-specific quirks.

Scope:
- Add shared public helpers for tool composition and durable JSON parameter-section rendering.
- Replace duplicated private helper logic where it materially improves consistency.
- Add a consistent additive `tools=` hook to concrete agents that still lack one.
- Fix any adjacent base-runtime helper gap surfaced by the refactor.
- Do not redesign individual memory-store schemas.

Relevant Files:
- `harnessiq/tools/registry.py`: add public tool-composition helper(s).
- `harnessiq/tools/__init__.py`: export the new helper(s).
- `harnessiq/shared/agents.py`: add reusable parameter-section helper(s).
- `harnessiq/agents/base/agent.py`: fix or expose any supporting runtime helper needed by the new public surface.
- `harnessiq/agents/instagram/agent.py`: add additive custom tool injection and use shared helpers where appropriate.
- `harnessiq/agents/linkedin/agent.py`: add additive custom tool injection and use shared helpers where appropriate.
- `harnessiq/agents/prospecting/agent.py`: add additive custom tool injection and use shared helpers where appropriate.
- `harnessiq/agents/exa_outreach/agent.py`: add additive custom tool injection and use shared helpers where appropriate.
- `harnessiq/agents/email/agent.py`: align email harness customization naming/surface with the broader SDK.
- Agent/package export files and targeted tests as needed.

Approach:
Create one shared merge helper for `RegisteredTool` collections and one shared helper for building JSON-backed `AgentParameterSection` objects. Use those helpers in the concrete agents while preserving specialized args such as `browser_tools=`. Add additive `tools=` hooks so users can inject custom tools across the agent catalog in a consistent way.

Assumptions:
- `tools=` should be additive to the harness default tool surface, not a total replacement.
- Existing specialized args (`browser_tools`, `email_tools`) remain supported for backward compatibility.

Acceptance Criteria:
- [ ] A public helper exists for composing ordered `RegisteredTool` collections without per-agent private merge code.
- [ ] A public helper exists for building JSON parameter sections for durable memory/state blocks.
- [ ] Concrete agents that previously lacked a generic `tools=` surface now accept additive custom tools.
- [ ] Existing defaults and specialized tool args keep working.
- [ ] Targeted tests verify custom tool injection for affected agents and the new helper behavior.

Verification Steps:
- Run `pytest tests/test_agents_base.py`.
- Run targeted agent tests for changed harness constructors.
- Run targeted tool-runtime tests for the new helper exports.

Dependencies:
- Ticket 1 independent.

Drift Guard:
This ticket must not replace the existing toolset SDK, alter provider-tool behavior, or introduce a new generic memory framework. It is about ergonomic composition and consistent injection, not a redesign of how agents think or persist state.
