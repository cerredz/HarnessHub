## Static / Compile Check

- `python -m py_compile harnessiq\cli\builders\exa_outreach.py harnessiq\cli\builders\leads.py harnessiq\cli\exa_outreach\commands.py harnessiq\cli\leads\commands.py harnessiq\cli\runners\exa_outreach.py harnessiq\cli\runners\leads.py harnessiq\config\models.py harnessiq\shared\agents.py harnessiq\shared\credentials.py harnessiq\shared\email.py harnessiq\shared\exa_outreach.py harnessiq\shared\leads.py harnessiq\shared\output_sinks.py harnessiq\shared\run_storage.py harnessiq\utils\ledger_models.py harnessiq\utils\run_storage.py tests\test_sdk_package.py`
- Result: passed.

## Targeted Test Slice

- `.venv\Scripts\python.exe -m pytest tests\test_sdk_package.py::HarnessiqPackageTests::test_shared_definition_exports_originate_from_shared_modules tests\test_sdk_package.py::HarnessiqPackageTests::test_shared_package_imports_only_shared_harnessiq_modules tests\test_email_agent.py tests\test_exa_outreach_shared.py tests\test_exa_outreach_cli.py tests\test_leads_shared.py tests\test_leads_cli.py -k "not test_run_uses_provider_tools_and_storage_backend_factories" tests\test_config_loader.py tests\test_output_sinks.py`
- Result: `157 passed, 1 deselected`.

## Additional Verification Notes

- Focused follow-up:
  - `.venv\Scripts\python.exe -m pytest tests\test_sdk_package.py::HarnessiqPackageTests::test_agents_and_providers_keep_shared_definitions_out_of_local_modules tests\test_leads_cli.py::TestRunCommand::test_run_uses_provider_tools_and_storage_backend_factories`
  - Result: `test_run_uses_provider_tools_and_storage_backend_factories` passed; `test_agents_and_providers_keep_shared_definitions_out_of_local_modules` still fails on pre-existing constants in `harnessiq/agents/base/agent_helpers.py`.
