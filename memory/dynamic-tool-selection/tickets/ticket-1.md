Title: Add tool-selection interfaces and provider-backed embedding support

Issue URL: https://github.com/cerredz/HarnessHub/issues/387
PR URL: https://github.com/cerredz/HarnessHub/pull/391

Intent:
Establish the public contracts and provider-layer primitives required for dynamic tool selection without changing existing agent behavior. This ticket creates the abstraction seams that later tickets depend on.

Scope:
- Add a public `DynamicToolSelector` interface and embedding-backend interface under `harnessiq/interfaces/`.
- Add shared immutable tool-selection dataclasses under `harnessiq/shared/`.
- Add a provider-backed embedding client surface in the providers layer and a default integration path for obtaining embeddings.
- Keep all runtime behavior unchanged; no agent should select tools dynamically after this ticket alone.

Scope Exclusions:
- No selector algorithm implementation.
- No `BaseAgent` runtime integration.
- No CLI flags.
- No prompt rendering changes.

Relevant Files:
- `harnessiq/interfaces/tool_selection.py` — new protocol definitions for dynamic tool selection and embeddings.
- `harnessiq/interfaces/__init__.py` — re-export the new interface contracts.
- `harnessiq/shared/tool_selection.py` — new immutable dataclasses for `ToolProfile`, `ToolSelectionConfig`, and `ToolSelectionResult`.
- `harnessiq/shared/agents.py` — add `tool_selection` runtime config field and merge support.
- `harnessiq/providers/` — add the provider-backed embedding client/request surface.
- `harnessiq/integrations/` — add runtime glue for the default embedding backend if needed.
- `tests/test_interfaces.py` — verify the new public contracts.
- new targeted tests under `tests/` — verify shared dataclass validation/merge behavior and provider embedding surface.

Approach:
Follow existing repo boundaries strictly:
- protocols in `interfaces/`
- immutable runtime models in `shared/`
- provider transport in `providers/`
- integration glue in `integrations/`

The provider embedding path should be additive and interface-driven so later selector logic can depend on an embedding backend without caring how vectors are produced.

Assumptions:
- The existing tool catalog must remain unchanged.
- Provider-backed embeddings are the default backend strategy for V1.
- Dynamic selection stays disabled by default after the config field is added.

Acceptance Criteria:
- [ ] `harnessiq/interfaces` exports a public `DynamicToolSelector` contract.
- [ ] `harnessiq/interfaces` exports a public embedding backend contract.
- [ ] `ToolSelectionConfig`, `ToolProfile`, and `ToolSelectionResult` exist as shared immutable dataclasses.
- [ ] `AgentRuntimeConfig` can carry tool-selection configuration without changing current default behavior.
- [ ] A provider-backed embedding surface exists in the providers/integrations layer and is test-covered.
- [ ] Existing tests unrelated to dynamic selection continue to pass.

Verification Steps:
- Static analysis on changed files.
- Type-check changed files or, if no checker is configured, ensure all new code is fully annotated.
- Run targeted unit tests for interfaces, shared models, and embedding provider surface.
- Run adjacent runtime/config tests that cover `AgentRuntimeConfig`.
- Perform a smoke import check that the new public interfaces are available from `harnessiq.interfaces`.

Dependencies:
- None.

Drift Guard:
This ticket must not implement selection logic, prompt changes, CLI changes, or agent behavior changes. Its only job is to create the public and provider-layer primitives the rest of the feature depends on.
