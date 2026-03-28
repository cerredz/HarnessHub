Title: Replace the Knowt prompt examples placeholder with the provided examples corpus

Intent: Populate the Knowt agent's examples section with the user-supplied script corpus so the master prompt contains concrete reference material instead of a placeholder TODO.

Scope:
- Update the `## Example Knowt TikTok Scripts` section in the Knowt master prompt.
- Preserve the rest of the prompt structure and other TODO sections.
- Verify the prompt still loads through the existing Knowt agent tests.
- Do not change agent code, tool registration, or memory-store behavior.

Relevant Files:
- `harnessiq/agents/knowt/prompts/master_prompt.md` - replace the placeholder examples block with the provided numbered examples.
- `tests/test_knowt_agent.py` - verification target only; no source changes expected.
- `memory/add-knowt-master-prompt-examples/*` - task artifacts for internalization, ticketing, quality, and critique.

Approach: Edit the single Markdown prompt file in place by removing the current TODO guidance under the examples heading and inserting the exact examples block supplied by the user. Keep all surrounding sections intact so the prompt contract exercised by the existing tests remains unchanged. Validate by running the focused Knowt agent test module.

Assumptions:
- The provided examples should appear exactly as supplied, including numbering gaps and empty entries.
- The placeholder examples instructions are no longer needed once the real examples corpus is inserted.
- Existing tests provide sufficient regression coverage for this content-only change.

Acceptance Criteria:
- [ ] `harnessiq/agents/knowt/prompts/master_prompt.md` contains the provided `<Examples>` block under `## Example Knowt TikTok Scripts`.
- [ ] The prior placeholder TODO text for that section is removed.
- [ ] All other prompt sections remain present.
- [ ] `tests/test_knowt_agent.py` passes after the change.
- [ ] No unrelated runtime code is modified.

Verification Steps:
- Run `python -m pytest tests/test_knowt_agent.py`.
- Manually inspect the Knowt prompt file to confirm the examples section contains the provided numbered block and surrounding sections remain intact.

Dependencies: None.

Drift Guard: This ticket must remain a prompt-content update only. It must not refactor the Knowt agent, add new tests for the examples corpus, or edit unrelated prompt sections beyond what is required to replace the placeholder examples block cleanly.
