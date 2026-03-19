Phase 2 questions and responses:

1. Agent-private path constants: Several harnesses still keep `_PROMPTS_DIR`, `_MASTER_PROMPT_PATH`, and `_DEFAULT_MEMORY_PATH` inside the agent module. Do you want those moved into `harnessiq/shared/<agent>.py` as part of “all constants/configs,” or should the refactor stop at durable/public definitions and leave path-wiring local to the harness implementation?
Response: Path wiring can remain local to the harness implementation. The refactor should stop at misplaced durable/public constants, types, and config values.

Why this matters: This keeps behavioral module-local file-system wiring local while still enforcing the file-index rule for shared definitions.

2. Provider-local credential/config dataclasses: Many provider `client.py` files define credential/config dataclasses that are currently only consumed by that provider package. Do you want every one of those moved into `harnessiq/shared/` as the single source of truth, even if they are not yet cross-module, or only the ones already shared across modules?
Response: Move every misplaced provider config/type/constant into `harnessiq/shared/`, even when it is currently only consumed by one provider package.

Why this matters: The shared folder should become the single architectural source of truth for provider definition surfaces, not only the ones that already have multiple consumers.

3. Scope boundary outside agents/providers: `harnessiq/providers/output_sinks.py` and a few adjacent runtime modules also own config/constants that fit the same structural category, but your request explicitly names agents and providers. Should this pass stay strictly scoped to all agent/provider domains, or should I also normalize adjacent provider-like runtime surfaces in the same refactor?
Response: Normalize everything in the same pass, including adjacent provider-like runtime surfaces.

Why this matters: The refactor should aim for architectural consistency across the runtime surfaces that behave like provider integrations, not just the narrow directory names.

Implementation implications:
- Agent harness-local prompt path/default-memory wiring may remain in agent modules.
- All provider-side config/types/constants should move under `harnessiq/shared/`, including provider-local credential/config dataclasses and operation metadata definitions.
- Adjacent provider-like runtime surfaces such as output sinks are in scope for the same normalization pass.
