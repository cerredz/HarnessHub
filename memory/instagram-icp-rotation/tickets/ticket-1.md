Title: Rotate the Instagram agent through one active ICP at a time

Issue URL: https://github.com/cerredz/HarnessHub/issues/273

Intent:
Rewrite the Instagram harness so the model sees one ICP and that ICP's recent searches at a time, while the runtime deterministically iterates through every configured ICP and keeps per-ICP durable search history.

Scope:
- Update the Instagram agent run loop to activate one ICP at a time in configured order.
- Replace global recent-search injection with active-ICP-only context injection.
- Add durable per-ICP progress/search state for the Instagram harness, including compatibility for existing memory folders.
- Simplify the Instagram master prompt into one to three natural-language paragraphs.
- Update Instagram CLI summaries and tests to reflect the new persistence and context behavior.
- Do not change the public `instagram.search_keyword` input schema.
- Do not change provider integrations outside the Instagram harness.

Relevant Files:
- `harnessiq/agents/instagram/agent.py`: add active-ICP rotation and active-context parameter loading.
- `harnessiq/shared/instagram.py`: add durable run/per-ICP state models and store helpers.
- `harnessiq/tools/instagram/operations.py`: scope duplicate checks and persistence to the active ICP.
- `harnessiq/agents/instagram/prompts/master_prompt.md`: rewrite the system prompt in concise natural language.
- `harnessiq/cli/instagram/commands.py`: update JSON summaries for per-ICP search state.
- `harnessiq/cli/adapters/instagram.py`: update platform CLI summaries for per-ICP search state.
- `tests/test_instagram_agent.py`: cover active-ICP rotation, scoped recent searches, and compatibility behavior.
- `tests/test_instagram_cli.py`: cover updated CLI summary payloads as needed.

Approach:
Mirror the proven pattern from the leads harness: persist a lightweight run state with the active ICP index plus one per-ICP JSON state file holding the ICP label, status, and its search records. Keep `icp_profiles.json` as the configured source list, derive deterministic ICP keys from those values, and bind the existing search tool to the active ICP through a callable injected by the agent. Maintain backward compatibility by continuing to expose a flattened `get_search_history()` view and by treating legacy `search_history.json` entries as fallback history when no per-ICP states exist yet. Rewrite the prompt so it explains the agent's role, keyword selection constraints, and stop condition in natural prose instead of bracketed sections.

Assumptions:
- The active ICP order is the configured order from `icp_profiles.json` or `custom_parameters["icp_profiles"]`.
- Recent-search scoping should be per ICP, not global across the entire memory folder.
- Backward compatibility should prefer safe reads over destructive migration.
- No new CLI flags are required for this behavior change.

Acceptance Criteria:
- [ ] Multi-ICP Instagram runs process ICPs serially in configured order.
- [ ] The model request for each ICP contains only that ICP in the ICP parameter section.
- [ ] The recent-search parameter section contains only searches associated with the active ICP.
- [ ] Duplicate keyword detection is scoped to the active ICP.
- [ ] Single-ICP runs continue to work.
- [ ] Existing memory folders with legacy flat `search_history.json` remain readable.
- [ ] The Instagram system prompt is rewritten into one to three natural-language paragraphs.
- [ ] Agent and CLI tests cover the new behavior and pass.

Verification Steps:
- Run the targeted Instagram agent and CLI test modules.
- Run the broader shared manifest/runtime tests if touched by the new persistence shape.
- Inspect the persisted memory files from a temporary test run to confirm per-ICP state and active-index tracking.
- Review the PR diff to confirm only live `harnessiq/` sources plus matching tests/docs were changed.

Dependencies:
- None.

Drift Guard:
This ticket must stay inside the Instagram harness. It must not refactor unrelated agent runtime abstractions, redesign the generic manifest system, or change external provider APIs. The only behavior change outside the agent itself should be minimal CLI/test/doc adjustments required to accurately represent the new Instagram persistence and context model.
