# Ticket 4: Remove the legacy prompt workflow, update docs, and land full verification coverage

## Title
Remove the legacy bundled prompt workflow and update docs and tests for Prompt Sync

## Intent
Finish the migration by deleting or repointing the old prompt surface, aligning all tests and generated docs with the new top-level Prompt Sync commands, and ensuring the repository no longer documents or ships the superseded bundled-prompt model.

## Scope
Changes:
- Remove the legacy `harnessiq prompts` command family and any obsolete prompt-session overlay helpers that only supported the old workflow
- Remove or rewrite old prompt tests so they validate the new Prompt Sync behavior instead of bundled JSON prompts
- Update narrative docs to describe `install`, `update`, `session`, and `list`
- Regenerate `README.md`, `artifacts/commands.md`, and `artifacts/file_index.md`
- Run the full relevant quality pipeline for the completed feature

Does not touch:
- New prompt source files or registry generator semantics beyond documentation and final cleanup
- Core fetch/cache/shim/session behavior already implemented in the preceding tickets

## Relevant Files
- DELETE `harnessiq/cli/master_prompts/commands.py` - remove the superseded bundled-prompt CLI surface or replace it with a compatibility stub if required during final cleanup
- DELETE `harnessiq/cli/master_prompts/__init__.py` - remove obsolete package exports if no longer needed
- DELETE or MODIFY `harnessiq/master_prompts/session_injection.py` - remove obsolete repo-local activation overlay logic if it no longer serves the new system
- MODIFY `tests/test_master_prompts_cli.py` - replace legacy command assertions with Prompt Sync command assertions or delete if fully superseded
- MODIFY `tests/test_master_prompt_session_injection.py` - replace or remove tests for the removed activation overlay behavior
- MODIFY `docs/master-prompt-session-injection.md` - rewrite around Prompt Sync or replace with a new sync-focused usage doc
- MODIFY `README.md` - regenerated command and usage references
- MODIFY `artifacts/commands.md` - regenerated CLI artifact
- MODIFY `artifacts/file_index.md` - regenerated architecture artifact
- MODIFY `tests/test_docs_sync.py` - update expectations only if required by the new live CLI surface

## Approach
Treat this as the migration-closure ticket. After the new sync runtime and session behavior exist, delete the old surface rather than keeping compatibility layers that undermine the user's explicit "do not coexist" decision. Let the live CLI source of truth drive the generated docs via `scripts/sync_repo_docs.py` rather than hand-editing the artifacts. Consolidate tests around the new top-level command surface and remove assertions that only made sense for the old package-bundled prompt model.

## Assumptions
- The user wants a clean replacement, so preserving the old `harnessiq prompts` surface is not required.
- It is acceptable for public Python prompt APIs to change if they were only supporting the superseded bundled workflow.
- Generated docs should be updated as part of the same migration, not deferred.

## Acceptance Criteria
- [ ] The old bundled prompt CLI surface is removed or made inert in favor of Prompt Sync
- [ ] Obsolete repo-local activation overlay helpers are removed if they are no longer part of the new architecture
- [ ] Tests no longer assert the superseded bundled prompt workflow
- [ ] Prompt Sync usage is documented in the narrative docs and reflected in generated artifacts
- [ ] `README.md`, `artifacts/commands.md`, and `artifacts/file_index.md` are regenerated and in sync
- [ ] The relevant test suite passes after the migration

## Verification Steps
1. Run the full prompt-sync-related test suite.
2. Run `python scripts/sync_repo_docs.py --check` and confirm generated docs are in sync.
3. Run a manual `harnessiq --help` and confirm the new top-level command surface is visible while the old prompt command family is gone or clearly deprecated.
4. Manually inspect docs to confirm Prompt Sync commands are the documented workflow.

## Dependencies
- Ticket 1, Ticket 2, and Ticket 3 must land first.

## Drift Guard
This ticket closes the migration and documentation loop. It must not reopen architectural decisions about prompt source of truth, invent new compatibility modes, or expand the feature beyond the approved Prompt Sync design. Any remaining behavior gaps discovered here should be documented as explicit follow-up work rather than smuggled into the cleanup ticket.

## Issue URL

https://github.com/cerredz/HarnessHub/issues/285

