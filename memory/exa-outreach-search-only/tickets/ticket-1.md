Title: Add SDK-level search-only mode to ExaOutreachAgent

Issue URL:
https://github.com/cerredz/HarnessHub/issues/184

Intent:
Introduce a first-class ExaOutreach search-only mode so SDK users can run deterministic lead discovery without any email capability. This satisfies the requirement that the agent can be configured to search and log leads only, with no access to Resend or other email-oriented tools when the mode is enabled.

Scope:
- Add a top-level `search_only: bool = False` parameter to `ExaOutreachAgent`.
- Represent the mode in the shared ExaOutreach config model and agent instance payload.
- Allow search-only construction without Resend credentials and without email templates.
- Remove all email-related tools and email-template context from the runtime surface when search-only mode is enabled.
- Adjust prompt assembly and parameter sections so the model is instructed to perform lead discovery/logging only in search-only mode.
- Preserve existing lead logging, dedupe behavior, and run-log/ledger output shape.

Scope exclusions:
- Do not add any new sink mechanism or alter the existing post-run output-sink architecture.
- Do not redesign the generic storage backend contract.
- Do not change non-Outreach agents.

Relevant Files:
- `harnessiq/agents/exa_outreach/agent.py` — add `search_only`, branch tool registration/prompt/parameter behavior, and include the mode in instance payload and ledger metadata.
- `harnessiq/shared/exa_outreach.py` — add the mode to `ExaOutreachAgentConfig` and validate the conditional email-template requirement.
- `harnessiq/agents/exa_outreach/prompts/master_prompt.md` — provide language the runtime can use for the normal email flow while supporting a clean search-only branch.
- `tests/test_exa_outreach_agent.py` — add coverage for search-only construction, tool-surface pruning, parameter-section changes, and deterministic lead-only behavior.

Approach:
Implement `search_only` as a constructor/config flag owned by the ExaOutreach harness rather than as an ad hoc runtime parameter inside the SDK. The agent will branch its runtime surface at construction time:
- normal mode keeps the current Exa + template + Resend + logging behavior
- search-only mode keeps Exa search plus lead logging/dedupe only

The prompt should not rely on tool absence alone; instead, `build_system_prompt()` and `load_parameter_sections()` should produce mode-consistent instructions and context blocks. This preserves deterministic behavior, keeps the model’s context semantically aligned with the available tools, and adheres to the file-index requirement that deterministic checks and state writes remain in the tool/storage layer.

Assumptions:
- Search-only mode is a public SDK feature and should not require unused email inputs.
- In search-only mode, the correct persisted outputs are lead events only; `emails_sent` should remain empty.
- Existing run-log and ledger formats can remain stable with an empty `emails_sent` list rather than introducing a separate run schema.

Acceptance Criteria:
- [ ] `ExaOutreachAgent(..., search_only=True)` is supported and defaults to `False`.
- [ ] Search-only mode does not require `email_data`, Resend credentials, or a Resend client.
- [ ] Search-only mode does not register `resend.request`, `exa_outreach.list_templates`, `exa_outreach.get_template`, or `exa_outreach.log_email_sent`.
- [ ] Search-only mode still registers Exa search capability plus deterministic lead dedupe/logging.
- [ ] The model prompt and parameter sections in search-only mode do not instruct the agent to select templates or send email.
- [ ] Agent instance payload/config/metadata reflect `search_only` so the mode is inspectable and stable.
- [ ] Existing non-search-only behavior remains intact.

Verification Steps:
- Static analysis on the changed ExaOutreach files.
- Type-check or, if no checker is configured, ensure all new/changed code remains fully annotated and consistent with existing typing style.
- Run `pytest tests/test_exa_outreach_agent.py`.
- Run a narrow smoke script or equivalent unit-backed execution path that confirms search-only runs can log leads without any Resend/email-template surface.

Dependencies:
- None.

Drift Guard:
This ticket must stay inside the SDK/runtime boundary of ExaOutreach itself. It must not expose new CLI flags, rewrite sink behavior, or broaden into storage-backend redesign. The goal is to make the harness semantically correct and deterministic in search-only mode before touching the command surface.
