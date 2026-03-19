Title: Move leads shared definitions and tool construction out of the agent module

Intent:
Apply the PR #161 review feedback by restoring the intended boundary between `agents/`, `shared/`, and `tools/` for the leads harness.

Scope:
- Move leads config/defaults/constants/types out of `harnessiq/agents/leads/agent.py`.
- Add a leads tool factory under `harnessiq/tools/leads/`.
- Update tests and `artifacts/file_index.md` to reflect and enforce the standard.

Relevant Files:
- `harnessiq/agents/leads/agent.py`
- `harnessiq/shared/leads.py`
- `harnessiq/shared/tools.py`
- `harnessiq/tools/leads/__init__.py`
- `harnessiq/tools/leads/operations.py`
- `tests/test_leads_shared.py`
- `tests/test_leads_tools.py`
- `artifacts/file_index.md`

Approach:
Use the same pattern already present in adjacent domains: shared config/state in `shared/`, concrete tool factories in `tools/`, and a thinner harness that imports those pieces and keeps orchestration only.

Acceptance Criteria:
- [ ] Leads shared definitions no longer originate in the agent file.
- [ ] Leads internal tool definitions and provider-tool composition originate under `harnessiq/tools/leads/`.
- [ ] `LeadsAgent` behavior stays unchanged from the caller’s perspective.
- [ ] Leads-focused tests pass.
- [ ] `artifacts/file_index.md` explicitly states the relevant architectural boundary.

Verification Steps:
- Run the leads-focused test suite.
- Inspect the changed files to confirm the boundary shift is real rather than cosmetic.

Dependencies:
- None.

Drift Guard:
Do not redesign the leads workflow or broaden the generic tool catalog. This is a structural cleanup plus standards reinforcement, not a feature change.
