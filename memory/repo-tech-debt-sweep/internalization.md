### 1a: Structural Survey

Repository shape:

- `harnessiq/` is the shipped Python package. It is organized into `agents/`, `cli/`, `config/`, `integrations/`, `master_prompts/`, `providers/`, `shared/`, `tools/`, `toolset/`, and `utils/`.
- `tests/` contains a broad unit/integration-style test suite, mostly `unittest` classes with some `pytest` usage.
- `docs/` contains lightweight usage docs for runtime, tools, LinkedIn, and output sinks.
- `artifacts/` contains architecture-maintenance docs, especially `file_index.md`.
- `memory/` contains prior planning artifacts and agent runtime state; it is large and contains both engineering notes and durable browser/agent memory. It is not part of the shipped package.

Technology stack:

- Python 3.11+ package managed through `pyproject.toml` and `setuptools`.
- Standard-library heavy implementation style: `argparse`, `dataclasses`, `pathlib`, `urllib`, `json`, `unittest`.
- No configured lint/type-check tool in `pyproject.toml`.
- Test runner is `pytest`, but the repository root also contains local runtime directories (`Lib/`, `.venv/`, `.worktrees/`) that affect discovery when pytest is run from the repo root.

Architecture:

- Runtime core:
  - `harnessiq/shared/agents.py` defines provider-agnostic agent dataclasses/protocols.
  - `harnessiq/agents/base/agent.py` implements the generic tool-using loop, transcript handling, compaction hooks, and audit-ledger emission.
  - concrete harnesses live under `harnessiq/agents/<agent>/`.
- Tools:
  - canonical tool constants/types live in `harnessiq/shared/tools.py`.
  - executable tool implementations live in `harnessiq/tools/`.
  - `harnessiq/tools/registry.py` is the deterministic execution registry for concrete `RegisteredTool` objects.
  - `harnessiq/toolset/` is the catalog/discovery layer that resolves tools by key/family.
- Providers:
  - `harnessiq/providers/base.py` and `harnessiq/providers/http.py` provide common request translation and transport helpers.
  - individual providers live in `harnessiq/providers/<provider>/`.
  - provider-backed output sink clients live in `harnessiq/providers/output_sinks.py`.
- CLI:
  - `harnessiq/cli/main.py` wires top-level subcommands.
  - agent-specific command modules repeat a common pattern: prepare/configure/show/run around file-backed memory stores.
- Shared data:
  - `harnessiq/shared/*.py` holds agent-specific memory-store models, constants, and normalization helpers.
- Utilities:
  - `harnessiq/utils/agent_ids.py` and `agent_instances.py` support stable instance identity.
  - `harnessiq/utils/ledger.py` currently mixes ledger models, sink implementations, connection persistence, sink-spec parsing, report/export helpers, and home-directory utilities in one large module.

Data flow:

- Agent run path:
  - CLI or SDK constructs agent config and tool executor.
  - `BaseAgent.run()` builds a provider-agnostic `AgentModelRequest`.
  - model adapter returns `AgentModelResponse`.
  - tool calls execute through `ToolRegistry` or equivalent executor.
  - terminal result is emitted and a ledger entry is written through default or injected output sinks.
- Provider tool path:
  - tool factory builds `RegisteredTool`.
  - tool handler normalizes args and invokes provider client/request builder.
  - provider transport uses `request_json()` and request translators in `providers/base.py`.
- Memory-backed agent path:
  - CLI writes text/json config files into per-agent memory folders.
  - agent `load_parameter_sections()` rehydrates those files into durable context window sections.

Test strategy:

- Many focused tests around providers, CLI modules, shared stores, agents, and tool registries.
- Packaging smoke tests exist in `tests/test_sdk_package.py`.
- Tests currently assume callers target `tests/` directly or otherwise avoid repo-local runtime directories.

Conventions:

- Public constants and aliases are centralized in `harnessiq/shared/*.py`.
- Dataclasses with `slots=True` and frozen data models are used heavily.
- CLI output is JSON for machine-readable commands.
- Memory stores are deterministic and file-backed.
- Tool keys follow `family.operation` naming.

Codebase inconsistencies observed:

- Public aggregator modules (`harnessiq/tools/__init__.py`, `harnessiq/tools/reasoning/__init__.py`, `harnessiq/agents/__init__.py`, `harnessiq/utils/__init__.py`) are maintained manually and already show drift/duplication.
- `harnessiq/shared/tools.py` contains duplicate assignments for brainstorming constants, which diverge from the newer reasoning implementation/tests.
- `harnessiq/cli/*/commands.py` repeats the same helper logic for JSON emission, agent-memory path resolution, text-or-file input handling, and runtime assignment parsing.
- `harnessiq/utils/ledger.py` bundles several unrelated responsibilities into a single nearly 1,000-line module.
- Running `.venv\Scripts\pytest.exe -q` from the repo root currently collects `Lib/site-packages` tests and fails before project tests complete.
- The current working tree is dirty on `feature/agent-audit-ledger-sinks`, so any new implementation work needs isolation from user changes.

### 1b: Task Cross-Reference

Task requirements mapped to the repo:

- “Go through repo”:
  - relevant across the full shipped package: `harnessiq/`, `tests/`, `docs/`, `artifacts/`.
  - irrelevant/noisy directories for survey purposes: `.git/`, `.venv/`, `Lib/`, `Scripts/`, `.worktrees/`, runtime `memory/` payloads.
- “Look for pieces of tech debt and ways to make the codebase more readable and maintainable”:
  - strongest maintainability hotspots found in public aggregation/export surfaces, duplicated CLI helpers, and monolithic utility modules.
  - repo-level test execution brittleness is also a maintainability problem, but that area is already represented by existing open issue/PR work.
- “Create an issue on GitHub for each of these”:
  - must use `gh issue create`.
  - to avoid duplicate issue noise, I should only create new issues for untracked debt and explicitly note already-tracked debt found during the survey.
- “For each issue implement a solution and create a PR for each”:
  - must use isolated worktrees/branches.
  - must avoid touching the user’s current uncommitted changes.
  - likely base each worktree off `origin/main`, not the dirty local branch.
- Artifact `artifacts/file_index.md`:
  - should be refreshed during the survey so it reflects the current repo shape and the specific maintainability hotspots discovered.

Concrete code areas implicated by the likely ticket set:

- CLI deduplication:
  - `harnessiq/cli/linkedin/commands.py`
  - `harnessiq/cli/instagram/commands.py`
  - `harnessiq/cli/prospecting/commands.py`
  - `harnessiq/cli/exa_outreach/commands.py`
  - `harnessiq/cli/ledger/commands.py`
  - likely a new shared CLI helper module under `harnessiq/cli/`
  - tests: CLI command suites for the touched modules
- Ledger modularization:
  - `harnessiq/utils/ledger.py`
  - `harnessiq/utils/__init__.py`
  - ledger/output-sink tests and CLI tests
- Survey artifact/documentation:
  - `artifacts/file_index.md`
  - task planning files under `memory/repo-tech-debt-sweep/`

Existing tracked debt discovered during the survey that should not be re-filed:

- Issue/PR around broken pytest baseline on refreshed main: GitHub issue `#203`, PR `#204`.
- Issue/PR around ExaOutreach run storage / CLI compatibility: GitHub issue `#199`, PR `#201`.
- Open reasoning/export cleanup issues already cover the duplicated reasoning package state and top-level toolset export gaps: `#100`, `#102`, `#110`, `#180`.

### 1c: Assumption & Risk Inventory

Assumptions:

- I can use `gh` to create issues and PRs directly; verified authenticated.
- The correct PR base branch for new cleanup work is `main`/`origin/main`, not the dirty local feature branch.
- Avoiding duplicate GitHub issues is preferable to mechanically re-filing debt that already has an open issue/PR.
- The user wants implementation work for a bounded set of high-signal debt items rather than every possible cleanup idea in the repository.

Risks:

- The current working tree contains many user changes and untracked runtime directories. Any work done in the root checkout risks mixing with those changes.
- Existing open PRs may already be modifying adjacent files, especially in CLI/runtime/export areas, so cherry-pick conflicts are possible if I choose overlapping tickets.
- Refactoring CLI helpers across multiple command modules can create behavior drift unless existing command tests are kept green.
- Splitting `harnessiq/utils/ledger.py` needs a compatibility-preserving facade so public imports from `harnessiq.utils` do not break.
- Updating `artifacts/file_index.md` in the root checkout will add another local modification in an already dirty tree; this is acceptable as a task artifact but should not be confused with ticket implementation branches.

Execution decision:

- Proceed without clarification.
- Create new GitHub issues only for untracked, concrete, bounded maintainability work.
- Use `origin/main` as the implementation base for worktrees to avoid carrying the dirty local branch forward.

Phase 1 complete
