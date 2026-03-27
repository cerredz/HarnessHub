Post-critique review found one meaningful gap: the new request DTO boundary validated empty allowed-operation tuples in code, but there was no direct test proving that behavior at the public seam.

Implemented improvement:

- Added `AgentRequestDTOTests` in [tests/test_provider_base_agents.py](/C:/Users/422mi/HarnessHub/.worktrees/issue-327/tests/test_provider_base_agents.py) to verify:
  - `ProviderToolAgentRequest` normalizes provider names and tool iterables.
  - `ApolloAgentRequest`, `ExaAgentRequest`, `EmailAgentRequest`, `InstantlyAgentRequest`, and `OutreachAgentRequest` all reject empty allowlists with a clear `ValueError`.

Reverification after the critique change:

- `python -m pytest tests/test_provider_base_agents.py tests/test_apollo_agent.py tests/test_exa_agent.py tests/test_email_agent.py tests/test_instantly_agent.py tests/test_outreach_agent.py tests/test_agents_base.py -q`
- `python -m pytest tests/test_sdk_package.py::HarnessiqPackageTests::test_package_builds_wheel_and_sdist_and_imports_from_wheel tests/test_sdk_package.py::HarnessiqPackageTests::test_shared_definition_exports_originate_from_shared_modules tests/test_sdk_package.py::HarnessiqPackageTests::test_provider_base_exports_resolve_from_documented_modules tests/test_sdk_package.py::HarnessiqPackageTests::test_cli_module_help_executes -q`
- DTO smoke check repeated successfully.
