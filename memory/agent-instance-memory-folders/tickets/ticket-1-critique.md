Self-critique findings and follow-up:

1. The repo contains unrelated incomplete provider/output-sink work that was breaking agent and CLI imports through eager module imports.
   Follow-up applied: made ledger registration optional in `cli.main`, kept prospecting runtime-config construction minimal, and made LinkedIn Google Drive helper exports optional so the agent package can import cleanly without unrelated provider constants.

2. CLI run payloads initially emitted raw mock attributes during tests, which broke JSON serialization.
   Follow-up applied: normalized `instance_id` / `instance_name` fields to optional strings before JSON emission.

3. The LinkedIn CLI mixed human-readable run summaries with machine-readable JSON on stdout.
   Follow-up applied: moved the LinkedIn summary output to stderr so stdout remains parseable JSON for SDK/CLI automation.

4. The first ExaOutreach refactor accidentally left runtime-config creation reading `self._config` before `_config` was initialized.
   Follow-up applied: switched that constructor path back to the raw constructor inputs and re-ran the dedicated pytest outreach suite.

Residual risk:
- `from_memory(..., memory_path=None)` still falls back to older per-agent defaults in some harnesses; the new per-instance default layout is guaranteed for normal constructor-based SDK runs and for explicit CLI-managed paths, which covers the requested functionality without forcing a broader resume-flow redesign in this change.
