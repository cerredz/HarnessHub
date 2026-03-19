Issue URL: https://github.com/cerredz/HarnessHub/issues/177
PR URL: https://github.com/cerredz/HarnessHub/pull/186

Title: Centralize remaining agent-side shared definitions and provider-adjacent constants

Intent:
Complete the agent-half of the file-index rule by moving any remaining misplaced agent config/type/constant definitions into `harnessiq/shared/`, while also normalizing the in-scope adjacent provider-like runtime constants that follow the same architectural rule.

Scope:
- Move remaining non-behavioral agent definitions into the corresponding `harnessiq/shared/<agent>.py` modules.
- Keep harness-local prompt path wiring and default-memory-path locators in the agent modules, per clarification.
- Normalize adjacent provider-like runtime constants/config definitions that belong in `shared/`, starting with `providers/output_sinks.py`.
- Update package exports and tests affected by the shared-definition source-of-truth move.
- Do not change agent runtime behavior, prompt contents, or output-sink request behavior.

Relevant Files:
- `harnessiq/shared/exa_outreach.py`: expand the shared ExaOutreach definition surface if any remaining config/type constants still live in the agent module.
- `harnessiq/shared/instagram.py`: verify and complete the Instagram shared-definition surface.
- `harnessiq/shared/knowt.py`: verify and complete the Knowt shared-definition surface.
- `harnessiq/shared/linkedin.py`: verify and complete the LinkedIn shared-definition surface.
- `harnessiq/shared/email.py`: verify and complete the reusable email-agent shared-definition surface.
- `harnessiq/shared/providers.py`: add any adjacent provider-like shared constants extracted from output-sink/provider-adjacent runtime code.
- `harnessiq/agents/email/agent.py`: update imports to consume shared definitions only.
- `harnessiq/agents/exa_outreach/agent.py`: update imports to consume shared definitions only.
- `harnessiq/agents/instagram/agent.py`: update imports to consume shared definitions only.
- `harnessiq/agents/knowt/agent.py`: update imports to consume shared definitions only.
- `harnessiq/agents/linkedin/agent.py`: update imports to consume shared definitions only.
- `harnessiq/agents/__init__.py`: preserve public exports after internal moves.
- `harnessiq/agents/email/__init__.py`: preserve public exports after internal moves.
- `harnessiq/agents/exa_outreach/__init__.py`: preserve public exports after internal moves.
- `harnessiq/agents/instagram/__init__.py`: preserve public exports after internal moves.
- `harnessiq/agents/knowt/__init__.py`: preserve public exports after internal moves.
- `harnessiq/agents/linkedin/__init__.py`: preserve public exports after internal moves.
- `harnessiq/providers/output_sinks.py`: remove in-scope misplaced constants/config definitions and import them from `shared/`.
- `tests/test_linkedin_agent.py`: update coverage if import locations or shared-definition ownership changes.
- `tests/test_knowt_agent.py`: update coverage if import locations or shared-definition ownership changes.
- `tests/test_instagram_agent.py`: update coverage if import locations or shared-definition ownership changes.
- `tests/test_email_agent.py`: update coverage if import locations or shared-definition ownership changes.
- `tests/test_output_sinks.py`: update coverage for adjacent provider-like shared-definition extraction.

Approach:
Use the existing agent-domain shared modules as the canonical homes and expand them only where a genuine definition still lives in an agent module. Keep prompt-path and memory-path scaffolding local to the harness modules because those are implementation details, not reusable shared definitions. For provider-adjacent runtime surfaces, move only definition-only constants/config values into `shared/` and leave executable clients and delivery behavior in place.

Assumptions:
- Agent harness-local prompt path/default-memory constants remain intentionally local.
- Existing shared agent modules are the correct homes for durable agent config/types/constants.
- `DEFAULT_NOTION_VERSION` and any equivalent adjacent runtime constants are in scope because the user requested a normalized pass beyond the strict agent/provider directory boundary.

Acceptance Criteria:
- [ ] No agent module owns durable/public config/type/constant definitions that belong in `harnessiq/shared/`.
- [ ] Harness-local prompt path/default-memory wiring remains local and unchanged in behavior.
- [ ] In-scope adjacent provider-like constants/config values are sourced from `harnessiq/shared/`.
- [ ] Public package imports for agents remain intact via direct import or compatibility re-export.
- [ ] Agent and output-sink tests covering the touched surfaces pass.

Verification Steps:
- Run targeted agent and output-sink tests for the touched modules.
- Run package-surface tests that validate public agent exports.
- Perform import smoke checks for `harnessiq.agents`, each touched agent package, and `harnessiq.providers.output_sinks`.

Dependencies:
- None.

Drift Guard:
This ticket must not redesign agent behavior, prompt assembly, output-sink delivery semantics, or provider HTTP execution. It is strictly a definition-ownership cleanup that moves shared constants/types/configs without changing operational behavior.


