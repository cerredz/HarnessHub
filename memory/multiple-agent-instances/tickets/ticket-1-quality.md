Stage 1 — Static Analysis:
- No dedicated linter is configured in this environment. Applied the repository's existing formatting and validation patterns manually while implementing.

Stage 2 — Type Checking:
- No standalone type-checker command is configured in this environment. New code uses explicit type annotations consistent with the existing codebase.

Stage 3 — Unit Tests:
- Ran:
  `.venv\Scripts\python.exe -m unittest tests.test_agent_instances tests.test_agents_base`
- Result: passed.

Stage 4 — Integration & Contract Tests:
- Ran:
  `.venv\Scripts\python.exe -m unittest tests.test_credentials_config tests.test_sdk_package`
- Result: passed. This verified the new registry/storage pattern coexists with existing config storage and package exports.

Stage 5 — Smoke & Manual Verification:
- Verified deterministic instance resolution behavior through tests plus direct instantiation flows while wiring concrete agents.
- Confirmed the registry file is written under `memory/agent_instances.json` and records remain retrievable by instance id.
