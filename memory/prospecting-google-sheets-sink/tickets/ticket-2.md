Title: Fail fast when a prospecting run still uses the placeholder company description

Intent: Prevent silent one-cycle “successful” prospecting runs when the agent was never given a real target profile.

Scope:
- Add validation in the prospecting run path before the first model call.
- Add tests that cover the placeholder-target failure case.
- Do not change evaluation heuristics or browser extraction logic.

Relevant Files:
- `harnessiq/shared/prospecting.py`: central source for the placeholder description and prospecting-specific validation helpers.
- `harnessiq/cli/prospecting/commands.py`: fail before model execution when the persisted company description is still the placeholder.
- `tests/test_prospecting_cli.py` or `tests/test_prospecting_agent.py`: add regression coverage.

Approach:
- Treat the placeholder description as invalid input for `run`.
- Raise a clear error that tells the operator to use `prospecting configure` first.

Assumptions:
- The right UX is a deterministic CLI error instead of another model roundtrip asking for clarification.

Acceptance Criteria:
- [ ] Prospecting runs with the default placeholder description fail before model execution.
- [ ] The error message tells the operator exactly how to fix the configuration.
- [ ] Existing configured runs still work.

Verification Steps:
- Run focused prospecting tests.
- Manually reason-check the CLI command path against the reproduced failure.

Dependencies:
- Ticket 1 is independent.

Drift Guard:
- This ticket must not introduce prompt-only fixes, retries, or hidden mutation of company descriptions during `run`.
