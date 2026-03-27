### 1a: Structural Survey

Repository shape:

- `harnessiq/` is the only live source tree. `build/`, `src/`, and `harnessiq.egg-info/` are generated or residual.
- `harnessiq/cli/` owns the argparse command surface. `harnessiq/cli/main.py` registers top-level command families directly.
- `harnessiq/cli/commands/` contains the platform-first generic harness commands (`prepare`, `show`, `run`, `resume`, `inspect`, `credentials`).
- `harnessiq/cli/adapters/` contains harness-specific adapter implementations that bridge manifest-backed generic CLI state into concrete agents and native memory stores.
- `harnessiq/shared/` is the declarative metadata and cross-package type layer. Harness manifests live here and drive the generic CLI.
- `harnessiq/config/` owns persisted repo-local credential bindings, model profiles, and harness profile/run snapshot persistence.
- `harnessiq/agents/` owns runtime orchestration and concrete harness implementations.
- `harnessiq/providers/` currently contains model providers plus many external service provider packages. There is no existing `gcloud` or Google Cloud deployment package.
- `harnessiq/utils/` contains runtime infrastructure such as durable run storage, ledger sinks, and harness-manifest helpers.
- `tests/` is broad and mostly uses `pytest` assertions with `unittest`-style modules and direct argparse entrypoint testing.

Technology and execution model:

- Python 3.11+ package with setuptools in `pyproject.toml`.
- No configured formatter, linter, or type checker is declared in `pyproject.toml`.
- CLI is argparse-based, JSON-emitting, and deterministic. Existing commands generally return structured JSON rather than human-oriented tables unless they are legacy specialized commands.
- Runtime state is file-backed under `memory/` and repo-local `.harnessiq/`.

CLI architecture:

- Top-level commands are registered in `harnessiq/cli/main.py`.
- The modern CLI path is manifest-driven: `harnessiq/cli/commands/platform_commands.py` enumerates harness manifests and delegates behavior to adapter factories declared on each manifest.
- There are also older harness-specific command families such as `harnessiq linkedin ...`, implemented as dedicated argparse modules.
- Shared CLI helpers in `harnessiq/cli/common.py` define conventions for option naming, model selection, parameter parsing, repo-root detection, and JSON output.

Configuration and credential architecture:

- Repo-local agent credential bindings are persisted through `CredentialsConfigStore` in `harnessiq/config/credentials.py`, backed by `.harnessiq/credentials.json`.
- Those bindings map logical agent credential fields to repo-local `.env` variables, then resolve concrete values from `.env` at runtime.
- Harness profile state is persisted per memory folder via `HarnessProfileStore` in `harnessiq/config/harness_profiles.py`.
- Model-provider credentials for Anthropic/OpenAI/Gemini/Grok are loaded directly from process environment in `harnessiq/integrations/agent_models.py`.
- Current credential handling is local and repo-scoped. There is no cloud secret sync mechanism yet.

Runtime and durable memory:

- `BaseAgent` in `harnessiq/agents/base/agent.py` treats durable parameter sections as a first-class runtime concept and refreshes them on resets.
- Durable state today is primarily local filesystem state under each harness memory folder.
- `harnessiq/utils/run_storage.py` provides a pluggable storage protocol with a filesystem implementation, showing the codebase already values backend abstraction around durability.
- The generated architecture artifact explicitly states that durable memory must survive resets and restarts.

Provider architecture:

- Existing providers are mostly package-per-service with `client.py`, `api.py`, `operations.py`, and sometimes `credentials.py`/`requests.py`.
- Provider code generally favors small explicit classes/functions, clear exports from `__init__.py`, and isolated tests.
- There is no existing provider sub-tree that resembles the proposed hierarchical `providers/gcloud/{deploy,credentials,infra,...}` layout.

Testing strategy and conventions:

- CLI tests invoke `harnessiq.cli.main.main(...)` directly and assert on JSON payloads.
- Config tests focus on file-backed stores, normalization, and failure messages.
- Provider tests are generally unit tests with fakes/mocks rather than live integration tests.
- The repo favors explicit dataclasses for persisted/configured state and direct unit tests against those dataclasses and stores.

Relevant inconsistencies or constraints:

- The design docs use Click-style CLI examples, but this repository uses argparse everywhere.
- The design docs assume a new deployment-centric command family (`harnessiq gcloud ...`), while the existing repo centers around local harness execution and manifest-backed prepare/run flows.
- The current git checkout is not on `main`; it is on `add-never-stop-master-prompt` and already has unrelated untracked files under `memory/`. That matters for later worktree/sync steps.

### 1b: Task Cross-Reference

Requested change mapped onto the codebase:

- Add a new Google Cloud provider layer under `harnessiq/providers/gcloud/`.
  - This is entirely net-new. No existing `gcloud` package exists.
  - The proposed layout fits the repo’s package-per-domain style, but will be the first provider tree with nested domains (`deploy`, `credentials`, `infra`, `storage`, `observability`, `commands`).

- Add a GCP command-builder helper layer under `harnessiq/providers/gcloud/commands/`.
  - Also net-new.
  - This aligns with the repo’s preference for explicit typed helpers and unit-testable pure functions.
  - It will need new tests under `tests/`, likely `tests/test_gcloud_commands_*.py` or similar.

- Add config/state for GCP agent deployment settings.
  - This likely belongs in `harnessiq/providers/gcloud/config.py` per the spec.
  - It overlaps conceptually with existing persisted config stores in `harnessiq/config/`, especially `HarnessProfileStore` and `CredentialsConfigStore`.
  - There is currently no established location for provider-specific persisted deployment config outside provider packages, so `providers/gcloud/config.py` is plausible and consistent with the design doc.

- Add new top-level CLI commands: `harnessiq gcloud ...`
  - This requires modifying `harnessiq/cli/main.py` to register a new command family.
  - A new CLI module tree such as `harnessiq/cli/gcloud/` would follow existing patterns for dedicated command families.
  - The credential subcommands in the design doc overlap in name with the existing top-level `harnessiq credentials ...`, so the new family must stay namespaced under `gcloud` to avoid command conflicts.

- Add a credential bridge from local harness credentials to GCP Secret Manager.
  - This touches existing credential concepts in `harnessiq/config/credentials.py`, existing model env handling in `harnessiq/integrations/agent_models.py`, and harness manifests/agent module naming in `harnessiq/shared/harness_manifests.py`.
  - The bridge spec relies on `HARNESSIQ_AGENT_MODULE` in saved config `env_vars`, but there is no existing GCP config model or saved deploy config that currently stores that key.
  - The bridge also overlaps with existing repo-local `.env` resolution conventions. The current codebase resolves most service credentials through `.env` bindings, not raw `os.environ` lookups, so the bridge design may need adaptation.

- Add Cloud Storage-backed memory persistence for scheduled runs.
  - This maps conceptually to `BaseAgent.load_parameter_sections()` in `harnessiq/agents/base/agent.py` and existing file-backed memory stores in concrete harnesses.
  - No current abstraction plugs remote object storage into agent memory loading/saving. The spec proposes a `CloudStorageProvider`, but integration points with actual agents are not defined in the current codebase yet.
  - This is broader than “just add a provider”; it implies follow-up integration into concrete agent memory-store behavior or a generic storage seam.

- Add health checks, IAM, billing, monitoring, logging, scheduler, Cloud Run, Artifact Registry, and Secret Manager support.
  - All net-new under the proposed GCP package.
  - Some of these are operational concerns not currently represented anywhere else in the repo, so new CLI, tests, and config persistence will be required.

- Preserve codebase conventions:
  - Use dataclasses for typed persisted/config objects.
  - Keep pure command-builders separate from execution.
  - Emit deterministic JSON in CLI commands where possible.
  - Keep provider methods thin and testable.
  - Avoid embedding live SDK-specific logic directly into CLI handlers.

Blast radius:

- `harnessiq/cli/main.py` for top-level registration.
- Net-new `harnessiq/cli/gcloud/` package or equivalent.
- Net-new `harnessiq/providers/gcloud/` tree.
- Net-new tests across providers and CLI.
- Possible follow-up touches to runtime memory abstractions if Cloud Storage persistence is implemented end-to-end rather than only as a provider surface.

### 1c: Assumption & Risk Inventory

Key assumptions surfaced by the design docs versus the live codebase:

1. The design assumes a deployment-oriented GCP config lifecycle (`GcpAgentConfig`) separate from the existing harness profile system. That is not inherently wrong, but it creates a second persisted configuration model in the repo.
2. The design assumes raw local environment discovery for credentials, while the current repo generally treats repo-local `.env` plus persisted field bindings as the canonical credential flow for harnesses.
3. The design assumes agent module identity is available from saved deployment config (`HARNESSIQ_AGENT_MODULE`), but the current codebase already has manifest metadata that may be a more stable source of harness identity.
4. The design assumes `harnessiq gcloud ...` should be a dedicated top-level command family rather than an extension of the existing platform-first CLI.
5. The design assumes Cloud Storage-backed cross-run memory persistence is in scope for this implementation, but the current agents do not yet expose a generic persistence hook where that provider can be plugged in without additional design work.

Primary implementation risks:

1. Command-surface duplication risk: adding a full `gcloud` command family may duplicate concepts already handled by `prepare`, `show`, `run`, `resume`, and `credentials`.
2. Credential-source-of-truth risk: if the bridge reads directly from `os.environ`, it may bypass the repo’s current persisted credential-binding system and create two competing local credential workflows.
3. Memory-integration risk: implementing `CloudStorageProvider` alone does not solve scheduled run continuity unless actual harness memory stores or the base agent runtime are wired to use it.
4. Workflow risk: the requested skill workflow requires sequential PR creation, merge into `main`, and then starting the next dependent ticket. That cannot proceed cleanly without an agreed merge cadence during this session.
5. Repository-state risk: the current checkout is on a feature branch with unrelated local files. Later worktree sync and `main` reconciliation steps must avoid overwriting user state.

Unresolved ambiguities that materially affect implementation:

1. Whether the new GCP system should integrate with the existing repo-local credential binding system or intentionally introduce a separate environment-variable discovery path.
2. Whether Cloud Storage memory persistence is expected to be fully wired into concrete harness runtime behavior in this pass, or only introduced as a provider/CLI surface.
3. Whether the user wants strict adherence to the skill’s one-ticket-per-PR/merge sequence, which would require pauses for merges between dependent tickets.
4. Whether the new GCP deployment flow should target all harnesses generically via manifests/adapters, or only a narrower subset first.
5. Whether JSON-emitting argparse CLI conventions should override the doc’s more human-oriented Click-style examples.

Phase 1 complete
