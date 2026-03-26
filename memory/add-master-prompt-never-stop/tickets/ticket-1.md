Title: Add the `never_stop` bundled master prompt

Intent: Add the user-supplied autonomous never-stop execution prompt to the packaged master-prompt catalog so it can be listed, retrieved, and activated through the existing registry and CLI surfaces.

Scope:
- Create a new bundled prompt JSON asset keyed as `never_stop`.
- Preserve the supplied prompt body exactly in the JSON `prompt` field.
- Update prompt catalog tests that pin the expected bundled key set.
- Do not change registry loading semantics, CLI behavior, or session-injection logic unless verification proves it is necessary.

Relevant Files:
- `harnessiq/master_prompts/prompts/never_stop.json` — new bundled prompt metadata and exact prompt body.
- `tests/test_master_prompts.py` — extend the expected prompt-key set for the new catalog member.
- `memory/add-master-prompt-never-stop/source_prompt.md` — source-of-truth copy of the user-supplied prompt text for exactness verification.
- `memory/add-master-prompt-never-stop/*` — implementation artifacts for internalization, verification, and critique.

Approach: Follow the existing filename-derived prompt registry pattern. Add one new JSON file under the bundled prompt directory with the required `title`, `description`, and `prompt` fields, using `never_stop` as the filename-derived key. Preserve the prompt text exactly by treating `memory/add-master-prompt-never-stop/source_prompt.md` as the source-of-truth reference and verifying the JSON `prompt` payload matches it byte-for-byte after packaging. Update the prompt catalog tests to include the new key and run the focused master-prompt suites to confirm the registry, CLI, and session activation surfaces discover the new prompt automatically.

Assumptions:
- The user-approved naming direction is `never_stop`.
- The prompt body should remain exactly the supplied markdown text once loaded from the registry.
- The prompt belongs in the bundled master-prompt catalog rather than agent-specific prompt directories.

Acceptance Criteria:
- [ ] `harnessiq/master_prompts/prompts/never_stop.json` exists with non-empty `title`, `description`, and `prompt` fields.
- [ ] The `prompt` field content matches the text stored in `memory/add-master-prompt-never-stop/source_prompt.md`.
- [ ] `never_stop` is discoverable through the existing bundled prompt registry API.
- [ ] The focused master-prompt tests pass after the change.
- [ ] No unrelated files are modified.

Verification Steps:
- Run `python -m pytest tests/test_master_prompts.py`.
- Run `python -m pytest tests/test_master_prompts_cli.py tests/test_master_prompt_session_injection.py`.
- Smoke-check `list_prompt_keys()` and confirm `never_stop` is present.
- Compare `memory/add-master-prompt-never-stop/source_prompt.md` with the bundled JSON `prompt` field and confirm they match exactly.

Dependencies: None.

Drift Guard: This ticket must stay limited to adding one new bundled prompt plus the minimal catalog-test alignment required by the existing contract. It must not refactor the prompt registry, alter prompt activation semantics, or hand-edit generated repository artifacts unless verification shows the generator output changed.
