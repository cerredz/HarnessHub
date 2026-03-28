# LinkedIn Job Applier

`LinkedIn Job Applier` is the built-in HarnessIQ browser-backed job-application harness. It persists job preferences, user profile state, imported files, screenshots, and recent actions between runs.

See [README.md](./README.md) for shared install, model-profile, credential-binding, sink, export, and reporting flows.

## Quick Facts

| Item | Value |
| --- | --- |
| Inspect command | `harnessiq inspect linkedin` |
| CLI family | `harnessiq linkedin` |
| Default memory root | `memory/linkedin` |
| Providers | `playwright` |
| Runtime parameters | `max_tokens`, `reset_threshold`, `action_log_window`, `linkedin_start_url`, `notify_on_pause`, `pause_webhook` |
| Custom parameters | open-ended `--custom-param KEY=VALUE` payload |
| Main outputs | `jobs_applied`, `managed_files`, `recent_actions` |

## Durable Files

The harness persists its working state under `memory/linkedin/<agent>/`.

- `job_preferences.md`: saved target-role preferences.
- `user_profile.md`: saved profile/background info for application decisions.
- `agent_identity.md`: optional system-identity override.
- `runtime_parameters.json`: saved `max_tokens`, `reset_threshold`, `action_log_window`, `linkedin_start_url`, `notify_on_pause`, and `pause_webhook`.
- `custom_parameters.json`: open-ended custom payload from `--custom-param`.
- `additional_prompt.md`: free-form extra operator guidance.
- `applied_jobs.jsonl`: append-only application history.
- `action_log.jsonl`: append-only recent action log.
- `managed_files.json` plus `managed_files/`: imported resume/cover-letter files tracked by the CLI.
- `screenshots/`: persisted screenshots captured during runs.

## Prepare, Browser Bootstrap, and Configure

```powershell
$Root = Join-Path (Get-Location) 'linkedin_ops'
New-Item -ItemType Directory -Force -Path "$Root\memory\linkedin" | Out-Null

harnessiq linkedin prepare --agent candidate-a --memory-root "$Root\memory\linkedin"

harnessiq linkedin init-browser --agent candidate-a --memory-root "$Root\memory\linkedin"

harnessiq linkedin configure `
  --agent candidate-a `
  --memory-root "$Root\memory\linkedin" `
  --job-preferences-file .\linkedin\job_preferences.md `
  --user-profile-file .\linkedin\profile.md `
  --agent-identity-file .\linkedin\identity.md `
  --additional-prompt-file .\linkedin\notes.md `
  --runtime-param action_log_window=25 `
  --runtime-param notify_on_pause=true `
  --custom-param preferred_locations='[\"Remote\",\"Chicago\"]' `
  --import-file .\linkedin\resume.pdf `
  --inline-file cover-letter.txt='Short cover letter text'
```

## Run Patterns

Run with a provider-backed model and a browser-tools factory:

```powershell
harnessiq linkedin run `
  --agent candidate-a `
  --memory-root "$Root\memory\linkedin" `
  --model openai:gpt-5.4 `
  --browser-tools-factory myproject.linkedin:create_browser_tools `
  --max-cycles 5
```

Run with a reusable model profile and a sink:

```powershell
harnessiq linkedin run `
  --agent candidate-a `
  --memory-root "$Root\memory\linkedin" `
  --profile fast-grok `
  --browser-tools-factory myproject.linkedin:create_browser_tools `
  --sink "jsonl:$Root\ledger\linkedin.jsonl" `
  --runtime-param notify_on_pause=false
```

Shared tool controls also apply:

```powershell
harnessiq linkedin run `
  --agent candidate-a `
  --memory-root "$Root\memory\linkedin" `
  --profile fast-grok `
  --browser-tools-factory myproject.linkedin:create_browser_tools `
  --approval on-request `
  --allowed-tools linkedin.*,browser_use.*,reasoning.* `
  --dynamic-tools
```

## Inspect and Export

```powershell
harnessiq linkedin show --agent candidate-a --memory-root "$Root\memory\linkedin"
harnessiq export --ledger-path "$Root\ledger\linkedin.jsonl" --format json --flatten-outputs > "$Root\exports\linkedin.json"
harnessiq report --ledger-path "$Root\ledger\linkedin.jsonl" --format markdown > "$Root\exports\linkedin-report.md"
```

Reuse the same `--agent` and `--memory-root` later to continue from the saved `applied_jobs.jsonl`, `action_log.jsonl`, and managed file state.
