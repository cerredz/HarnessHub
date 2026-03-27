Title: Add the `orchestrator_master_prompt` bundled master prompt
Issue URL: https://github.com/cerredz/HarnessHub/issues/348
Intent: Add the user-provided orchestrator master prompt to the bundled prompt catalog so it can be retrieved through the SDK, CLI, and prompt session injection workflow like the existing curated prompts.
Scope: Create one new prompt JSON asset under `harnessiq/master_prompts/prompts/`, update the prompt catalog regression tests for the new bundled key and nonstandard section shape, and write workflow artifacts under `memory/add-orchestrator-master-prompt/`. Do not refactor the prompt registry, prompt activation helpers, CLI wiring, or unrelated bundled prompt assets.
Relevant Files:
- `harnessiq/master_prompts/prompts/orchestrator_master_prompt.json`: new bundled prompt asset containing the exact user-provided prompt body with repository-standard metadata fields.
- `tests/test_master_prompts.py`: extend the expected prompt key set, exclude the new prompt from the standard section layout set, and add prompt-specific assertions for `orchestrator_master_prompt`.
- `memory/add-orchestrator-master-prompt/source_prompt.md`: exact source prompt body preserved before JSON wrapping.
- `memory/add-orchestrator-master-prompt/tickets/ticket-1.md`: this ticket definition.
Approach: Use the existing file-driven prompt registry exactly as designed by adding a single new JSON file to the prompts package. Preserve the provided prompt body in a task-local artifact and in the JSON `prompt` field, infer only the required title and description metadata, and update `tests/test_master_prompts.py` so the new asset is part of the expected bundled catalog and receives direct structure and content assertions tailored to its `Identity / Persona` heading format.
Assumptions:
- The inferred key `orchestrator_master_prompt` is acceptable for the bundled catalog.
- The title `Orchestrator Master Prompt` and a concise description are sufficient metadata wrappers around the exact prompt body.
- The provided prompt text is intended to be added verbatim rather than normalized into the repository's more common `Identity` heading format.
- Existing prompt catalog tooling will pick up the new file automatically without separate registration.
Acceptance Criteria:
- [ ] `MasterPromptRegistry().list()` includes `orchestrator_master_prompt`.
- [ ] `harnessiq/master_prompts/prompts/orchestrator_master_prompt.json` contains non-empty `title`, `description`, and `prompt` fields.
- [ ] The `prompt` field preserves the provided prompt body exactly apart from JSON escaping.
- [ ] `tests/test_master_prompts.py` includes `orchestrator_master_prompt` in the expected bundled prompt key set.
- [ ] `tests/test_master_prompts.py` validates the new prompt's `Identity / Persona`-style section ordering and key requested phrases.
- [ ] Focused prompt tests pass for the updated catalog.
- [ ] Prompt registry, CLI, and session injection surfaces continue to load the bundled catalog successfully after the addition.
Verification Steps:
- Run `python -m pytest tests/test_master_prompts.py tests/test_master_prompts_cli.py tests/test_master_prompt_session_injection.py`.
- Run `python -c "from harnessiq.master_prompts import get_prompt; prompt = get_prompt('orchestrator_master_prompt'); print(prompt.title); print(prompt.prompt.splitlines()[0])"`.
- Confirm the prompt body still matches `memory/add-orchestrator-master-prompt/source_prompt.md`.
Dependencies: None.
Drift Guard: This ticket must stay additive. Do not refactor the prompt registry, do not rewrite existing prompt assets, do not normalize the user-provided prompt body into a different style, and do not stage or revert unrelated dirty-worktree changes.
