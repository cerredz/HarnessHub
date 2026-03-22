## Stage 1 - Static Analysis

- Repository has no configured linter.
- Performed manual review of:
  - `harnessiq/shared/apollo_agent.py`
  - `harnessiq/shared/exa_agent.py`
  - `harnessiq/agents/apollo/agent.py`
  - `harnessiq/agents/apollo/__init__.py`
  - `harnessiq/agents/exa/agent.py`
  - `harnessiq/agents/exa/__init__.py`
  - `tests/test_apollo_agent.py`
  - `tests/test_exa_agent.py`
- Verified the provider-specific layers stay thin, config dataclasses remain under `harnessiq/shared/`, and the agent modules avoid provider-operation duplication.

## Stage 2 - Type Checking

- Repository has no configured type checker.
- New public functions and classes were annotated manually.
- `python -m compileall harnessiq tests` passed.

## Stage 3 - Unit Tests

- `python -m unittest tests.test_apollo_agent tests.test_exa_agent tests.test_apollo_provider tests.test_exa_provider` passed.

## Stage 4 - Integration & Contract Tests

- `python -m unittest` was executed as the repository-wide regression suite.
- Result: failed due to unrelated pre-existing baseline issues on `main`, not due to this ticket.
- Observed unrelated failures:
  - `harnessiq.providers.google_drive` / `harnessiq.tools.google_drive` / `tests.test_google_drive_provider`
    - import error: missing `GOOGLE_DRIVE_DEFAULT_BASE_URL` in `harnessiq.shared.providers`
  - `tests.test_leads_agent`
    - `LeadsAgent` cannot instantiate because `build_instance_payload` is abstract
  - `tests.test_linkedin_cli.LinkedInCLITests.test_run_seeds_langsmith_environment_from_repo_env`
    - runtime error resolving home directory
  - `tests.test_providers.LangSmithTracingTests.test_trace_model_call_preserves_provider_http_error`
    - `NameError` for `provider_error`
  - `tests.test_sdk_package.HarnessiqPackageTests.test_agents_and_providers_keep_shared_definitions_out_of_local_modules`
    - pre-existing package-surface violations in `google_drive` and `output_sink_metadata`

## Stage 5 - Smoke & Manual Verification

- Manual smoke check executed:
  - `python - <<script>>` instantiating the Apollo and Exa test subclasses with a temporary repo root
- Observed output:
  - `apollo_tool`: `apollo.request`
  - `apollo_parameters`: `['Apollo Credentials', 'Apollo Brief']`
  - `exa_tool`: `exa.request`
  - `exa_parameters`: `['Exa Credentials', 'Research Brief']`
- This confirms both harnesses expose the provider request tool as the default tool and inject the expected provider credential sections ahead of their extra parameter sections.
