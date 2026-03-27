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
