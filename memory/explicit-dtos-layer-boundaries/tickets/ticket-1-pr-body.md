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


## Quality Pipeline Results
## Stage 1: Static Analysis

- No project linter or standalone static-analysis command is configured in `pyproject.toml`.
- Applied manual review to the changed files for import hygiene, serialization behavior, and package export consistency.
- Resolved one real import-cycle bug discovered during test collection by removing the DTO module's dependency on `harnessiq.utils.__init__` transitively through `agent_ids`.

## Stage 2: Type Checking

- No project type-checker configuration is present in `pyproject.toml`.
- Added explicit type annotations to the new DTO package and updated the base agent / instance-store boundary signatures to use `AgentInstancePayload`.
- Verified the new typed import surface through focused unit and packaging tests.

## Stage 3: Unit Tests

Commands run:

```powershell
python -m pytest tests/test_agent_instances.py -q
python -m pytest tests/test_agents_base.py -q
python -m pytest tests/test_sdk_package.py -q -k "package_builds_wheel_and_sdist_and_imports_from_wheel or provider_base_exports_resolve_from_documented_modules or shared_definition_exports_originate_from_shared_modules or cli_module_help_executes"
python -m pytest tests/test_sdk_package.py -q
```

Results:

- `tests/test_agent_instances.py`: passed (`6 passed`)
- `tests/test_agents_base.py`: passed (`22 passed`)
- Targeted `tests/test_sdk_package.py` coverage for DTO imports, packaging smoke, and CLI help: passed (`4 passed, 2 deselected`)
- Full `tests/test_sdk_package.py`: one failure remained outside this ticket's scope

Residual baseline failure:

- `tests/test_sdk_package.py::HarnessiqPackageTests::test_agents_and_providers_keep_shared_definitions_out_of_local_modules`
- Failure source: pre-existing violations under `harnessiq/providers/gcloud/client.py`
- Verification: reran that single test on a pristine detached worktree created directly from `origin/main`; it fails there with the same `gcloud` violations, so it is baseline and not introduced by Ticket 1

## Stage 4: Integration & Contract Tests

- The packaging smoke path inside the targeted `tests/test_sdk_package.py` run passed, which exercised:
  - wheel/sdist build
  - import of `harnessiq.shared.dtos.AgentInstancePayload` from the built wheel
  - CLI module import/help path
  - shared-definition module origin assertions
- This is the closest contract/integration test configured for the shared DTO package and the instance-store boundary.

## Stage 5: Smoke & Manual Verification

Command run:

```powershell
@'
from tempfile import TemporaryDirectory
from harnessiq.shared.dtos import AgentInstancePayload
from harnessiq.utils.agent_instances import AgentInstanceStore

with TemporaryDirectory() as temp_dir:
    store = AgentInstanceStore(repo_root=temp_dir)
    payload = AgentInstancePayload.from_dict({"query": "staff platform", "notify_on_pause": False})
    record = store.resolve(agent_name="linkedin_job_applier", payload=payload)
    reloaded = store.get(record.instance_id)
    assert reloaded.payload.to_dict() == {"notify_on_pause": False, "query": "staff platform"}
    print(record.instance_id)
'@ | python -
```

Observed output:

- Printed a stable instance id: `linkedin_job_applier::a4421e5dbe721624`

What this confirmed:

- The new DTO package imports at runtime without circular dependencies.
- `AgentInstanceStore.resolve(...)` accepts the DTO contract directly.
- Persistence and reload round-trip through JSON storage while preserving the normalized payload content.


## Post-Critique Changes
## Self-Critique

1. The first implementation made the shared agent-instance boundary too narrow by typing `BaseAgent.build_instance_payload()` and `AgentInstanceStore.resolve()` directly to `AgentInstancePayload`.

Why this mattered:

- Ticket 1 is supposed to establish the DTO foundation for later agent-specific DTO work.
- If the base contract only accepted the generic persistence envelope, later tickets would be forced to collapse richer agent DTOs back into `AgentInstancePayload` too early, weakening the public DTO design.

Improvement applied:

- Widened the base contract to `SerializableDTO` for `BaseAgent.build_instance_payload()`.
- Widened `AgentInstanceStore.resolve()` and `get_for_payload()` to accept `SerializableDTO | Mapping[str, Any] | None`, while still normalizing persisted records into `AgentInstancePayload`.
- Re-ran the focused suites covering the base-agent and instance-store boundary after the change:
  - `python -m pytest tests/test_agent_instances.py tests/test_agents_base.py -q`
  - `python -m pytest tests/test_sdk_package.py -q -k "package_builds_wheel_and_sdist_and_imports_from_wheel or provider_base_exports_resolve_from_documented_modules or shared_definition_exports_originate_from_shared_modules or cli_module_help_executes"`

2. The full `tests/test_sdk_package.py` suite still has one unrelated baseline failure under `harnessiq/providers/gcloud/client.py`.

Why this mattered:

- Without checking baseline, it would be easy to misattribute that failure to the DTO refactor.

Improvement applied:

- Verified the same failure on a pristine detached worktree from `origin/main` and recorded that evidence in the quality artifact so the residual risk is explicit.

