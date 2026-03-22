Stage 1 — Static Analysis:
- No project linter command is configured locally. Reviewed constructor refactors and payload helpers manually for consistency with the current codebase.

Stage 2 — Type Checking:
- No configured type-checker command was available. New constructor and helper code is fully annotated.

Stage 3 — Unit Tests:
- Ran:
  `.venv\Scripts\python.exe -m unittest tests.test_linkedin_agent tests.test_linkedin_cli tests.test_knowt_agent`
- Result: passed.

Stage 4 — Integration & Contract Tests:
- Ran:
  `.venv\Scripts\python.exe -m unittest tests.test_agent_instances tests.test_agents_base tests.test_linkedin_agent tests.test_linkedin_cli tests.test_knowt_agent tests.test_credentials_config tests.test_sdk_package`
- Result: passed.

Stage 5 — Smoke & Manual Verification:
- Ran a direct ExaOutreach constructor/run smoke script with `.venv\Scripts\python.exe` because the local environment does not have `pytest` installed, and `tests/test_exa_outreach_agent.py` imports `pytest`.
- Observed:
  `completed`
  an emitted `agent.instance_id`
  the expected resolved `agent.memory_path`
- This confirmed the ExaOutreach constructor remained runnable after the instance-registration changes.
