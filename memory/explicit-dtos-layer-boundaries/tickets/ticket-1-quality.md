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
