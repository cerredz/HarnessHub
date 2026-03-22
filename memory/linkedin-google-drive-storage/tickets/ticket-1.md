Title: Add Google Drive credentials persistence and provider client support
Issue URL: https://github.com/cerredz/HarnessHub/issues/145

Intent: Establish a repo-native way to save/load Google Drive OAuth credentials and a first-class Google Drive provider surface so the LinkedIn agent can persist application artifacts using the same provider patterns as the rest of the SDK.

Scope:
- Add a concrete Google Drive credential schema and client/request helpers for env-backed OAuth credentials.
- Add SDK support for persisting actual credential values plus agent-to-env bindings through the existing config layer.
- Add a Google Drive tool/provider factory surface sufficient for deterministic folder and file writes.
- Do not modify LinkedIn agent behavior in this ticket beyond any strictly necessary import-safe plumbing.

Relevant Files:
- `harnessiq/config/credentials.py`: add safe `.env` write/update helpers and any supporting persistence APIs needed to store credential values from SDK calls.
- `harnessiq/config/__init__.py`: export any new credential persistence helpers.
- `harnessiq/shared/credentials.py`: add the Google Drive credential TypedDict.
- `harnessiq/providers/http.py`: extend provider-name inference for Google Drive API hosts if needed for clear errors.
- `harnessiq/providers/google_drive/api.py`: define Drive API constants, scopes, and auth/header helpers.
- `harnessiq/providers/google_drive/client.py`: implement validated credentials plus Drive client logic, including access-token refresh from refresh token.
- `harnessiq/providers/google_drive/operations.py`: define the limited Drive operation catalog and request preparation for deterministic folder/file upserts.
- `harnessiq/providers/google_drive/__init__.py`: re-export the provider surface.
- `harnessiq/tools/google_drive/__init__.py`: expose the provider tool factory for the toolset dispatch pattern.
- `harnessiq/toolset/catalog.py`: register static metadata and lazy factory mapping for the Google Drive family if the provider is intended to participate in the public toolset.
- `tests/test_credentials_config.py`: cover persisted `.env` writes and binding resolution for saved credentials.
- `tests/test_google_drive_provider.py`: cover credential validation, token refresh preparation, and Drive tool/client behavior with fake executors.

Approach:
- Extend the existing repo-local credentials store instead of inventing a second secret persistence path.
- Keep Google auth env-backed and explicit: persist named env vars in `.env`, persist the logical binding in `.harnessiq/credentials.json`, then resolve concrete credentials through the existing config store.
- Implement only the minimum Drive operations needed for deterministic persistence: locate/create folder hierarchy and upsert a JSON metadata file.
- Keep the provider implementation stdlib-based to match existing HTTP client conventions and avoid introducing new third-party dependencies.

Assumptions:
- Google Drive access will be provided through OAuth client credentials plus a refresh token stored in repo-local configuration.
- The SDK should be able to save credential values to `.env` in addition to saving the binding metadata.
- A narrow Google Drive operation surface is sufficient; this task does not require a complete generic Drive SDK wrapper.
- Adding Google Drive to the public toolset catalog is acceptable if the implementation remains narrow and credential-gated.

Acceptance Criteria:
- [ ] The SDK can save Google Drive credential values into the repo-local `.env` file and persist a matching agent credential binding.
- [ ] The SDK can resolve saved Google Drive credentials back into a concrete credential payload for runtime use.
- [ ] A validated Google Drive client/provider surface exists for deterministic folder lookup/creation and JSON file upsert behavior using OAuth bearer auth.
- [ ] Automated tests cover credential persistence, credential resolution, token refresh preparation, and Drive request behavior.
- [ ] Existing credential-config behavior for unrelated agents/providers remains backward compatible.

Verification Steps:
- Static analysis: manually review the changed config/provider files for secret handling, overwrite semantics, and exception clarity because no configured linter is present.
- Type checking: no configured checker; validate the new dataclasses, TypedDicts, and helper signatures through import-time execution and tests.
- Unit tests: run `python -m pytest tests/test_credentials_config.py tests/test_google_drive_provider.py`.
- Integration and contract tests: run the broader provider/config suite that exercises package exports and credential helpers.
- Smoke/manual verification: save a temporary Google Drive credential set into a temp repo root, resolve it through the config store, and verify the prepared Drive operations target stable folder/file paths.

Dependencies: None.

Drift Guard: This ticket must not add LinkedIn-specific business logic, duplicate-application behavior, or CLI user flows beyond the minimum needed to expose credential persistence APIs cleanly. Its goal is to deliver a stable credentials and provider foundation only.
