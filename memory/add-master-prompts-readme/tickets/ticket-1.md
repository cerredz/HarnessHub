Title: Add a master prompt package README and enforce catalog coverage

Intent: Document `harnessiq/master_prompts/` as the repository location for HarnessIQ master plans and make the bundled prompt inventory visible in-package, while preventing future prompt additions from skipping the README update.

Scope: Create one new README under `harnessiq/master_prompts/`, populate it with the current bundled prompt titles and descriptions, and extend prompt tests so the README must contain every bundled prompt title and description. Do not change prompt-loading code, prompt JSON assets, CLI behavior, or generated repository artifacts.

Relevant Files:

- `harnessiq/master_prompts/README.md`: new package README describing the directory and documenting the bundled prompt catalog.
- `tests/test_master_prompts.py`: regression coverage ensuring the README stays aligned with bundled prompt metadata.
- `memory/add-master-prompts-readme/*`: workflow artifacts for internalization, verification, and critique.

Approach: Use the live prompt JSON metadata as the source for the README catalog and add a focused test that reads the README and asserts each bundled prompt title and description appears there. This keeps the request implemented as documentation plus a durable drift guard.

Assumptions:

- `harnessiq/master_prompts/prompts/*.json` remains the source-of-truth prompt inventory.
- A README-level catalog is sufficient for the user's request; no CLI or generator changes are required.
- Generated docs such as `artifacts/file_index.md` should remain untouched.

Acceptance Criteria:

- [ ] `harnessiq/master_prompts/README.md` exists.
- [ ] The README states that `harnessiq/master_prompts/` is the repository location containing HarnessIQ master plans.
- [ ] The README includes every current bundled prompt title and description.
- [ ] `tests/test_master_prompts.py` fails if a bundled prompt title or description is missing from the README.
- [ ] Focused master prompt tests pass after the change.

Verification Steps:

- Run `python -m pytest tests/test_master_prompts.py tests/test_master_prompts_cli.py tests/test_master_prompt_session_injection.py`.
- Manually inspect `harnessiq/master_prompts/README.md` to confirm the overview text and prompt catalog are readable.

Dependencies: None.

Drift Guard: This ticket must stay documentation-focused. Do not refactor the prompt registry, rewrite prompt JSON metadata, or modify generated repository artifacts. The only code change beyond the README should be the minimum regression coverage needed to keep the README synchronized with the bundled prompt catalog.
