Title: Wire concrete harnesses and SDK exports into payload-driven instance resolution

Intent: Make the shared instance model real for SDK users by teaching the concrete harnesses to register their normalized parameters as instance payloads and by exporting retrieval helpers from the public package surface.

Scope:
- Update concrete agent constructors to provide stable payload snapshots to `BaseAgent`.
- Preserve existing memory-store behavior while ensuring different parameter payloads create different instance records automatically.
- Export the retrieval APIs from the SDK surface and update documentation/tests.
- Do not redesign the CLI interaction model beyond keeping it compatible with the new instance registry.

Relevant Files:
- `harnessiq/agents/linkedin/agent.py`: register LinkedIn payloads and resolved instance memory path.
- `harnessiq/agents/exa_outreach/agent.py`: register ExaOutreach payloads and resolved instance memory path.
- `harnessiq/agents/knowt/agent.py`: register Knowt payloads and resolved instance memory path.
- `harnessiq/agents/email/agent.py`: keep base-email inheritance compatible with the new base constructor surface.
- `harnessiq/agents/__init__.py`: export instance-store APIs.
- `README.md`: document instance ids/names and retrieval.
- `artifacts/file_index.md`: reflect the new shared instance registry if the architecture changes materially.
- `tests/test_linkedin_agent.py`: verify LinkedIn payload-driven instance creation/reuse.
- `tests/test_linkedin_cli.py`: confirm CLI-backed flows remain compatible.
- Additional tests for Knowt/ExaOutreach as needed.

Approach: Refactor constructors so the base class resolves the instance identity before the concrete memory stores are finalized, then build each harness config/memory store from the resolved memory path. Payloads will include only deterministic, user-meaningful parameters and exclude non-serializable runtime objects such as model adapters and live clients.

Assumptions:
- LinkedIn custom/runtime parameter files remain the source of truth for resumed runs; the instance registry is metadata, not a replacement memory store.
- Default instance names can be derived from logical agent names plus stable ids rather than requiring new user input.

Acceptance Criteria:
- [ ] LinkedIn, ExaOutreach, and Knowt agents each receive stable instance ids and names.
- [ ] Changing the normalized payload for the same logical agent creates a different persisted instance record automatically.
- [ ] SDK users can list/get instance records with their stored payload/configuration.
- [ ] Existing targeted agent/CLI tests continue to pass after the integration.
- [ ] Public docs/exports describe the new SDK capability.

Verification Steps:
- Run targeted agent and CLI tests for the updated harnesses.
- Run the full test suite.
- Manually instantiate the same concrete agent twice with different parameter payloads and confirm distinct ids/memory paths.

Dependencies: Ticket 1.

Drift Guard: This ticket must not change the semantics of agent tool execution, context resets, or concrete memory-file schemas beyond what is required to attach instance metadata and resolved memory paths.
