Title: Expose ExaOutreach search-only mode through the CLI and public docs

Issue URL:
https://github.com/cerredz/HarnessHub/issues/185

Intent:
Make the new ExaOutreach search-only mode reachable and understandable for users through the existing outreach CLI contract and README documentation, while keeping the CLI aligned with the runtime-parameter conventions already used in this command family.

Scope:
- Extend outreach runtime-parameter normalization to accept `search_only`.
- Update `outreach run` so `--resend-credentials-factory` and `--email-data-factory` are optional when `search_only=true` is configured or overridden.
- Pass the resolved `search_only` value into the SDK agent constructor.
- Update CLI summaries/tests to reflect that a search-only run persists leads and may have zero emails by design.
- Update README SDK and CLI examples/documentation to explain the new mode and its optional inputs.

Scope exclusions:
- Do not add bespoke CLI flags for search-only mode.
- Do not change the core SDK behavior beyond what is needed to thread the resolved runtime parameter into the constructor.
- Do not refactor unrelated README sections.

Relevant Files:
- `harnessiq/cli/exa_outreach/commands.py` — accept and normalize `search_only`, relax factory requirements conditionally, and construct the agent correctly.
- `tests/test_exa_outreach_cli.py` — add parser/runtime coverage for search-only configuration, optional factories, and run construction.
- `README.md` — document SDK and CLI usage for search-only mode and correct the ExaOutreach public behavior description.

Approach:
Keep CLI behavior consistent with existing outreach runtime parameters by adding `search_only` to the normalized runtime-param map instead of introducing a dedicated top-level flag. Resolve the mode before loading optional factories so the CLI can skip Resend/email-template requirements in search-only mode. Documentation should show both the normal outreach path and the lead-only variant, making the public contract explicit.

Assumptions:
- Ticket 1 has already landed and the SDK constructor accepts `search_only`.
- Users should be able to configure search-only once via `configure` and also override it at run time via `--runtime-param`.
- The CLI should still reject missing email factories in normal mode.

Acceptance Criteria:
- [ ] `search_only` is accepted by outreach runtime-parameter normalization.
- [ ] `harnessiq outreach configure --runtime-param search_only=true` persists the mode.
- [ ] `harnessiq outreach run` can execute in search-only mode without `--resend-credentials-factory` and without `--email-data-factory`.
- [ ] `harnessiq outreach run` still requires those factories in normal mode.
- [ ] The CLI passes the resolved `search_only` value into `ExaOutreachAgent`.
- [ ] README documents the SDK constructor flag and the CLI runtime-parameter workflow for search-only usage.

Verification Steps:
- Static analysis on the changed CLI/doc/test files where applicable.
- Type-check or manual typed review if no checker is configured.
- Run `pytest tests/test_exa_outreach_cli.py`.
- Run a CLI smoke path that configures `search_only=true` and confirms the command constructs/runs without email factories.

Dependencies:
- Ticket 1.

Drift Guard:
This ticket must stay focused on public surface area for the already-implemented SDK behavior. It must not reopen prompt/tool-surface design or spill into unrelated CLI cleanup. The objective is a clean, documented, runtime-parameter-based path to the new mode.
