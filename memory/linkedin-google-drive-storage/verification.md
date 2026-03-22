## Verification

Date: 2026-03-18

Focused automated checks run from the repo root with the project virtual environment:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_credentials_config tests.test_google_drive_provider tests.test_linkedin_agent tests.test_linkedin_cli tests.test_sdk_package
.\.venv\Scripts\python.exe -c "import harnessiq; import harnessiq.agents; import harnessiq.cli.main; import harnessiq.providers.google_drive; print('ok')"
```

Results:

- `42` targeted tests passed.
- Import smoke passed for the SDK package, agent exports, CLI entrypoint, and Google Drive provider module.

Coverage of the implemented behavior:

- Repo-local credential binding persistence and `.env` updates for LinkedIn Google Drive credentials.
- Google Drive provider client, operation catalog, tool factory, and deterministic folder / `job.json` upsert behavior.
- LinkedIn agent duplicate detection via `already_applied`.
- Rich applied-job record persistence and optional Drive synchronization after successful application.
- CLI configuration, credential management, and `run` stdout/stderr contract.
- Packaging smoke coverage through `tests.test_sdk_package`.
