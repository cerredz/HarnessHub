## Self-Critique

Initial review found one documentation gap: the first README draft listed every title and description, but it did not explicitly say that the catalog was the combined live metadata inventory. That wording mattered because the user asked for a combination of all prompt titles and descriptions.

Improvement applied:

- Added a sentence under `## Bundled Prompt Catalog` clarifying that the table combines the live title and description metadata from every bundled prompt JSON file.
- While rebasing the change onto the latest `origin/main` for PR creation, updated the README catalog to include the newly added `competitor_researcher` prompt after the drift-guard test exposed the omission.

Additional review outcomes:

- Keeping the change scoped to README plus a regression test is the simplest correct solution; a generator or runtime code path would have been unnecessary scope growth.
- The README drift guard belongs in `tests/test_master_prompts.py` because future prompt additions already touch that suite.
- Leaving `artifacts/file_index.md` untouched is correct because it is generator-owned.

Post-critique verification:

- Re-ran `python -m pytest tests/test_master_prompts.py tests/test_master_prompts_cli.py tests/test_master_prompt_session_injection.py`.
- Result: 71 passed.
