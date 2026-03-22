### 1a: Structural Survey

Top-level architecture:
- `harnessiq/` is the shipped SDK package. It contains the reusable agent runtime, concrete harnesses, CLI entrypoints, provider clients, tool factories, config helpers, and shared datamodels/constants.
- `docs/` contains usage and runtime behavior documentation for the SDK.
- `artifacts/` contains repository-shape guidance; `artifacts/file_index.md` is the architectural reference artifact supplied with this task.
- `tests/` is the verification surface. The project mixes `unittest`-style test cases and `pytest` execution.
- `memory/` is already used as a durable filesystem area for agent state and for local engineering artifacts created during prior tasks.

Source layout and responsibilities:
- `harnessiq/agents/base/agent.py` defines `BaseAgent`, the provider-agnostic run loop. It owns system prompt assembly, durable parameter section refresh, transcript recording, pause handling, and context-reset/compaction behavior.
- `harnessiq/shared/agents.py` defines core runtime datamodels such as `AgentRuntimeConfig`, `AgentModelRequest`, `AgentParameterSection`, and `AgentRunResult`.
- `harnessiq/agents/linkedin/agent.py` contains the LinkedIn harness and `LinkedInMemoryStore`. This is the most mature example of file-backed durable memory, parameter/config hydration from disk, and CLI-backed agent setup.
- `harnessiq/shared/linkedin.py`, `harnessiq/shared/exa_outreach.py`, and `harnessiq/shared/knowt.py` hold definition-only constants, configs, and memory-store datamodels for the concrete harnesses.
- `harnessiq/agents/exa_outreach/agent.py` and `harnessiq/utils/run_storage.py` show the other persistence pattern in the repo: a generic filesystem-backed store/registry for runs with stable JSON schemas.
- `harnessiq/config/credentials.py` is the closest existing persistence pattern to reuse for instance registration. It provides a small JSON-backed config store rooted at repo-local filesystem paths with explicit dataclasses, upsert/load/resolve helpers, and deterministic serialization.
- `harnessiq/cli/` provides JSON-emitting command handlers that prepare memory folders, persist configuration, and run agents from durable state.
- `harnessiq/agents/__init__.py` is the public SDK export surface.

Technology stack:
- Python 3.11+ package built with setuptools (`pyproject.toml`).
- Minimal dependency surface in `project.dependencies`; most functionality is pure stdlib plus provider-specific modules in-repo.
- CLI is `argparse`.
- Tests run in local Python tooling (`pytest` present in repo environment, but tests themselves often use `unittest`).

Data flow through the system:
- Agent constructors wire a model adapter, a tool executor/registry, runtime config, and sometimes a memory path.
- `BaseAgent.run()` calls `prepare()`, refreshes parameter sections, then repeatedly builds `AgentModelRequest`, records model output, executes tools, optionally rewrites context via compaction, and resets context when the token budget is exceeded.
- Durable state is currently owned by concrete harnesses, not by `BaseAgent`. LinkedIn, Knowt, and ExaOutreach each maintain separate memory-store abstractions and file conventions.
- CLI commands typically resolve a memory path from `--agent` plus `--memory-root`, persist memory/config files there, and later reconstruct the agent from that memory path.

Test strategy:
- Focused unit tests exist for base runtime behavior, concrete agents, CLI commands, config stores, provider clients, tools, and packaging smoke tests.
- The highest-value coverage points for this task are `tests/test_agents_base.py`, `tests/test_linkedin_agent.py`, `tests/test_linkedin_cli.py`, and config-store style tests such as `tests/test_credentials_config.py`.

Observed conventions:
- Dataclasses with `slots=True` and strong `__post_init__` validation are the standard pattern for persisted config/data models.
- Filesystem-backed stores use explicit path properties plus `prepare()`, `read_*`, and `write_*` helpers.
- JSON is written with `indent=2` and `sort_keys=True`.
- Public package APIs are re-exported through package `__init__.py` modules.
- Runtime-parameter normalization is explicit and narrow rather than accepting arbitrary dictionaries silently.

Current inconsistencies relevant to this task:
- `BaseAgent` accepts `memory_path`, but concrete agents do not use it consistently. `KnowtAgent` passes it to `BaseAgent`; `LinkedInJobApplierAgent` and `ExaOutreachAgent` currently do not, even though they are memory-backed.
- Agent identity today is split between logical harness names (`BaseAgent.name`) and user-chosen memory-folder names (`candidate-a`, `campaign-a`, etc.). There is no generic concept of an agent instance id.
- The persistence patterns are split between per-agent memory stores and repo-local config stores; there is no shared instance registry for the SDK.
- The git worktree is dirty before this task, so edits must be additive and careful around already-modified files.

### 1b: Task Cross-Reference

Task requirement mapping:
- “Have multiple instances of the same agent” maps to `BaseAgent` plus concrete constructors. The base runtime needs a generic instance identity model, while concrete agents need to provide the payload/config used to determine whether a run belongs to an existing instance or a new one.
- “Build this functionality into our base agent class” maps primarily to `harnessiq/agents/base/agent.py`, with supporting datamodel additions in `harnessiq/shared/agents.py`.
- “Store a user's agents' instances somewhere for the sdk” maps to a new shared persistence layer patterned after `harnessiq/config/credentials.py` and/or `harnessiq/utils/run_storage.py`. The best fit is a new utility store under `harnessiq/utils/` plus durable files under the repo filesystem (`memory/` is already the established durable area for agent state).
- “At the end of your implementation, each agent should have a name and id” maps to the public `BaseAgent` API, public datamodel/export surface, and tests that can assert `agent.name` plus a new id property.
- “Id creation/retrieval helper functions inside of utils folder” maps to a new utility module under `harnessiq/utils/` for stable id generation, payload fingerprinting, and lookup helpers.
- “Retrieve agent instances with their config/parameters with our sdk” maps to a new public instance-store/query API and package exports so SDK users can list, fetch by id, and fetch by payload with parameters/config included in the stored record.
- “Every time a user runs an agent the parameters should be treated as the payload and every time they are different a new instance ... should be created automatically on the backend” maps to constructor-time or prepare-time registration logic for each concrete agent. This needs explicit payload snapshots derived from runtime parameters/config rather than raw memory folder names.

Concrete files likely touched:
- `harnessiq/agents/base/agent.py`: add shared instance identity/registration behavior and public accessors.
- `harnessiq/shared/agents.py`: add instance datamodel(s) if the base runtime needs shared typed records.
- `harnessiq/utils/`: add id helpers and an agent-instance persistence store.
- `harnessiq/agents/linkedin/agent.py`: register/reuse instances using LinkedIn runtime/custom parameters and durable memory path defaults; likely the highest-impact concrete harness because it already hydrates from memory and exposes CLI flows.
- `harnessiq/agents/exa_outreach/agent.py`: same integration so the feature is base-level rather than LinkedIn-only.
- `harnessiq/agents/knowt/agent.py`: same integration for consistency.
- `harnessiq/agents/__init__.py` and possibly `harnessiq/utils/__init__.py`: export new SDK APIs.
- `tests/test_agents_base.py`: verify instance id/name exposure and generic registration behavior.
- `tests/test_linkedin_agent.py`, `tests/test_linkedin_cli.py`, and likely new utility-store tests: verify payload-driven instance creation/retrieval and backward-compatible behavior.
- `README.md` and `artifacts/file_index.md`: update the documented architecture/public behavior if the public SDK surface changes materially.

Existing behavior that must be preserved:
- Current agent loops, parameter refresh, context resets, pause behavior, and tool execution semantics.
- Existing per-agent durable memory file formats, unless a compatibility-preserving extension is required.
- Current constructor ergonomics for direct SDK usage and CLI-backed memory preparation.

Blast radius:
- Medium to high. The change cuts across the base runtime, public SDK exports, concrete harness constructors, memory-path defaults, and tests.
- The main architectural risk is coupling instance registration too tightly to one concrete agent’s memory conventions instead of making it generic.

### 1c: Assumption & Risk Inventory

Assumptions I can implement against:
- “Parameters as payload” means the normalized runtime/config inputs that materially distinguish one agent run from another, not ephemeral values like a model object instance or tool executor object identity.
- Same logical agent type + same normalized payload should resolve to the same persisted instance; a different normalized payload should create a new instance record automatically.
- The persisted instance record should include enough data for SDK retrieval without reconstructing the live agent object: at minimum logical agent name, instance id, instance display name, payload/config snapshot, timestamps, and memory path.
- `memory/` is the correct durable filesystem root for instance persistence because the repo already treats it as durable agent state and the user explicitly suggested the SDK filesystem/memory folder.

Risks and edge cases:
- The repo currently allows callers to pass explicit `memory_path` values. If instance identity is payload-driven, explicit paths can conflict with previously-registered instances for the same payload. The implementation needs a deterministic precedence rule.
- Some agent constructor arguments are not JSON-serializable (`model`, live clients, tool objects). Payload extraction must be explicit and limited to serializable configuration values.
- Existing CLI flows name agent folders by user-provided slugs. Automatic instance creation must not silently break those flows or orphan existing memory folders.
- `BaseAgent.run()` currently calls `prepare()` on every invocation. Instance registration should not create duplicate records on repeated runs with the same payload.
- The worktree is already dirty in several relevant files, so any edits must be based on the current in-worktree content rather than assumptions from `HEAD`.
- The skill’s GitHub issue creation step may be blocked by the environment’s network restrictions; if so, local ticket artifacts will need to stand in for remote issue creation.

Phase 1 complete
