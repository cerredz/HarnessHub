Title: Establish shared DTO package and typed agent instance boundaries

Intent:
Create the `harnessiq/shared/dtos/` package and use it to replace the raw dict-based agent instance boundary with explicit serializable DTOs. This foundation gives the rest of the refactor a common pattern for DTO ownership, serialization, and public exports.

Issue URL:
https://github.com/cerredz/HarnessHub/issues/326

Scope:
- Create the shared DTO subpackage and the first common agent-boundary DTO modules.
- Convert the base agent instance payload contract from raw `dict[str, Any]` to explicit DTO types.
- Update `AgentInstanceRecord` / `AgentInstanceStore` persistence so instance payloads are serialized from DTOs rather than passed around as raw mappings.
- Preserve compatibility when reading already-persisted JSON registry data where reasonable.
- Do not yet convert the concrete agent families or the CLI/provider layers to DTO-first APIs; this ticket only establishes the shared package and the core instance boundary they depend on.

Relevant Files:
- `harnessiq/shared/dtos/__init__.py` - new shared DTO package surface.
- `harnessiq/shared/dtos/base.py` - common DTO serialization helpers or base protocols for JSON-safe dataclasses.
- `harnessiq/shared/dtos/agents.py` - common agent-boundary DTOs for instance payloads and related shared envelopes.
- `harnessiq/shared/__init__.py` - export the shared DTO package as part of the public shared surface.
- `harnessiq/agents/base/agent.py` - change `build_instance_payload()` and related base-agent instance plumbing to use DTOs.
- `harnessiq/utils/agent_instances.py` - persist typed DTO payloads instead of raw mappings and support serialization/deserialization.
- `tests/test_agent_instances.py` - cover DTO serialization, persistence, and backwards-compatible load behavior.
- `tests/test_sdk_package.py` - lock the DTO package into the packaging/public-surface expectations where appropriate.

Approach:
Introduce a small shared DTO framework under `harnessiq/shared/dtos/` that is intentionally boring: frozen dataclasses with explicit `to_dict()` / `from_dict()` style conversions for persistence boundaries. Use that framework to make the base agent instance contract explicit. The `BaseAgent` / `AgentInstanceStore` seam is the highest-value first slice because every agent already depends on it, and it is currently the main place where agent-specific raw dict payloads are normalized and persisted. The ticket should keep the JSON file format stable enough to read old persisted data, but the in-memory contract should become DTO-first immediately.

Assumptions:
- The DTO package should be importable from `harnessiq.shared.dtos`.
- Public contract change is acceptable; `build_instance_payload()` can become DTO-first rather than dict-first.
- Existing persisted instance registry files may exist locally and should not become unreadable because of this refactor.

Acceptance Criteria:
- [ ] `harnessiq/shared/dtos/` exists with an explicit package surface and agent DTO module.
- [ ] The base agent instance payload contract is expressed as shared DTO types rather than raw dicts.
- [ ] `AgentInstanceStore` serializes and deserializes the DTO-based payload boundary correctly.
- [ ] Existing JSON-backed agent instance registry files remain loadable or fail with a deliberate, documented migration error rather than a silent type break.
- [ ] Packaging and unit tests cover the new DTO package and instance persistence behavior.

Verification Steps:
- Run the targeted agent-instance and SDK packaging tests covering DTO persistence and exports.
- Run any relevant lint/static checks available for the changed files.
- Run the focused unit suite around base agent / instance store behavior.
- Smoke-check instance creation through at least one concrete agent that inherits from `BaseAgent`.

Dependencies:
- None.

Drift Guard:
This ticket must not redesign concrete agent payload shapes, CLI result envelopes, or provider request models. Its job is to establish the DTO package and convert the single shared agent-instance seam that every later ticket will build on.
