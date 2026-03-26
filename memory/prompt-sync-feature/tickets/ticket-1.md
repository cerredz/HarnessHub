# Ticket 1: Migrate master prompts to repository artifacts and generate the sync registry

## Title
Migrate master prompts to `artifacts/prompts/` and generate `registry.json`

## Intent
Establish the repository itself, not packaged JSON prompt assets, as the authoritative source of truth for HarnessHub master prompts. This ticket creates the canonical prompt layout required by Prompt Sync and adds the generator path that keeps the machine-readable registry aligned with the actual prompt files.

## Scope
Changes:
- Create `artifacts/prompts/` as the canonical prompt store using one Markdown file per harness
- Migrate the current bundled prompt payloads from `harnessiq/master_prompts/prompts/*.json` into repository Markdown files under `artifacts/prompts/`
- Add a deterministic registry generator that scans `artifacts/prompts/` and writes `artifacts/prompts/registry.json`
- Update packaging and runtime references so prompt metadata is no longer sourced from bundled JSON package data
- Add tests covering registry generation and prompt-file discovery

Does not touch:
- Top-level sync command registration in `harnessiq/cli/main.py`
- Tool launch and injection behavior
- Clipboard behavior
- Interactive session execution and sticky-mode orchestration

## Relevant Files
- CREATE `artifacts/prompts/*.md` - canonical prompt Markdown files, one file per harness slug
- CREATE `artifacts/prompts/registry.json` - generated prompt catalog checked into the repo
- CREATE `scripts/generate_prompt_registry.py` - prompt registry generator for local use and CI reuse
- MODIFY `pyproject.toml` - remove obsolete bundled JSON package-data wiring and include any new shipped assets if still needed
- MODIFY `harnessiq/master_prompts/__init__.py` - rewrite public prompt API around repository artifacts or remove obsolete APIs as part of the replacement
- MODIFY `harnessiq/master_prompts/registry.py` - replace bundled JSON loading with artifact-backed loading logic or retire the module in favor of artifact-backed helpers
- DELETE `harnessiq/master_prompts/prompts/*.json` - remove superseded bundled prompt assets after migration is complete
- MODIFY `tests/test_master_prompts.py` - replace bundled-JSON assertions with artifact-backed prompt assertions
- CREATE `tests/test_prompt_registry_generator.py` - verify registry generation behavior and deterministic output

## Approach
Treat the current bundled JSON prompt files as migration input, not the long-term store. Convert each existing prompt into a verbatim Markdown file under `artifacts/prompts/`, preserving the slug as the filename stem. Generate `registry.json` by scanning these files, deriving the harness name from the filename, deriving a description from the existing prompt metadata where available, and producing deterministic ordering and timestamps. Keep the generator script explicit and idempotent so future CI can call the same implementation rather than duplicating registry logic in workflow YAML.

## Assumptions
- All current bundled prompt slugs should continue to exist after migration unless explicitly removed as dead product surface.
- Existing prompt JSON metadata contains enough information to derive the human-readable description field for `registry.json`.
- It is acceptable for `updated_at` to be sourced from git file history or file metadata if the exact desired source was not previously implemented; the generator will need one deterministic strategy.
- Replacing the bundled prompt system means downstream tests and docs should follow the new artifact source of truth rather than preserving backward compatibility with the removed JSON package data.

## Acceptance Criteria
- [ ] `artifacts/prompts/` exists and contains Markdown prompt files for the supported harness catalog
- [ ] `artifacts/prompts/registry.json` is generated deterministically from `artifacts/prompts/`
- [ ] The registry contains `name`, `description`, and `updated_at` fields for every prompt file
- [ ] The old bundled JSON prompt files are removed or made inert so they are no longer the source of truth
- [ ] Any surviving prompt-loading Python API reads from the repository artifact source rather than bundled JSON package data
- [ ] Tests cover prompt discovery and registry generation behavior

## Verification Steps
1. Run the registry generator and confirm it rewrites `artifacts/prompts/registry.json` without errors.
2. Run the prompt-registry tests and confirm they pass.
3. Run the broader prompt tests and confirm they now assert against artifact-backed behavior.
4. Manually inspect `artifacts/prompts/` and `artifacts/prompts/registry.json` for deterministic ordering and expected fields.

## Dependencies
None.

## Drift Guard
This ticket defines the source of truth and the registry only. It must not introduce install/update/session launch behavior, tool-specific command execution, clipboard handling, or sticky-mode session orchestration. Any temporary compatibility scaffolding should exist only to keep the codebase coherent during the migration and should not recreate the old bundled prompt workflow as a parallel system.

## Issue URL

https://github.com/cerredz/HarnessHub/issues/282

