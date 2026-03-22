Title: Add a shared agent-instance registry and base runtime identity model

Intent: Introduce a generic SDK-level concept of agent instances so all harnesses can resolve a stable instance id/name from their payload, persist that mapping durably, and expose instance metadata through the base runtime.

Scope:
- Add shared utility helpers for agent instance ids, payload normalization/fingerprinting, and filesystem-backed instance persistence.
- Extend the base runtime and shared agent datamodel surface to expose instance id/name/record access.
- Do not yet wire every concrete agent constructor to register payloads automatically.

Relevant Files:
- `harnessiq/utils/agent_ids.py`: stable id and payload-fingerprint helpers.
- `harnessiq/utils/agent_instances.py`: filesystem-backed instance registry dataclasses and store helpers.
- `harnessiq/utils/__init__.py`: export new utility helpers.
- `harnessiq/shared/agents.py`: add typed instance-record datamodels shared by the SDK/runtime.
- `harnessiq/agents/base/agent.py`: integrate instance registration/access into `BaseAgent`.
- `tests/test_agents_base.py`: verify base-level instance behavior.
- `tests/test_agent_instances.py`: verify registry persistence, lookup, and id helpers.

Approach: Follow the existing `CredentialsConfigStore` pattern: small validated dataclasses, deterministic JSON serialization, load/save/upsert helpers, and explicit lookup methods. `BaseAgent` will accept a normalized instance payload plus an optional memory path candidate, resolve/create the instance record through the new store, and surface the resolved instance metadata through public properties without changing the run-loop semantics.

Assumptions:
- Persisted instance data belongs under `memory/` rather than `.harnessiq/`.
- Instance records should be queryable by id and by payload fingerprint.
- The stored payload must remain JSON-serializable and stable across process restarts.

Acceptance Criteria:
- [ ] SDK utilities can create stable payload fingerprints and instance ids.
- [ ] A filesystem-backed store can create, list, fetch, and resolve agent instances deterministically.
- [ ] `BaseAgent` exposes resolved instance metadata, including a stable id and name.
- [ ] Reconstructing the same agent name + payload resolves the same instance record.
- [ ] New tests cover base runtime integration and store behavior.

Verification Steps:
- Run targeted tests for the new utility store and base agent runtime.
- Run the full unit test suite after integration is complete.
- Manually instantiate a small test agent twice with the same payload and confirm the id is reused.

Dependencies: None.

Drift Guard: This ticket must not add LinkedIn-specific or Exa-specific behavior to the shared registry layer. It defines only the generic instance model and base runtime hooks.
