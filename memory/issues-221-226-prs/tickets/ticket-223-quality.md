## Quality Pipeline Results

### Stage 1: Static Analysis

- No repository-configured linter is present.
- Manually reviewed `harnessiq/shared/instantly_agent.py`, `harnessiq/agents/instantly/agent.py`, `harnessiq/agents/instantly/__init__.py`, and `tests/test_instantly_agent.py` for import hygiene, naming consistency, and parity with the Apollo/Exa provider-base pattern.

### Stage 2: Type Checking

- No repository-configured type checker is present.
- Confirmed all new public classes, functions, and properties in the Instantly scaffold are explicitly annotated.

### Stage 3: Unit Tests

- `python -m compileall harnessiq tests`
  - Passed.
- `python -m unittest tests.test_instantly_agent tests.test_instantly_provider`
  - Passed.
  - Post-critique rerun passed with 30 tests after adding the injected-client credential mismatch regression case.

### Stage 4: Integration and Contract Tests

- No separate integration or contract test runner is configured for this repository.
- `tests.test_instantly_agent` exercises the new harness against the real Instantly tool factory and operation schemas, including allowed-operation filtering and representative provider execution through `instantly_request`.

### Stage 5: Smoke and Manual Verification

- `python -m unittest`
  - Failed on pre-existing baseline issues unrelated to this ticket:
    - `harnessiq.providers.google_drive` / `harnessiq.tools.google_drive` / `tests.test_google_drive_provider` import `GOOGLE_DRIVE_DEFAULT_BASE_URL` from `harnessiq.shared.providers`, which is currently missing.
    - `tests.test_leads_agent` cannot instantiate `LeadsAgent` because `build_instance_payload` remains abstract.
    - `tests.test_linkedin_cli` fails when `Path.home()` cannot be determined in the test environment.
    - `tests.test_providers` references an undefined `provider_error` symbol.
    - `tests.test_sdk_package` reports pre-existing package-surface violations in `harnessiq/providers/output_sink_metadata.py` and `harnessiq/providers/google_drive/`.
  - Post-critique rerun produced the same failure set.
- Manual prompt verification passed with a temporary test agent:
  - The first parameter section title is `Instantly Credentials`.
  - The credentials section includes a masked API key and the allowed-operation summary without exposing the raw key.
  - The rendered system prompt explicitly instructs the harness to use `instantly_request` for account, campaign, lead, label, inbox-placement, and webhook operations.
