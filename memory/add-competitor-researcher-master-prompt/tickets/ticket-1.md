Title: Add the `competitor_researcher` bundled master prompt

Intent: Package the provided competitive content intelligence prompt as a first-class bundled master prompt so it can be listed, retrieved, and activated through the existing registry and CLI surfaces.

Scope:
- Add one new JSON prompt asset under `harnessiq/master_prompts/prompts/`.
- Preserve the supplied prompt body exactly.
- Update prompt catalog tests to recognize the new bundled key and validate its structure.
- Do not modify registry loading behavior, prompt activation semantics, or any harness runtime logic.

Relevant Files:
- `harnessiq/master_prompts/prompts/competitor_researcher.json` — new bundled prompt metadata plus exact prompt text.
- `tests/test_master_prompts.py` — expected prompt-key set and prompt-specific regression coverage.
- `memory/add-competitor-researcher-master-prompt/source_prompt.md` — verbatim source copy of the supplied prompt used to generate the bundled JSON.

Approach: Preserve the user-supplied prompt verbatim in a task-local source artifact, generate the packaged JSON asset from that source so the repo bundle stays exact, and extend the existing prompt catalog tests with the new key plus prompt-specific assertions that match the repository’s current testing style.

Assumptions:
- `competitor_researcher` is the correct key because `mission_driven` is already occupied.
- The prompt body should remain unchanged from the supplied text, including headings and markdown separators.
- Existing registry and CLI paths will pick up the new asset automatically because they enumerate prompt files dynamically.

Acceptance Criteria:
- [ ] `harnessiq/master_prompts/prompts/competitor_researcher.json` exists with non-empty `title`, `description`, and `prompt` fields.
- [ ] The bundled prompt’s `prompt` field matches the supplied prompt body exactly.
- [ ] `competitor_researcher` is returned by the master-prompt registry and public API.
- [ ] The focused master-prompt and docs-sync verification steps pass.
- [ ] No unrelated runtime files are modified.

Verification Steps:
- Run `pytest tests/test_master_prompts.py tests/test_master_prompts_cli.py tests/test_master_prompt_session_injection.py tests/test_docs_sync.py`.
- Run `python scripts/sync_repo_docs.py --check`.

Dependencies: None.

Drift Guard: Keep this ticket scoped to adding one new bundled prompt and updating the tests that explicitly track bundled prompts. Do not refactor the registry, do not change prompt activation behavior, and do not hand-edit generated docs unless the docs sync check proves they are stale.
