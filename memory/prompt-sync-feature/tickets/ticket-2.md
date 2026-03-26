# Ticket 2: Build the shared Prompt Sync runtime, config, cache, and shim generation

## Title
Build the shared Prompt Sync runtime for config, cache, fetch, and shim generation

## Intent
Create the reusable infrastructure behind Prompt Sync so the CLI can resolve tool contracts, fetch prompt text from the canonical repository source, cache it safely, and install/update static discovery shims without duplicating platform-specific logic across commands.

## Scope
Changes:
- Create the `harnessiq/cli/sync/` package and the shared runtime modules required by `install`, `update`, and `list`
- Create the `harnessiq/master_prompts/injections/` helper package requested in the design doc for tool-specific prompt/instruction utilities
- Implement user-home config loading and creation at `~/.harnessiq/config.toml`
- Implement prompt cache layout and TTL handling under `~/.harnessiq/cache/`
- Implement GitHub raw fetch logic, registry fetch logic, and cache fallback behavior
- Implement per-tool shim template generation and target path resolution for Claude, Codex, Gemini, and OpenCode
- Implement `harnessiq install`, `harnessiq update`, and `harnessiq list`

Does not touch:
- Interactive session launch and `os.execvp` handoff
- Sticky-mode temp-file orchestration
- Legacy command removal and final docs cleanup

## Relevant Files
- CREATE `harnessiq/cli/sync/__init__.py` - re-export sync command registration
- CREATE `harnessiq/cli/sync/fetch.py` - registry fetch, prompt fetch, cache read/write, TTL logic, and error handling
- CREATE `harnessiq/cli/sync/shim.py` - tool target metadata, shim templates, and install/update rendering
- CREATE `harnessiq/cli/sync/install.py` - `harnessiq install`
- CREATE `harnessiq/cli/sync/update.py` - `harnessiq update`
- CREATE `harnessiq/cli/sync/list_.py` - `harnessiq list`
- CREATE `harnessiq/cli/sync/clipboard.py` - platform clipboard abstraction and fallback handling
- CREATE `harnessiq/master_prompts/injections/__init__.py` - re-export injection helpers
- CREATE `harnessiq/master_prompts/injections/contracts.py` - current per-tool contract metadata such as binary names, startup strategy, and supported sticky-mode behavior
- CREATE `harnessiq/master_prompts/injections/paths.py` - home-directory target resolution for skills, rules, and config files
- CREATE `harnessiq/master_prompts/injections/files.py` - helper functions for writing managed files and generated temp assets
- MODIFY `harnessiq/cli/main.py` - register the new top-level sync commands
- CREATE `tests/test_prompt_sync_fetch.py` - cache, TTL, registry, and error-handling coverage
- CREATE `tests/test_prompt_sync_install_update.py` - install/update/list coverage including dry-run and path selection

## Approach
Keep the sync runtime small and composable. `fetch.py` should own the network and cache concerns, `shim.py` should own all static template rendering and tool-target metadata that is stable across commands, and the top-level command modules should stay thin. Put the higher-churn tool contract details behind a dedicated helper layer in `harnessiq/master_prompts/injections/` so `session.py` can reuse the same platform metadata later. Create config defaults lazily and never overwrite a user-edited config file during `update`. For install/update, prefer documented native paths when verified and local-environment-backed paths where official docs are absent.

## Assumptions
- The default cache TTL is 3600 seconds unless overridden in config.
- The runtime may use standard-library HTTP primitives if no additional dependency is introduced.
- OpenCode and Codex shim placement can rely on verified local paths plus current tool docs and environment findings captured during clarification.
- The root-level `harnessiq list` command should be dedicated to Prompt Sync harness discovery even though it is a generic command name.

## Acceptance Criteria
- [ ] `harnessiq install` is registered at the top level and supports `--target`, `--all`, `--dry-run`, and `--force`
- [ ] `harnessiq update` is registered at the top level and supports `--target`, `--all`, `--harness`, `--clear-cache`, and `--dry-run`
- [ ] `harnessiq list` is registered at the top level and returns the registry in human-readable or JSON form
- [ ] Config defaults are created lazily in `~/.harnessiq/config.toml`
- [ ] Prompt cache files and metadata files are written and reused according to TTL rules
- [ ] Install/update generate the correct shim files for each supported target and respect dry-run/idempotency semantics
- [ ] Tests cover fetch, cache fallback, install, update, and list behavior

## Verification Steps
1. Run the sync fetch and install/update tests.
2. Run a dry-run install for each target and confirm the reported paths and file contents match the current tool contracts.
3. Run a dry-run update with and without `--clear-cache` and confirm cache invalidation behavior is reported correctly.
4. Run `harnessiq list --json` and confirm the output matches `artifacts/prompts/registry.json`.

## Dependencies
- Ticket 1 must land first because the fetch and list runtime depend on the canonical prompt and registry artifacts.

## Drift Guard
This ticket provides the shared runtime and the non-session commands only. It must not attempt to launch interactive tool sessions, replace the current process with `os.execvp`, or implement sticky-mode workspace mutation. The only platform-specific logic allowed here is contract metadata, shim generation, and path resolution needed by install/update/list.

## Issue URL

https://github.com/cerredz/HarnessHub/issues/283

