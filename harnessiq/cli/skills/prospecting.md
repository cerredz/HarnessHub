# Google Maps Prospecting

`Google Maps Prospecting` is the built-in HarnessIQ harness for finding local businesses, evaluating them against a company description, and persisting qualified leads over time.

See [README.md](./README.md) for shared install, model-profile, credential-binding, sink, export, and reporting flows.

## Quick Facts

| Item | Value |
| --- | --- |
| Inspect command | `harnessiq inspect prospecting` |
| CLI family | `harnessiq prospecting` |
| Default memory root | `memory/prospecting` |
| Providers | `playwright` |
| Runtime parameters | `max_tokens`, `reset_threshold` |
| Custom parameters | `qualification_threshold`, `summarize_at_x`, `max_searches_per_run`, `max_listings_per_search`, `website_inspect_enabled`, `sink_record_type`, `eval_system_prompt` |
| Main outputs | `company_description`, `qualified_leads`, `searches_completed`, `summary`, `counts` |

## Durable Files

The harness persists its working state under `memory/prospecting/<agent>/`.

- `company_description.md`: durable description of the company or offer you are prospecting for.
- `agent_identity.md`: optional identity override.
- `additional_prompt.md`: free-form extra prompt guidance.
- `runtime_parameters.json`: saved `max_tokens` and `reset_threshold`.
- `custom_parameters.json`: saved `qualification_threshold`, `summarize_at_x`, `max_searches_per_run`, `max_listings_per_search`, `website_inspect_enabled`, `sink_record_type`, and `eval_system_prompt`.
- `prospecting_state.json`: current search/run state.
- `qualified_leads.jsonl`: append-only qualified lead records.
- `browser-data/`: persisted browser session data.

## Prepare, Browser Bootstrap, and Configure

```powershell
$Root = Join-Path (Get-Location) 'prospecting_ops'
New-Item -ItemType Directory -Force -Path "$Root\memory\prospecting" | Out-Null

harnessiq prospecting prepare --agent chicago-restaurants --memory-root "$Root\memory\prospecting"

harnessiq prospecting init-browser --agent chicago-restaurants --memory-root "$Root\memory\prospecting" --channel chrome

harnessiq prospecting configure `
  --agent chicago-restaurants `
  --memory-root "$Root\memory\prospecting" `
  --company-description-file .\prospecting\company.md `
  --agent-identity-file .\prospecting\identity.md `
  --additional-prompt-file .\prospecting\notes.md `
  --eval-system-prompt-file .\prospecting\eval_prompt.md `
  --custom-param qualification_threshold=0.8 `
  --custom-param summarize_at_x=25 `
  --custom-param max_searches_per_run=10 `
  --custom-param max_listings_per_search=20 `
  --custom-param website_inspect_enabled=true `
  --custom-param sink_record_type='\"qualified_lead\"'
```

## Run Patterns

Run with the default Google Maps Playwright browser-tools factory:

```powershell
harnessiq prospecting run `
  --agent chicago-restaurants `
  --memory-root "$Root\memory\prospecting" `
  --model openai:gpt-5.4 `
  --browser-tools-factory harnessiq.integrations.google_maps_playwright:create_browser_tools `
  --sink "jsonl:$Root\ledger\prospecting.jsonl" `
  --max-cycles 40
```

Run with a reusable model profile and per-run custom overrides:

```powershell
harnessiq prospecting run `
  --agent chicago-restaurants `
  --memory-root "$Root\memory\prospecting" `
  --profile fast-grok `
  --custom-param qualification_threshold=0.9 `
  --custom-param max_searches_per_run=5 `
  --sink "jsonl:$Root\ledger\prospecting-high-confidence.jsonl"
```

Shared tool controls work here too:

```powershell
harnessiq prospecting run `
  --agent chicago-restaurants `
  --memory-root "$Root\memory\prospecting" `
  --profile fast-grok `
  --approval on-request `
  --allowed-tools prospecting.*,browser_use.*,reasoning.* `
  --dynamic-tools
```

## Inspect and Export

```powershell
harnessiq prospecting show --agent chicago-restaurants --memory-root "$Root\memory\prospecting"
harnessiq export --ledger-path "$Root\ledger\prospecting.jsonl" --format csv --flatten-outputs > "$Root\exports\prospecting.csv"
harnessiq report --ledger-path "$Root\ledger\prospecting.jsonl" --format markdown > "$Root\exports\prospecting-report.md"
```
