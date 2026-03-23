# Verification

- Synced local `main` to `origin/main` with `git pull --ff-only origin main` before implementation.
- Ran targeted runtime regression:
  - `pytest tests/test_output_sinks.py tests/test_tools.py tests/test_agents_base.py tests/test_instagram_agent.py tests/test_linkedin_agent.py tests/test_prospecting_agent.py tests/test_exa_outreach_agent.py tests/test_email_agent.py -q`
  - Result after fixes: `98 passed`
- Ran adjacent harness and packaging coverage:
  - `pytest tests/test_leads_agent.py tests/test_leads_tools.py tests/test_knowt_agent.py tests/test_sdk_package.py -q`
  - Result: all agent/package smoke checks passed except `tests/test_sdk_package.py::HarnessiqPackageTests::test_agents_and_providers_keep_shared_definitions_out_of_local_modules`
- Ran consolidated affected-suite verification excluding the known unrelated package invariant:
  - `pytest tests/test_output_sinks.py tests/test_tools.py tests/test_agents_base.py tests/test_instagram_agent.py tests/test_linkedin_agent.py tests/test_prospecting_agent.py tests/test_exa_outreach_agent.py tests/test_email_agent.py tests/test_knowt_agent.py tests/test_leads_agent.py tests/test_leads_tools.py tests/test_sdk_package.py -k "not test_agents_and_providers_keep_shared_definitions_out_of_local_modules" -q`
  - Result: `141 passed, 1 deselected`

# Known Unrelated Failure

- `tests/test_sdk_package.py::HarnessiqPackageTests::test_agents_and_providers_keep_shared_definitions_out_of_local_modules`
- Current failure is caused by existing provider-module violations outside this task's scope:
  - `harnessiq/providers/output_sink_metadata.py`
  - `harnessiq/providers/google_drive/client.py`
  - `harnessiq/providers/google_drive/operations.py`
