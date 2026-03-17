# Ticket 3: Rename custom instructions, reorder context window, update tests

**Title:** Surface custom instructions cleanly and move applied jobs to first context window position

**Intent:** The user wants two specific UX improvements: (1) the "additional_prompt" concept should be surfaced as "custom instructions" in the CLI and context window so the interface matches user intent; (2) the applied jobs log should be the first parameter section injected into the context window so the agent sees its duplicate-prevention list immediately after the system prompt.

**Scope:**
- Renames `--additional-prompt-text/file` CLI flags to `--custom-instructions-text/file` in `commands.py`
- Renames context window section title from "Additional Prompt Data" to "Custom Instructions"
- Reorders `load_parameter_sections()` so "Jobs Already Applied To" is first
- Does NOT rename underlying file (`additional_prompt.md`), Python method names, or any data class
- Does NOT touch `custom_parameters.json` (unrelated to custom instructions)
- Updates tests to reflect new section order and renamed section title

**Relevant Files:**
- `harnessiq/cli/linkedin/commands.py` — rename CLI flags
- `harnessiq/agents/linkedin/agent.py` — reorder sections, rename title
- `tests/test_linkedin_agent.py` — update expected section order and title

**Approach:**
In `_add_text_or_file_options` calls in `register_linkedin_commands()`, change the field name `"additional_prompt"` to `"custom_instructions"` which changes the generated flags to `--custom-instructions-text/file`. Update the `_handle_configure` function to use `args.custom_instructions_text` and `args.custom_instructions_file`. The store method `write_additional_prompt()` is still called internally (no rename there).

In `load_parameter_sections()`, move the "Jobs Already Applied To" section to be built and appended first (index 0), before "Job Preferences" and "User Profile".

Change the section title from `"Additional Prompt Data"` to `"Custom Instructions"` in `load_parameter_sections()`.

**Assumptions:**
- No users have scripts depending on the `--additional-prompt-text/file` CLI flags (SDK is in active development)
- Underlying file `additional_prompt.md` stays unchanged so any existing persisted content is preserved
- Tests need the order update: applied jobs should be first in the sections list

**Acceptance Criteria:**
- [ ] `harnessiq linkedin configure --custom-instructions-text "..."` works and writes to `additional_prompt.md`
- [ ] `harnessiq linkedin configure --custom-instructions-file path/to/file` works
- [ ] `--additional-prompt-text/file` flags no longer exist (not kept as aliases)
- [ ] `load_parameter_sections()` returns sections where index 0 is "Jobs Already Applied To"
- [ ] Section title is "Custom Instructions" (not "Additional Prompt Data")
- [ ] All existing tests pass; updated tests verify new order and title

**Verification Steps:**
1. `python -m pytest tests/test_linkedin_agent.py -v`
2. `python -m pytest tests/ -v` — full suite must pass
3. Manual: `harnessiq linkedin configure --agent test --custom-instructions-text "Prefer companies in NYC"` → verify `additional_prompt.md` is written

**Dependencies:** Ticket 2 (load_parameter_sections must include Job Search Config in correct position)

**Drift Guard:** Does not rename any Python method or memory file. Does not touch `custom_parameters.json` (a separate concept). Does not change any behavior other than section ordering and CLI flag names.
