Title: Document dynamic tool selection and update repo-doc references

Issue URL: https://github.com/cerredz/HarnessHub/issues/390

Intent:
Provide clear user-facing and repository-facing documentation for the new dynamic tool-selection feature so SDK users and maintainers understand how to enable it, what it changes, and what remains static by default.

Scope:
- Add a focused public doc for dynamic tool selection.
- Update existing runtime/tool docs to mention the new opt-in feature.
- Update generated repo-doc references or doc-link inputs as needed so the documentation surface stays consistent.

Scope Exclusions:
- No runtime behavior changes.
- No selector algorithm changes.
- No new CLI behavior beyond documentation of what prior tickets implemented.

Relevant Files:
- `docs/dynamic-tool-selection.md` — new author-facing documentation.
- `docs/tools.md` — describe dynamic selection relative to current tool composition.
- `docs/agent-runtime.md` — describe the runtime integration point and static-default behavior.
- `README.md` — add high-signal mention of the feature if appropriate.
- `scripts/sync_repo_docs.py` — update doc-link references if needed for generated docs.
- `tests/test_docs_sync.py` — keep doc-generation expectations aligned.

Approach:
Document the feature in the same style as the rest of the repo:
- static path remains the default
- dynamic selection is opt-in
- existing catalog remains intact
- candidate existing tools can be specified by string
- custom callable tools remain available through Python construction

Assumptions:
- Prior tickets completed the runtime and CLI behavior being documented.
- Generated repo-doc references are the correct place to keep doc discoverability aligned.

Acceptance Criteria:
- [ ] A dedicated `docs/dynamic-tool-selection.md` exists.
- [ ] Existing runtime/tool docs mention the feature accurately.
- [ ] README or generated doc references are updated if needed for discoverability.
- [ ] Doc-generation tests pass.

Verification Steps:
- Static analysis/manual style review of changed markdown and generator code.
- Run doc-generation-related tests.
- Run `python scripts/sync_repo_docs.py --check` or equivalent if supported.
- Perform a smoke/manual review that the new documentation is internally consistent with the implementation.

Dependencies:
- `ticket-3.md`

Drift Guard:
This ticket must not change runtime logic. Its job is to document the implemented feature clearly and keep the repo-doc generation surface aligned with the new docs.
