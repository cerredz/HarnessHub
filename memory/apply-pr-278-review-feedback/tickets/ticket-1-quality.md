## Stage 1: Static Analysis

No dedicated linter is configured in this repository. Used:

- `python -m compileall harnessiq/agents tests`

Result:
- Passed after the helper extraction and Instagram refactor.

## Stage 2: Type Checking

No standalone type checker is configured in this repository. Verified the changed modules compile cleanly and preserved explicit type annotations on the new helper interfaces and Instagram loop helpers.

## Stage 3: Unit Tests

Passed:

- `python -m unittest tests.test_agents_base tests.test_email_agent tests.test_exa_outreach_agent tests.test_instagram_agent tests.test_knowt_agent tests.test_leads_agent tests.test_linkedin_agent tests.test_prospecting_agent tests.test_research_sweep_agent tests.test_instagram_cli`

Notes:

- Added explicit Instagram prompt coverage to confirm the prompt now renders structured identity, goal, and checklist sections.
- The first verification attempt exposed a local shared-state race because two parallel test batches were both writing to `memory/agent_instances.json`. Re-ran the suite sequentially and it passed.

## Stage 4: Integration & Contract Tests

Passed:

- `python scripts/sync_repo_docs.py`
- `python -m unittest tests.test_harness_manifests tests.test_docs_sync.DocsSyncTests.test_generated_docs_are_in_sync`

Result:
- Generated docs stayed in sync after the helper-module additions and artifact refresh.

## Stage 5: Smoke & Manual Verification

Verified via passing tests and diff review that:

- PR `#278`'s Instagram ICP-rotation behavior still works on top of current `main`.
- The Instagram prompt now contains explicit Identity, Goal, and Action Checklist sections.
- `_run_instagram_loop()` now delegates one active-ICP iteration to a dedicated helper and includes short inline comments for the high-level steps.
- Each package under `harnessiq/agents/` with `agent.py` now has a sibling `helpers.py`.
- Repeated path/timestamp/text helpers now live in `harnessiq/agents/helpers.py`, while package-specific helpers moved into local helper modules.
- The branch diff stayed scoped to the agent/helper refactor, the Instagram prompt/test updates, and the regenerated file index.
