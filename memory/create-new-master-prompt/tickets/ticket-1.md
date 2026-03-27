Title: Add the `cognitive_multiplexer` bundled master prompt
Issue URL: https://github.com/cerredz/HarnessHub/issues/305
Intent: Add the user-provided cognitive multiplexer master prompt to the bundled prompt catalog so it can be retrieved through the SDK, CLI, and prompt session injection workflow like the existing curated prompts.
Scope: Create one new prompt JSON asset under `harnessiq/master_prompts/prompts/`, update the prompt catalog regression tests for the new bundled key, and write workflow artifacts under `memory/create-new-master-prompt/`. Do not refactor the prompt registry, session injection helpers, CLI wiring, or unrelated prompt assets.
Relevant Files:
- `harnessiq/master_prompts/prompts/cognitive_multiplexer.json`: new bundled prompt asset containing the exact user-provided prompt body with repository-standard metadata fields.
- `tests/test_master_prompts.py`: extend the expected prompt key set and add prompt-specific assertions for `cognitive_multiplexer`.
- `memory/create-new-master-prompt/internalization.md`: Phase 1 repository survey and task mapping.
- `memory/create-new-master-prompt/clarifications.md`: recorded assumption resolution for the inferred prompt metadata.
- `memory/create-new-master-prompt/tickets/index.md`: ticket index and later issue/PR bookkeeping.
- `memory/create-new-master-prompt/tickets/ticket-1.md`: this ticket definition.
Approach: Use the existing file-driven prompt registry exactly as designed by adding a single new JSON file to the prompts package. Preserve the provided prompt body verbatim in the `prompt` field, infer only the required catalog metadata, and update `tests/test_master_prompts.py` so the new asset is part of the expected prompt catalog and receives at least one direct content assertion validating the preserved persona text.
Assumptions:
- The inferred key `cognitive_multiplexer` is acceptable for the bundled catalog.
- The title `Cognitive Multiplexer` and a concise description are sufficient metadata wrappers around the exact prompt body.
- The provided prompt text is intended to be added verbatim rather than normalized into the repo’s typical `Identity` heading format.
- Existing prompt catalog tooling should pick up the new file automatically without separate registration.
Acceptance Criteria:
- [ ] `MasterPromptRegistry().list()` includes `cognitive_multiplexer`.
- [ ] `harnessiq/master_prompts/prompts/cognitive_multiplexer.json` contains non-empty `title`, `description`, and `prompt` fields.
- [ ] The `prompt` field preserves the provided prompt body exactly apart from JSON escaping.
- [ ] `tests/test_master_prompts.py` includes `cognitive_multiplexer` in the expected bundled prompt key set.
- [ ] Focused prompt tests pass for the updated catalog.
- [ ] Prompt registry and CLI surfaces continue to load the bundled catalog successfully after the addition.
Verification Steps:
- Run `python -m pytest tests/test_master_prompts.py tests/test_master_prompts_cli.py tests/test_master_prompt_session_injection.py`.
- Run `python -c "from harnessiq.master_prompts import get_prompt; prompt = get_prompt('cognitive_multiplexer'); print(prompt.title); print(prompt.prompt.splitlines()[0])"`.
- If prompt catalog docs are generated from repository structure, run the repo’s docs verification command and confirm no prompt-related drift was introduced.
Dependencies: None.
Drift Guard: This ticket must stay additive. Do not refactor the prompt registry, do not rewrite existing prompt assets, do not normalize the user-provided prompt body into a different style, and do not mix unrelated dirty-worktree changes into the implementation branch.
