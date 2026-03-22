Title: Add the highest_form_of_leverage bundled master prompt
Issue URL: https://github.com/cerredz/HarnessHub/issues/235
Intent: Add a new deployable master prompt to the bundled prompt catalog so users can retrieve a system prompt that answers like a leverage-maximizing operator who combines game theory, marketing psychology, aggressive implementation speed, delusional optimism, and specific domain knowledge.
Scope: Create one new bundled prompt JSON asset, update the master prompt regression tests for the new catalog member, and add task workflow artifacts under `memory/highest-form-of-leverage-master-prompt/`. Do not refactor the prompt registry, do not add new CLI surfaces, and do not pull in unrelated prompt-catalog work from the dirty local branch.
Relevant Files:
- `harnessiq/master_prompts/prompts/highest_form_of_leverage.json`: new bundled master prompt asset using the established seven-section structure.
- `tests/test_master_prompts.py`: extend the expected prompt key set and add prompt-specific assertions for the new bundled prompt.
- `memory/highest-form-of-leverage-master-prompt/internalization.md`: Phase 1 survey and task mapping.
- `memory/highest-form-of-leverage-master-prompt/clarifications.md`: clarification outcome for this task.
- `memory/highest-form-of-leverage-master-prompt/tickets/index.md`: ticket index entry and later issue/PR bookkeeping.
- `memory/highest-form-of-leverage-master-prompt/tickets/ticket-1.md`: this ticket document.
Approach: Use the existing file-driven prompt registry exactly as designed by adding a new JSON file under `harnessiq/master_prompts/prompts/`. Model the prompt structure and quality bar after `create_master_prompts.json`, but make the content domain-specific to the requested strategist/operator persona. Update `tests/test_master_prompts.py` so the new prompt is part of the expected catalog and receives one direct content assertion in addition to the shared seven-section checks.
Assumptions:
- The prompt slug `highest_form_of_leverage` is acceptable and aligns with the user's wording.
- The requested persona should speak directly in answers rather than producing meta-analysis about the persona.
- Additive prompt-catalog work on the dirty local branch is intentionally out of scope for this ticket because the PR target is `main`.
Acceptance Criteria:
- [ ] `MasterPromptRegistry().list()` includes `highest_form_of_leverage`.
- [ ] The new JSON prompt contains non-empty `title`, `description`, and `prompt` fields.
- [ ] The prompt text contains the seven required master prompt sections in the established order.
- [ ] The prompt content clearly encodes the requested combination of game theory, marketing psychology, implementation speed, optimism, and specific knowledge.
- [ ] `tests/test_master_prompts.py` passes on `origin/main` with the new prompt included.
- [ ] Generated docs remain in sync, or any actual drift introduced by the change is updated deliberately.
Verification Steps:
- Run `python -m pytest tests/test_master_prompts.py`.
- Run `python scripts/sync_repo_docs.py --check`.
- Run a focused registry smoke check such as `python -c "from harnessiq.master_prompts import get_prompt; print(get_prompt('highest_form_of_leverage').title)"`.
Dependencies: None.
Drift Guard: This ticket must not turn into a broader prompt-catalog refactor, CLI expansion, or merge of unrelated uncommitted work from the local feature branch. The only runtime behavior change is adding one bundled prompt asset to the current `main` branch implementation and proving it through focused tests.
