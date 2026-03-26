# Prompt Sync Feature Internalization

### 1a: Structural Survey

#### Repository shape

- `harnessiq/` is the authoritative runtime package. The repo also contains generated docs in `artifacts/`, focused narrative docs in `docs/`, tests in `tests/`, and local task/runtime state in `memory/`.
- `harnessiq/cli/` is the top-level argparse surface. `harnessiq/cli/main.py` wires command families into the root parser. Existing command families follow a package-per-domain layout such as `linkedin/commands.py`, `leads/commands.py`, `master_prompts/commands.py`, and `models/commands.py`.
- `harnessiq/master_prompts/` currently owns prompt-related runtime logic. It contains:
  - `registry.py`: loads bundled prompt assets from package data.
  - `session_injection.py`: writes repo-local `.claude/CLAUDE.md`, `AGENTS.override.md`, and state metadata for project-scoped prompt activation.
  - `prompts/*.json`: packaged prompt assets with `title`, `description`, and `prompt` fields.
- `scripts/sync_repo_docs.py` statically inspects the CLI tree and other runtime modules to regenerate `README.md`, `artifacts/commands.md`, and `artifacts/file_index.md`.
- `tests/` includes focused CLI and master-prompt coverage:
  - `tests/test_master_prompts.py`
  - `tests/test_master_prompts_cli.py`
  - `tests/test_master_prompt_session_injection.py`
  - `tests/test_docs_sync.py`
  - `tests/test_cli_common.py`

#### Technology stack and packaging

- Language/runtime: Python 3.11+.
- Packaging: setuptools via `pyproject.toml`.
- CLI: standard-library `argparse`.
- Tests: `pytest` plus `unittest` style modules.
- Package data currently includes `harnessiq.master_prompts.prompts/*.json`.
- There is no dedicated third-party HTTP dependency in `pyproject.toml`; current prompt loading is local-package based rather than network based.

#### Current prompt data flow

1. `harnessiq.master_prompts.registry.MasterPromptRegistry` loads prompt JSON files bundled inside the package.
2. `harnessiq.cli.master_prompts.commands` exposes `harnessiq prompts list/show/text/activate/current/clear`.
3. `activate` writes repo-local instruction overlays through `harnessiq.master_prompts.session_injection`.
4. Claude Code and Codex then consume those repo-local files on fresh sessions.

This is materially different from the design doc’s proposed source of truth and launch flow:

- Current source of truth: packaged JSON under `harnessiq/master_prompts/prompts/`.
- Proposed source of truth: GitHub-hosted Markdown under `artifacts/prompts/`.
- Current activation model: repo-local overlay files for fresh sessions.
- Proposed activation model: fetched prompt text injected via tool-native startup flags or copied/printed on demand.

#### Configuration and local-state conventions

- `harnessiq` already uses JSON output for CLI responses where commands are machine-oriented (`emit_json` in `harnessiq/cli/common.py`).
- Repo-root resolution follows `resolve_repo_root(...)` in `harnessiq/cli/common.py`.
- Generated/local-only files are expected to live under hidden directories such as `.harnessiq/` and `.claude/`; the repo docs explicitly treat these as local/generated state.
- The design doc introduces a separate user-home config/cache root at `~/.harnessiq/`, which does not currently exist as a runtime subsystem inside the live package.

#### Test and docs strategy

- Tests assert parser registration, command output payloads, file side effects, and docs synchronization.
- `tests/test_docs_sync.py` enforces that generated docs remain aligned with live source after CLI changes.
- Because the docs generator inspects the CLI source tree, any top-level command additions will require regenerated `README.md`, `artifacts/commands.md`, and `artifacts/file_index.md`.

#### Observed conventions

- Modules are small and responsibility-scoped.
- CLI registration typically lives in `commands.py` plus a thin `__init__.py` re-export.
- Public modules expose narrow `__all__` lists.
- Files use type hints and docstrings consistently.
- Tests are behavior-oriented and usually call `main(argv)` directly instead of shelling out.

#### Notable inconsistencies or drift already present

- `artifacts/file_index.md` says the key CLI file is `harnessiq/cli/main.py`; `pyproject.toml` also points the console script at `harnessiq.cli.main:main`, but `harnessiq/cli/__main__.py` exists separately. This is consistent enough but worth keeping aligned.
- The repo currently has a local prompt feature named `harnessiq prompts`, while the design doc wants top-level commands `harnessiq install`, `harnessiq update`, `harnessiq session`, and `harnessiq list`. That is a surface-area replacement or expansion, not an additive internal refactor only.
- The checked-out worktree is already dirty in unrelated `harnessiq/agents/**` files and an unrelated `memory/` subtree. Those changes must be preserved and not reverted.

### 1b: Task Cross-Reference

#### Requested design mapped to current codebase

1. Top-level CLI commands
   - Design target: `harnessiq install`, `harnessiq update`, `harnessiq session`, `harnessiq list`.
   - Current code touchpoints:
     - `harnessiq/cli/main.py` must register the new top-level commands.
     - New command-family package is best added under `harnessiq/cli/sync/` per the design doc.
     - Existing `harnessiq/cli/master_prompts/` package is the closest related surface and may need to coexist, delegate, or be retired.

2. Shared sync implementation modules
   - Design target: `harnessiq/cli/sync/{install,update,session,list_,fetch,shim,clipboard}.py`.
   - Current code touchpoints:
     - New package/modules are net-new.
     - Reusable CLI helpers can come from `harnessiq/cli/common.py`.
     - New fetch/cache/config logic does not exist today and must be added.

3. Prompt storage migration to repository artifacts
   - Design target: canonical Markdown prompts under `artifacts/prompts/` and registry file `artifacts/prompts/registry.json`.
   - Current code touchpoints:
     - This is net-new repo structure.
     - Existing bundled JSON prompt assets under `harnessiq/master_prompts/prompts/` conflict with the proposed source of truth.
     - Existing prompt registry/loading APIs in `harnessiq/master_prompts/{__init__,registry.py}` would need either replacement, compatibility adapters, or explicit preservation for legacy callers/tests.

4. Local cache and config
   - Design target: `~/.harnessiq/cache/*.md`, `*.meta.json`, and `~/.harnessiq/config.toml`.
   - Current code touchpoints:
     - Net-new implementation.
     - No existing user-home prompt cache/config module exists.
     - New code will need path resolution, TOML parsing/writing, TTL evaluation, and cache invalidation behavior.

5. Shim generation and install/update behavior
   - Design target: write small static shim files into each tool’s discovery directory, without storing prompt text locally.
   - Current code touchpoints:
     - Net-new implementation, but it overlaps conceptually with `session_injection.py`.
     - The design doc specifically requests helper/utility files under a new `harnessiq/master_prompts/injections/` subfolder; those modules are net-new and would likely host path resolution, template fragments, temp-file lifecycle, or sticky-mode helpers.

6. Session launching and sticky mode
   - Design target: fetch prompt text, then launch target tool with the appropriate startup injection mechanism using `os.execvp`; optionally provide sticky mode via per-turn instruction files.
   - Current code touchpoints:
     - Current `session_injection.py` already knows how to write Claude/Codex instruction files, but it is repo-local and package-prompt based.
     - New session launch logic is net-new and belongs in `harnessiq/cli/sync/session.py`.
     - Sticky-mode temp workspace handling is net-new; this likely belongs in the requested `harnessiq/master_prompts/injections/` helpers.

7. Clipboard mode
   - Design target: copy fetched prompt text with platform-native clipboard utilities.
   - Current code touchpoints:
     - Net-new module `clipboard.py`.
     - Requires Windows/macOS/Linux branching; the current repo has no shared clipboard abstraction.

8. Registry/list command
   - Design target: fetch `registry.json` and print human or JSON output.
   - Current code touchpoints:
     - Could replace or parallel the current `harnessiq prompts list`.
     - New fetch layer is needed because the current list command is local-package based.

9. Documentation and generated artifacts
   - Required touchpoints:
     - `README.md`
     - `artifacts/commands.md`
     - `artifacts/file_index.md`
     - potentially `docs/master-prompt-session-injection.md`
   - Any command-surface change requires rerunning `python scripts/sync_repo_docs.py`.

10. Tests
   - Existing tests that will be impacted:
     - `tests/test_master_prompts.py`
     - `tests/test_master_prompts_cli.py`
     - `tests/test_master_prompt_session_injection.py`
     - `tests/test_docs_sync.py`
   - New tests will be needed for:
     - sync parser registration
     - install/update/session/list behavior
     - cache TTL and invalidation
     - shim template generation
     - sticky-mode file lifecycle
     - clipboard fallback behavior
     - exec-argument construction without actually replacing the test runner process

#### Environment findings relevant to implementation

- `gh` is installed and authenticated against `github.com/cerredz/HarnessHub`.
- Installed tool binaries on this machine:
  - `claude.exe`
  - `codex.ps1`
  - `gemini.ps1`
  - `opencode.exe`
- Local tool homes confirm:
  - `~/.claude/skills` exists.
  - `~/.codex/skills` exists.
  - `~/.codex/AGENTS.md` exists.
  - `~/.gemini` exists, but `~/.gemini/skills` does not currently exist.
  - `~/.opencode` does not currently exist.

#### Cross-reference against the draft’s specific platform assumptions

- Claude
  - Confirmed locally: `claude --append-system-prompt` exists.
  - Confirmed locally: `~/.claude/skills` exists.
  - Design assumption is plausible.

- Codex
  - Not confirmed locally: top-level `codex --instructions` does not exist in `codex --help`.
  - Confirmed locally: Codex has `~/.codex/skills` and a global `~/.codex/AGENTS.md`.
  - Confirmed locally: `codex exec [PROMPT]` accepts initial instructions as a positional prompt, and interactive `codex [PROMPT]` also accepts an initial prompt.
  - The draft’s startup-flag design for Codex does not match the installed CLI on this machine.

- Gemini
  - Not confirmed locally: `gemini --system-prompt` is not shown in `gemini --help`.
  - Confirmed locally: Gemini has a `skills` command family.
  - The draft’s startup-flag assumption is unverified and likely wrong for the installed CLI on this machine.

- OpenCode
  - Not confirmed locally: `opencode --system-prompt` is not shown in `opencode --help`.
  - Confirmed locally: OpenCode exposes `agent` management commands; no established `~/.opencode/skills` home is present on this machine.
  - The draft’s startup-flag and skill-directory assumptions are unverified for the installed CLI on this machine.

### 1c: Assumption & Risk Inventory

1. The design doc assumes a cross-tool startup-flag contract that is not true for the installed binaries on this machine.
   - Risk: implementing exactly as written will produce commands that fail for Codex, Gemini, or OpenCode.

2. The design doc assumes one canonical prompt store under `artifacts/prompts/`, but the live package and tests currently depend on packaged JSON prompt assets under `harnessiq/master_prompts/prompts/`.
   - Risk: a direct replacement could break the public Python API, package-data expectations, and the existing `harnessiq prompts` command family.

3. The design doc asks for top-level `harnessiq list`, which is a broad command name and would coexist with the existing `harnessiq models list`, `connections list`, etc.
   - Risk: while argparse allows this, the semantic shift from a root-level generic `list` to “list harnesses” is a product decision that should be explicit.

4. The design doc asks for `install` and `update` as top-level commands.
   - Risk: those names may be interpreted as package-install/update commands rather than prompt-sync commands unless their help text and docs are very explicit. They also create overlap with `claude install` and `claude update` concepts in user mental models.

5. Sticky mode is specified differently per tool, but only Claude/Codex have any concrete mechanism in the design doc.
   - Risk: implementing “best effort” sticky mode for Gemini/OpenCode without a verified per-turn instruction contract could create false confidence.

6. The draft claims “no local prompt storage,” while the cache architecture explicitly stores cached prompt Markdown under `~/.harnessiq/cache/`.
   - Risk: this is only consistent if “no manually maintained prompt files” is the intended meaning. The requirement wording and the architecture wording are slightly in tension.

7. The design doc describes `registry.json` as CI-generated on every push, but no such generator or CI workflow exists in the current repo state.
   - Risk: implementing a runtime feature that depends on `registry.json` without deciding who generates it will leave the repo in a partially wired state.

8. The design doc asks for `harnessiq/master_prompts/injections/` helper files in addition to `harnessiq/cli/sync/`.
   - Risk: it is not fully specified which responsibilities belong in the runtime prompt package versus the CLI sync package. Without an explicit boundary, logic may be split awkwardly.

9. The git worktree is already dirty in unrelated agent files.
   - Risk: any implementation must avoid touching or reverting those unrelated changes and should keep the write set isolated to prompt-sync files, tests, docs, and memory artifacts.

10. The `github-software-engineer` skill requires ticket drafting and GitHub issue creation before implementation.
    - Risk: if the user wants direct implementation in a single local branch without issue/PR workflow, that conflicts with the skill’s prescribed process and needs confirmation before Phase 3.

Phase 1 complete.
