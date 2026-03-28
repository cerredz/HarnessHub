### 1a: Structural Survey

Repository shape:
- `harnessiq/` is the authoritative Python package and contains the agent runtime, shared manifests, CLI layers, providers, tools, and integrations.
- `tests/` mirrors the public package surface closely and includes command-family tests, manifest-registry tests, docs-sync tests, and package-hygiene tests.
- `artifacts/` and `docs/` are generated or synchronized documentation surfaces driven from live manifests and CLI registrations.
- `scripts/sync_repo_docs.py` regenerates repository docs from the current codebase and is part of the verification surface.
- `memory/` holds implementation artifacts and prior task traces. This task is using `memory/add-email-agent-cli/`.

Technology and runtime:
- Python package with `argparse`-based CLI entrypoint at `harnessiq/cli/main.py`.
- Agent runtime is built around `BaseAgent` in `harnessiq/agents/base/agent.py`, with tool execution, transcript management, dynamic tool selection, and ledger emission.
- Durable harness configuration is modeled declaratively through `HarnessManifest` in `harnessiq/shared/harness_manifest.py`.
- Platform-first CLI commands (`prepare`, `show`, `run`, `inspect`, `credentials`) are generated from registered manifests in `harnessiq/shared/harness_manifests.py`.
- Dedicated command families such as `instagram` coexist with platform-first commands and typically share the same underlying memory-store and agent logic.

CLI architecture and conventions:
- `harnessiq/cli/main.py` only wires command families into the root parser.
- Dedicated command-family `commands.py` modules are thin: they define argparse flags and forward to builders/runners. Existing `instagram/commands.py` is the clearest reference pattern.
- Builders in `harnessiq/cli/builders/` own memory-path resolution, persistence of text/config files, and state-summary construction.
- Runners in `harnessiq/cli/runners/` own execution-time orchestration, environment seeding, agent construction, and result shaping.
- Platform adapters in `harnessiq/cli/adapters/` translate manifest-driven generic commands into harness-native stores and runtime construction. `StoreBackedHarnessCliAdapter` is the primary abstraction for store-backed harnesses.
- The repository strongly separates parser concerns from business logic. This matches the user’s request that the CLI remain a pure argument parser and executor.

Agent-layer architecture and conventions:
- Reusable agent families derive from `BaseAgent`. Concrete harnesses override `build_system_prompt`, `load_parameter_sections`, `build_instance_payload`, and optionally ledger output helpers.
- `BaseEmailAgent` in `harnessiq/agents/email/agent.py` already provides Resend tool wiring, credential masking, and email-specific system-prompt framing, but it is abstract and does not yet define a concrete durable-memory email harness.
- Existing durable harnesses such as Instagram keep their state in `harnessiq/shared/<harness>.py` and expose a memory-store object, manifest, runtime config dataclasses, and normalization helpers there.
- Concrete agent modules often maintain prompt files under `harnessiq/agents/<harness>/prompts/` and use a small number of allowed module-level constants. Package hygiene tests in `tests/test_sdk_package.py` constrain new agent-module constants.

Data flow relevant to this task:
- CLI command parses args -> builder/runner or platform adapter resolves memory path -> memory store loads persisted config -> runner/adapter constructs agent -> `agent.run()` executes tool-backed model loop -> ledger output is emitted through the base runtime.
- For Instagram today, leads/emails are persisted in harness-native JSON memory and can also be exported to MongoDB through ledger sink configuration.
- MongoDB support currently exists in `harnessiq/providers/output_sink_clients.py` as a write-oriented client (`insert_documents`) for output sinks. There is no general read/query abstraction yet.
- Resend support exists as tool-driven agent capability via `BaseEmailAgent` and `resend_request`, plus credential binding through provider-family metadata surfaced by manifests and platform CLI commands.

Testing strategy and repository standards:
- Command families have focused CLI tests that patch agent construction and assert parser registration, persistence behavior, and JSON output shape.
- Platform-first manifest behavior is covered in `tests/test_platform_cli.py`.
- Manifest registry and coercion contracts are covered in `tests/test_harness_manifests.py`.
- Email support currently has only base-harness tests in `tests/test_email_agent.py`.
- `tests/test_docs_sync.py` enforces synchronized docs. Any new manifest or CLI surface requires re-running the repo doc sync script.
- The codebase favors typed dataclasses, JSON-safe DTOs, explicit normalization functions, and deterministic output payloads.

Inconsistencies or gaps relevant to the task:
- Email capability exists at the abstract agent layer but has no concrete harness, no manifest, no dedicated CLI family, and no platform adapter.
- MongoDB support is asymmetric: the repo can write leads to Mongo as an output sink but cannot yet read those leads back through a shared provider interface.
- Documentation and file index currently enumerate built-in manifests without an email harness, so those artifacts will drift as soon as email is added unless regenerated.

### 1b: Task Cross-Reference

User request mapping:
- “Build on top of our CLI integration for our emailing agent” maps to the missing dedicated command family in `harnessiq/cli/` and a missing manifest-backed adapter in `harnessiq/cli/adapters/`.
- “I dont want to have to create a seperate script” means the earlier helper-script approach must be replaced by first-class CLI commands and reusable repository code.
- “Create a new system in our CLI folder for the emailing agent” maps to net-new files under:
  - `harnessiq/cli/email/`
  - `harnessiq/cli/builders/`
  - `harnessiq/cli/runners/`
  - `harnessiq/cli/adapters/`
- “Include all of the capabilities that our instagram agent has in the CLI” maps to parity with the Instagram family’s lifecycle surface:
  - dedicated `prepare`, `configure`, `show`, `run`
  - one data-inspection command analogous to `get-emails`
  - platform-first `prepare/show/run/inspect/credentials` support through a manifest and adapter
  - resumability and run-snapshot compatibility inherited from the platform runner
- “The CLI should be a pure argument parser and executor and have no business logic” maps directly to preserving the existing split where:
  - parser code remains in `harnessiq/cli/email/commands.py`
  - persistence/state logic moves into a builder
  - execution/runtime composition moves into a runner and adapter
  - durable workflow logic moves into shared store/config and concrete agent code
- “Extrapolate all of the logic to either the adapters or builders folders” maps to keeping command modules thin and introducing reusable abstractions instead of inline command logic.
- “Follow the software design patterns in our repository and adhere to the file index” maps to:
  - registering a new `EMAIL_HARNESS_MANIFEST`
  - exporting the new harness from package `__init__` modules
  - updating `artifacts/file_index.md` and generated command docs via the repo sync script
  - following existing manifest/store/adapter conventions instead of inventing a bespoke CLI path
- “Update the instructions in the Obsidian file” maps to modifying the previously created Obsidian note so it uses the new CLI commands rather than a helper script.

Concrete files and modules implicated:
- Existing files to modify:
  - `harnessiq/cli/main.py`
  - `harnessiq/cli/builders/__init__.py`
  - `harnessiq/cli/runners/__init__.py`
  - `harnessiq/cli/adapters/__init__.py`
  - `harnessiq/shared/harness_manifests.py`
  - `harnessiq/shared/__init__.py`
  - `harnessiq/agents/email/__init__.py`
  - `harnessiq/providers/output_sink_clients.py`
  - `harnessiq/interfaces/output_sinks.py`
  - generated docs and the Obsidian note
- Net-new likely files:
  - `harnessiq/shared/email_harness.py` or equivalent shared email harness module containing manifest, config, and durable store
  - `harnessiq/agents/email/campaign.py` or equivalent concrete harness implementation
  - `harnessiq/cli/email/__init__.py`
  - `harnessiq/cli/email/commands.py`
  - `harnessiq/cli/builders/email.py`
  - `harnessiq/cli/runners/email.py`
  - `harnessiq/cli/adapters/email.py`
  - email CLI and platform tests

Existing behavior that must be preserved:
- The abstract `BaseEmailAgent` API and existing tests in `tests/test_email_agent.py` must remain valid.
- Instagram CLI behavior and manifest-driven platform flows must not regress.
- Dedicated CLI modules must stay thin and JSON-output behavior must stay deterministic.
- Generated docs must remain synchronized with the code.

Blast radius:
- CLI registration surface changes globally because a new root command family and a new built-in manifest will be visible.
- Manifest registry tests and docs sync tests will fail until updated and regenerated.
- Platform-first credential commands will pick up a new harness automatically once the manifest is registered.
- MongoDB client changes will affect a shared provider used by sinks, so additions must be backward compatible.

### 1c: Assumption & Risk Inventory

Assumptions:
- The intended first-class email CLI is specifically for the previously requested workflow: read Instagram leads from MongoDB and send email batches through Resend.
- “All of the capabilities that our instagram agent has in the CLI” means lifecycle parity, not a one-to-one replication of Instagram domain behaviors.
- The email harness should participate in both dedicated and platform-first CLI flows because that is how the repository structures supported harnesses.
- Reading MongoDB-backed leads belongs in shared/provider logic rather than command modules, even though current Mongo support is sink-oriented.
- It is acceptable for the new concrete email harness to use a durable memory folder for sender identity, campaign content, source configuration, and runtime parameters.

Ambiguities judged low-risk enough to resolve in implementation:
- The exact analog to Instagram’s `get-emails` command is not specified. A likely email-domain equivalent is a recipient preview/export command that returns deduped source recipients.
- The user did not specify whether email message content should be model-generated or purely operator-supplied. Given the earlier Obsidian workflow, the safer default is operator-supplied subject/body stored in memory and used by the harness.
- The user did not specify all supported source schemas inside Mongo. The implementation will need a narrow, explicit contract that matches the current Instagram-lead export shape and can tolerate common variants.

Implementation risks:
- Adding MongoDB read/query support in the wrong layer could violate the repository’s separation patterns. The change must stay provider- or shared-domain-centric, not CLI-centric.
- A new concrete email agent could introduce extra module-level constants that violate `tests/test_sdk_package.py` if the file is structured carelessly.
- Manifest/provider-family metadata must align with credential-binding infrastructure or generic `credentials bind email ...` will not work.
- Docs sync must be rerun after manifest registration or repo tests will fail.
- Updating the Obsidian note must reflect the final CLI shape exactly; otherwise the docs will immediately drift from the implementation.

No blocking ambiguities remain that require user clarification for a first implementation aligned to the repository’s existing patterns.

Phase 1 complete
