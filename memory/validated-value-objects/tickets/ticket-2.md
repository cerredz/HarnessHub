Title: Normalize provider and env credential models through validated scalars

Issue URL: https://github.com/cerredz/HarnessHub/issues/336

Intent:
Apply the new value-object pattern to the repo’s highest-leverage string seams: credential bindings, provider credential specs, shared provider credential dataclasses, and direct env-to-credential factories.

Scope:
Refactor credential/config/provider modules to construct validated scalar objects at parse time instead of trusting raw strings and validating them piecemeal downstream. Preserve the public provider credential APIs and existing behavior. This ticket does not yet touch context/reasoning numeric tools or provider operation-description builders.

Relevant Files:
- `harnessiq/config/credentials.py`: validate env var names, field names, agent names, and resolved env values through shared scalars
- `harnessiq/config/provider_credentials/models.py`: validate provider family names, field names, descriptions, and required values through shared scalars
- `harnessiq/config/provider_credentials/api.py`: stop reimplementing provider-family normalization
- `harnessiq/shared/credentials.py`: replace repeated blank/base-url/timeout checks with shared validated scalars across service-provider credential dataclasses
- `harnessiq/shared/google_drive.py`: reuse shared validated scalars for OAuth credential fields and URLs
- `harnessiq/shared/resend_models.py`: reuse shared validated scalars for API key, base URL, user agent, and timeout handling
- `harnessiq/providers/exa/client.py`: construct `ExaCredentials` from validated env input instead of raw stripped strings
- `harnessiq/providers/output_sink_metadata.py`: reuse shared non-empty string coercion for provider/model metadata extraction
- `tests/test_credentials_config.py`: update/add coverage for the value-object-backed env/config layer
- `tests/test_apollo_provider.py`: preserve credential behavior through the refactor
- `tests/test_google_drive_provider.py`: preserve Google Drive credential behavior
- `tests/test_resend_tools.py`: preserve Resend credential behavior

Approach:
Adopt the new shared scalar parsers inside the smallest number of central modules that fan out across the provider layer. Keep dataclass fields externally readable as familiar primitive values where needed, but normalize and validate in `__post_init__` via the shared constructors rather than repeating `strip()` / `<= 0` checks. For env loading, parse env-variable names and non-empty values once at resolution time so downstream credential builders receive already-valid data.

Assumptions:
- Existing public credential constructors should continue accepting primitive Python inputs.
- Preserving current test expectations is more important than exposing the new scalar types directly in every public attribute.
- Shared provider credential dataclasses are the dominant injection point for “all providers” in the service-provider layer.

Acceptance Criteria:
- [ ] Credential binding/config modules use shared validated scalars instead of ad hoc string normalization.
- [ ] Shared provider credential dataclasses and related credential models centralize blank/base-url/timeout validation through the shared scalar layer.
- [ ] Direct env credential factories no longer trust raw stripped environment strings.
- [ ] Existing credential-oriented tests pass after the refactor, with new coverage where semantics changed.

Verification Steps:
- Run `tests/test_credentials_config.py`.
- Run `tests/test_apollo_provider.py`.
- Run `tests/test_google_drive_provider.py`.
- Run `tests/test_resend_tools.py`.

Dependencies:
- Ticket 1

Drift Guard:
This ticket must not redesign provider APIs, change credential payload schemas, or rewrite unrelated provider request logic. The goal is to centralize primitive validation, not to change integration behavior.
