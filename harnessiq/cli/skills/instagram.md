# Instagram Keyword Discovery

`Instagram Keyword Discovery` is the built-in HarnessIQ harness for rotating through one or more ICP definitions, searching Instagram, and persisting deduplicated leads/emails over time.

See [README.md](./README.md) for shared install, model-profile, credential-binding, sink, export, and reporting flows.

## Quick Facts

| Item | Value |
| --- | --- |
| Inspect command | `harnessiq inspect instagram` |
| CLI family | `harnessiq instagram` |
| Default memory root | `memory/instagram` |
| Providers | `playwright` |
| Runtime parameters | `max_tokens`, `recent_result_window`, `recent_search_window`, `reset_threshold`, `search_result_limit` |
| Custom parameters | open-ended `--custom-param KEY=VALUE` payload |
| Main outputs | `emails`, `leads`, `search_history` |

## Durable Files

The harness persists its working state under `memory/instagram/<agent>/`.

- `icp_profiles.json`: the persisted ICP descriptions.
- `search_history.json`: legacy flat search history kept for compatibility.
- `run_state.json`: current multi-ICP run state.
- `icps/*.json`: per-ICP history and completion state.
- `lead_database.json`: deduplicated persisted leads/emails.
- `runtime_parameters.json`: saved `max_tokens`, `recent_result_window`, `recent_search_window`, `reset_threshold`, and `search_result_limit`.
- `custom_parameters.json`: open-ended custom payload from `--custom-param`.
- `agent_identity.txt`: optional system-identity override.
- `additional_prompt.txt`: extra prompt guidance.

## Prepare and Configure

```powershell
$Root = Join-Path (Get-Location) 'vidbyte_leads'
New-Item -ItemType Directory -Force -Path "$Root\memory\instagram" | Out-Null
New-Item -ItemType Directory -Force -Path "$Root\ledger" | Out-Null
New-Item -ItemType Directory -Force -Path "$Root\exports" | Out-Null

harnessiq instagram prepare --agent ig-ai-edu --memory-root "$Root\memory\instagram"

harnessiq instagram configure `
  --agent ig-ai-edu `
  --memory-root "$Root\memory\instagram" `
  --icp 'AI educational creators who produce content about artificial intelligence, machine learning, LLMs, and AI-powered learning tools' `
  --icp 'STEM creators who explain science and engineering concepts for students and professionals' `
  --runtime-param search_result_limit=5 `
  --runtime-param recent_search_window=10 `
  --runtime-param recent_result_window=10 `
  --custom-param market='\"education\"' `
  --additional-prompt-file .\prompts\instagram_notes.txt
```

There is no API credential binding requirement here, but most real runs use the default Playwright search backend and therefore need Playwright Chromium installed.

## Run Patterns

Minimal run using the default browser-backed search backend:

```powershell
harnessiq instagram run `
  --agent ig-ai-edu `
  --memory-root "$Root\memory\instagram" `
  --model openai:gpt-5.4 `
  --search-backend-factory harnessiq.integrations.instagram_playwright:create_search_backend `
  --max-cycles 100
```

Run with a reusable profile and per-run ICP override:

```powershell
harnessiq instagram run `
  --agent ig-ai-edu `
  --memory-root "$Root\memory\instagram" `
  --profile fast-grok `
  --icp 'Founders and operators who post practical AI workflow content' `
  --runtime-param search_result_limit=8 `
  --custom-param campaign='\"spring_launch\"'
```

Run with shared tool controls:

```powershell
harnessiq instagram run `
  --agent ig-ai-edu `
  --memory-root "$Root\memory\instagram" `
  --profile fast-grok `
  --approval on-request `
  --allowed-tools instagram.*,reasoning.* `
  --dynamic-tools `
  --dynamic-tool-top-k 10
```

## Inspect and Export

Return the currently persisted discovered emails:

```powershell
harnessiq instagram get-emails --agent ig-ai-edu --memory-root "$Root\memory\instagram"
```

Inspect the durable state:

```powershell
harnessiq instagram show --agent ig-ai-edu --memory-root "$Root\memory\instagram"
```

Export the ledger after runs:

```powershell
harnessiq export --ledger-path "$Root\ledger\ig-ai-edu.jsonl" --format csv --flatten-outputs > "$Root\exports\ig-ai-edu.csv"
harnessiq report --ledger-path "$Root\ledger\ig-ai-edu.jsonl" --format markdown > "$Root\exports\ig-ai-edu-report.md"
```

Because the state lives under the same `--agent` and `--memory-root`, later runs continue from the saved `run_state.json`, `icps/*.json`, and `lead_database.json` files even without a separate `--resume` flag.
