Title: Add the `mission_driven` bundled master prompt

Intent: Add the user-supplied long-running mission prompt to the packaged master-prompt catalog so it can be listed, retrieved, and activated through the existing registry and CLI surfaces without changing registry behavior.

Scope:
- Create a new bundled prompt JSON asset keyed as `mission_driven`.
- Preserve the supplied prompt body exactly in the JSON `prompt` field.
- Update existing master-prompt catalog tests for the new prompt key.
- Do not change registry loading semantics, CLI command behavior, or session-injection logic unless verification proves it is necessary.

Relevant Files:
- `harnessiq/master_prompts/prompts/mission_driven.json` — new bundled prompt metadata and exact prompt body.
- `tests/test_master_prompts.py` — extend the expected prompt-key set to include `mission_driven`.
- `memory/add-master-prompt-mission-driven/*` — workflow artifacts for internalization, ticketing, quality, and critique.

Approach: Use the existing filename-derived prompt registry contract. Add one new JSON prompt file with required metadata fields (`title`, `description`, `prompt`) and keep the user-provided prompt text intact. Then update the hard-coded expected prompt-key set in the focused test module so the catalog assertions reflect the new bundle member. Verify via the focused master-prompt tests and CLI/session-injection tests that the registry-driven surfaces pick up the new prompt automatically.

Assumptions:
- The prompt key should be `mission_driven` because prompt keys are derived from filenames.
- The user’s “exactly as it is” requirement applies to the prompt body, not the required JSON metadata wrapper.
- The existing registry/CLI/session-injection implementation is sufficiently generic and should not require source changes beyond the new asset and catalog tests.

Acceptance Criteria:
- [ ] `harnessiq/master_prompts/prompts/mission_driven.json` exists with non-empty `title`, `description`, and `prompt` fields.
- [ ] The `prompt` field content matches the user-supplied prompt text exactly.
- [ ] `mission_driven` is returned by the bundled master-prompt catalog under the existing registry API.
- [ ] The focused master-prompt test suite passes after the change.
- [ ] No unrelated files are modified.

Verification Steps:
- Run the focused master-prompt tests in `tests/test_master_prompts.py`.
- Run CLI-focused tests in `tests/test_master_prompts_cli.py`.
- Run session-injection tests in `tests/test_master_prompt_session_injection.py`.
- Optionally smoke-check the registry/CLI by listing prompts and confirming `mission_driven` appears.

Dependencies: None.

Drift Guard: This ticket must stay limited to registering one new bundled prompt and aligning catalog tests. It must not refactor the prompt registry, redesign prompt metadata, alter activation semantics, or update unrelated generated docs just because a new prompt exists in the tree.
