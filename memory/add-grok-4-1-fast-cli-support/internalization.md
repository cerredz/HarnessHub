### 1a: Structural Survey

- `harnessiq/` is the primary Python package. The system is organized around provider-agnostic agents, manifest-backed CLI adapters, provider clients/request builders, and shared DTO/config modules.
- `harnessiq/cli/` owns the top-level `harnessiq` command. `harnessiq/cli/main.py` builds the root parser, and `harnessiq/cli/commands/platform_commands.py` registers the platform-first `prepare/show/run/resume/inspect/credentials` flows for every manifest-backed harness.
- `harnessiq/cli/common.py` holds shared CLI surfaces for agent selection, model selection, runtime config construction, import-path factory loading, and parsing of open-ended `KEY=VALUE` CLI arguments.
- `harnessiq/cli/runners/lifecycle.py` resolves persisted run state, merges resume overrides, constructs the selected model through `resolve_agent_model`, and executes the chosen harness adapter with a provider-agnostic `AgentModel`.
- `harnessiq/cli/adapters/` contains one adapter per harness. The Instagram path is in `harnessiq/cli/adapters/instagram.py`; it translates CLI arguments into `InstagramKeywordDiscoveryAgent.from_memory(...)` and passes a selected model plus runtime config.
- `harnessiq/shared/` contains manifest definitions, DTOs, and durable memory-store helpers. `harnessiq/shared/instagram.py` defines the Instagram harness manifest, runtime/custom parameters, memory layout, and the durable store used by the adapter and agent.
- `harnessiq/integrations/agent_models.py` is the provider-backed model abstraction. It parses `provider:model_name`, creates provider-specific `AgentModel` implementations from env-backed credentials or stored profiles, and translates canonical agent requests into provider-native payloads.
- `harnessiq/providers/` contains provider-specific request builders and HTTP clients. The Grok integration lives in `harnessiq/providers/grok/`, with request serialization in `requests.py` and transport in `client.py`.
- `harnessiq/config/model_profiles.py` persists reusable model profiles, including provider, model name, temperature, max output tokens, and optional `reasoning_effort`.
- Tests are broad and mostly pytest-based under `tests/`. Relevant coverage is split by concern: provider translation (`tests/test_grok_provider.py`), model abstraction (`tests/test_agent_models.py`), CLI/common helpers (`tests/test_cli_common.py`), and end-to-end platform CLI flows (`tests/test_platform_cli.py`).
- Conventions in this codebase:
  - DTOs and config objects are dataclasses with normalization/validation in `__post_init__`.
  - CLI modules are JSON-oriented, deterministic, and layered: parse args -> build context -> resolve run request -> execute adapter.
  - Provider request builders omit `None` values before sending payloads.
  - Tests favor direct object inspection and patched seams over full subprocess execution.
- Observed inconsistency relevant to this task: Grok support currently assumes the reasoning-capable model family in docs/examples (`grok-4-1-fast-reasoning`) while some fixtures and sink metadata already reference non-reasoning variants (`grok-4-1-fast`). That suggests the plumbing partially expects both families but the runtime request shaping may not yet distinguish them.

### 1b: Task Cross-Reference

- User request: support `--model grok:grok-4.1-fast` for agent CLI runs, including the platform-first `harnessiq run instagram ...` flow.
- The entrypoint for that command is `harnessiq/cli/main.py` -> `harnessiq/cli/commands/platform_commands.py` -> `HarnessCliLifecycleRunner.execute_run()` in `harnessiq/cli/runners/lifecycle.py`.
- Model resolution for `--model grok:grok-4.1-fast` happens in `harnessiq/cli/common.py::resolve_agent_model`, which delegates to `harnessiq.integrations.create_model_from_spec`.
- `harnessiq/integrations/agent_models.py` is the key behavior surface:
  - `parse_model_spec()` must accept the user’s provider/model syntax unchanged.
  - `create_model_from_spec()` and `create_provider_model()` must construct a `GrokAgentModel`.
  - `ProviderAgentModel._generate_grok_turn()` currently always forwards `self._reasoning_effort` into `GrokChatCompletionRequestDTO`.
  - `GrokAgentModel.with_model_override()` currently preserves reasoning effort across model overrides without considering model capability.
- `harnessiq/shared/dtos/providers.py::GrokChatCompletionRequestDTO` and `harnessiq/providers/grok/requests.py::build_chat_completion_request()` define whether `reasoning_effort` is emitted into the outgoing xAI payload.
- The Instagram harness path in `harnessiq/cli/adapters/instagram.py` does not contain Grok-specific logic; preserving its existing behavior means any fix should happen below the harness adapter, in shared model/provider plumbing.
- Persisted profile behavior may also be affected:
  - `harnessiq/config/model_profiles.py` stores `reasoning_effort` for reusable profiles.
  - `create_model_from_profile()` in `harnessiq/integrations/agent_models.py` must keep reasoning-enabled Grok profiles working while allowing non-reasoning Grok models to run without invalid request fields.
- Relevant tests to update or add:
  - `tests/test_agent_models.py` for provider-agent model behavior when Grok model names are non-reasoning.
  - `tests/test_grok_provider.py` for request payload emission rules.
  - `tests/test_cli_common.py` and/or `tests/test_platform_cli.py` for CLI acceptance of the target model string in the `run instagram` path.
- Documentation/examples likely touched:
  - `docs/agent-runtime.md`, CLI skill docs, or other Grok-specific examples if they currently imply only reasoning-capable Grok models are supported.
- Existing behavior that must be preserved:
  - `grok:grok-4-1-fast-reasoning` plus explicit `reasoning_effort` must continue working.
  - `--model`, `--profile`, and `--model-factory` selection rules must remain unchanged.
  - Instagram adapter behavior, search backend loading, sink injection, and memory persistence must remain unchanged.

### 1c: Assumption & Risk Inventory

- Assumption: `grok-4.1-fast` is a valid user-facing CLI model string for xAI, and the repo should normalize or accept dotted/hyphenated naming as entered rather than forcing one canonical spelling everywhere.
- Assumption: the main runtime failure is the presence of `reasoning_effort` on non-reasoning Grok models, not rejection of the model string at the CLI parser layer.
- Assumption: support is meant for all agents because the shared model adapter is reused by every harness, so the correct fix belongs in shared Grok model/request code rather than in one harness adapter.
- Risk: if the implementation infers capability only from a hard-coded substring, future Grok model names may be misclassified. The fix should use a small, explicit capability helper with tests rather than ad hoc checks spread through the code.
- Risk: stored model profiles can still carry `reasoning_effort`; the runtime must gracefully suppress that field for non-reasoning models without mutating persisted profile data or breaking reasoning-capable runs.
- Risk: docs and tests currently mix `grok-4-1-fast` and `grok-4-1-fast-reasoning`. A partial code-only fix could leave examples misleading or leave gaps in regression coverage.

Phase 1 complete.
