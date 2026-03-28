# Leads Agent

`Leads Agent` is the built-in HarnessIQ multi-ICP prospect discovery harness. It rotates through saved ICPs, persists search history, and deduplicates saved leads through a pluggable storage backend.

See [README.md](./README.md) for shared install, model-profile, credential-binding, sink, export, and reporting flows.

## Quick Facts

| Item | Value |
| --- | --- |
| Inspect command | `harnessiq inspect leads` |
| CLI family | `harnessiq leads` |
| Default memory root | `memory/leads` |
| Providers | `apollo`, `arcads`, `arxiv`, `attio`, `browser_use`, `coresignal`, `creatify`, `exa`, `expandi`, `hunter`, `inboxapp`, `instantly`, `leadiq`, `lemlist`, `lusha`, `outreach`, `paperclip`, `peopledatalabs`, `phantombuster`, `proxycurl`, `resend`, `salesforge`, `serper`, `smartlead`, `snovio`, `zerobounce`, `zoominfo` |
| Runtime parameters | `max_tokens`, `reset_threshold`, `prune_search_interval`, `prune_token_limit`, `search_summary_every`, `search_tail_size`, `max_leads_per_icp` |
| Custom parameters | no typed custom parameters |
| Main outputs | `run_config`, `run_state`, `icp_states`, `saved_leads` |

## Durable Files

The harness persists its working state under `memory/leads/<agent>/`.

- `run_config.json`: company background, ICPs, and enabled provider families.
- `run_state.json`: active run state and ICP pointer.
- `runtime_parameters.json`: saved runtime settings including `prune_search_interval`, `prune_token_limit`, `search_summary_every`, `search_tail_size`, and `max_leads_per_icp`.
- `icps/*.json`: per-ICP history, summaries, saved lead keys, and completion state.
- `lead_storage/`: storage backend root.
- `lead_storage/saved_leads.json`: default filesystem deduplicated lead database.

## Prepare and Configure

```powershell
$Root = Join-Path (Get-Location) 'leads_ops'
New-Item -ItemType Directory -Force -Path "$Root\memory\leads" | Out-Null

harnessiq leads prepare --agent outbound-a --memory-root "$Root\memory\leads"

harnessiq leads configure `
  --agent outbound-a `
  --memory-root "$Root\memory\leads" `
  --company-background-file .\company\background.md `
  --icp-text 'VP Sales at Series A SaaS companies' `
  --icp-text 'Head of Revenue at 50-200 employee SaaS companies' `
  --platform apollo `
  --platform zoominfo `
  --runtime-param search_summary_every=250 `
  --runtime-param search_tail_size=15 `
  --runtime-param prune_search_interval=25 `
  --runtime-param max_leads_per_icp=50
```

## Credentials and Provider Wiring

Bind whichever provider families you want the harness to use. Example for `apollo` and `zoominfo`:

```powershell
harnessiq credentials bind leads `
  --agent outbound-a `
  --memory-root "$Root\memory\leads" `
  --env apollo.api_key=APOLLO_API_KEY `
  --env zoominfo.username=ZOOMINFO_USERNAME `
  --env zoominfo.password=ZOOMINFO_PASSWORD
```

The built-in provider families currently available to `harnessiq leads` are:

`apollo`, `arcads`, `arxiv`, `attio`, `browser_use`, `coresignal`, `creatify`, `exa`, `expandi`, `hunter`, `inboxapp`, `instantly`, `leadiq`, `lemlist`, `lusha`, `outreach`, `paperclip`, `peopledatalabs`, `phantombuster`, `proxycurl`, `resend`, `salesforge`, `serper`, `smartlead`, `snovio`, `zerobounce`, `zoominfo`.

You can also bypass the default provider construction:

- `--provider-tools-factory module:callable`
- `--provider-credentials-factory FAMILY=module:callable`
- `--provider-client-factory FAMILY=module:callable`
- `--storage-backend-factory module:callable`

## Run Patterns

Run with default provider construction from the configured `--platform` families:

```powershell
harnessiq leads run `
  --agent outbound-a `
  --memory-root "$Root\memory\leads" `
  --model openai:gpt-5.4 `
  --max-cycles 40
```

Run with explicit factories and a custom storage backend:

```powershell
harnessiq leads run `
  --agent outbound-a `
  --memory-root "$Root\memory\leads" `
  --profile fast-grok `
  --provider-credentials-factory apollo=myproject.creds:create_apollo_credentials `
  --provider-credentials-factory zoominfo=myproject.creds:create_zoominfo_credentials `
  --storage-backend-factory myproject.leads:create_storage_backend `
  --runtime-param max_leads_per_icp=75 `
  --max-cycles 60
```

Shared tool controls work here too:

```powershell
harnessiq leads run `
  --agent outbound-a `
  --memory-root "$Root\memory\leads" `
  --profile fast-grok `
  --allowed-tools apollo.*,zoominfo.*,reasoning.* `
  --dynamic-tools `
  --dynamic-tool-top-k 15
```

## Inspect and Export

```powershell
harnessiq leads show --agent outbound-a --memory-root "$Root\memory\leads"
harnessiq export --ledger-path "$Root\ledger\leads.jsonl" --format json --flatten-outputs > "$Root\exports\leads.json"
harnessiq report --ledger-path "$Root\ledger\leads.jsonl" --format markdown > "$Root\exports\leads-report.md"
```

Like the Instagram harness, the Leads Agent continues from its durable state when you reuse the same `--agent` and `--memory-root`; there is no separate dedicated `--resume` flag on `harnessiq leads run`.
