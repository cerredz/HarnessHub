Title: Finish shared agent-instance registration and per-instance memory resolution

Intent: Make every concrete Harnessiq agent resolve a stable `instance_id`, persist its payload in the shared registry, and use a per-instance memory directory so multiple instances of the same agent type can coexist safely.

Scope:
- Extend the shared base-agent contract to resolve and expose instance metadata.
- Export the existing instance-registry helpers from the public utility surface.
- Update all current concrete agents to pass stable payload snapshots and use the resolved memory path.
- Keep CLI-managed flows compatible while surfacing the resolved instance metadata for runs.
- Update tests and the architecture artifact.

Relevant Files:
- `harnessiq/agents/base/agent.py`: instance registration, repo-root resolution, and public instance accessors.
- `harnessiq/utils/__init__.py`: export agent id and instance-registry helpers.
- `harnessiq/agents/linkedin/agent.py`: deterministic payload builder and resolved memory-store path.
- `harnessiq/agents/exa_outreach/agent.py`: deterministic payload builder and resolved memory-store path.
- `harnessiq/agents/knowt/agent.py`: deterministic payload builder and resolved memory-store path.
- `harnessiq/agents/instagram/agent.py`: align with finalized base contract.
- `harnessiq/agents/prospecting/agent.py`: align with finalized base contract.
- `harnessiq/cli/*/commands.py`: emit instance ids and keep run-time registration consistent.
- `tests/test_agent_instances.py`, `tests/test_agents_base.py`, `tests/test_*agent.py`, `tests/test_*cli.py`: verification.
- `artifacts/file_index.md`: architectural update.

Approach: Reuse the existing `AgentInstanceStore` as the sole registry. `BaseAgent` will accept an optional `instance_payload`, optional `memory_path`, and optional `repo_root`, resolve an `AgentInstanceRecord` at construction time, and expose `instance_id`, `instance_name`, and `instance_record`. Concrete agents will build stable JSON-serializable payloads from their effective runtime/custom parameters and then derive their memory stores from the resolved base-agent `memory_path`. CLI run commands will continue to respect named folders or explicit memory roots, but they will also surface the resolved registry-backed instance id in their JSON output.

Assumptions:
- The current logical agent names (`linkedin_job_applier`, `instagram_keyword_discovery`, etc.) are the correct top-level keys for the shared memory layout.
- Existing CLI-managed folders remain supported and should not be migrated automatically.
- Documentation changes can stay focused on the new memory layout and instance registry rather than a full CLI redesign.

Acceptance Criteria:
- [ ] Every concrete agent exposes a stable `instance_id` and `instance_name`.
- [ ] The shared registry persists records in `memory/agent_instances.json` with payloads and resolved memory paths.
- [ ] Default SDK memory paths resolve to per-instance folders under `memory/agents/<agent_name>/<instance_id>/`.
- [ ] Explicit `memory_path` usage remains compatible and still registers the instance.
- [ ] CLI run flows include the resolved instance id in their output and continue to use the expected durable memory folder.
- [ ] Tests cover the shared runtime behavior and concrete agent integration.

Verification Steps:
- Run targeted unit tests for the registry store and base runtime.
- Run targeted concrete-agent and CLI tests for the affected harnesses.
- Run a focused packaging/import smoke test that exercises public exports.
- Manually inspect a temp repo run to confirm the registry file and per-instance memory path are created as expected.

Dependencies: None.

Drift Guard: This ticket must not redesign tool execution, prompt behavior, or per-agent durable file schemas. It is limited to stable instance identity, memory-path resolution, exports, tests, and architecture documentation.
