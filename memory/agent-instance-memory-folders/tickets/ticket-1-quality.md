Stage 1 - Static Analysis:
- No dedicated linter command is configured in this repository. Reviewed the shared-runtime, concrete-agent, and CLI changes manually for consistency with the existing codebase.

Stage 2 - Type Checking:
- No standalone type-checker command is configured in this repository. New and changed code paths keep explicit annotations consistent with the surrounding modules.

Stage 3 - Unit Tests:
- Ran:
  `.venv\Scripts\python.exe -m unittest tests.test_agent_instances tests.test_agents_base tests.test_instagram_agent tests.test_linkedin_agent tests.test_knowt_agent tests.test_prospecting_agent tests.test_instagram_cli tests.test_linkedin_cli tests.test_prospecting_cli tests.test_sdk_package`
- Ran:
  `.venv\Scripts\pytest.exe tests\test_exa_outreach_agent.py tests\test_exa_outreach_cli.py`
- Result: passed.

Stage 4 - Integration & Contract Tests:
- The command above exercises the concrete harness constructors, CLI entrypoints, public package imports, and wheel/sdist packaging smoke tests together with the shared instance-registry logic.
- Result: passed.

Stage 5 - Smoke & Manual Verification:
- Verified that direct SDK agent construction now resolves a stable `instance_id` and a default memory path under `memory/agents/<agent_name>/<instance_id>/`.
- Verified that CLI run payloads now include `instance_id` / `instance_name` while preserving the configured memory folder path for CLI-managed agents.
