# Research Sweep

`Research Sweep` is the built-in HarnessIQ harness for working through a research query, maintaining context runtime state, and producing a final report over multiple search steps.

See [README.md](./README.md) for shared install, sink, export, and reporting flows.

## Quick Facts

| Item | Value |
| --- | --- |
| Inspect command | `harnessiq inspect research_sweep` |
| CLI family | `harnessiq research-sweep` |
| Default memory root | `memory/research_sweep` |
| Providers | `serper` |
| Runtime parameters | `max_tokens`, `reset_threshold` |
| Custom parameters | `query`, `allowed_serper_operations` |
| Main outputs | `all_sites_empty`, `continuation_pointer`, `final_report`, `query`, `site_results` |

## Durable Files

The harness persists its working state under `memory/research_sweep/<agent>/`.

- `query.txt`: the saved research question.
- `additional_prompt.md`: extra operator guidance.
- `runtime_parameters.json`: saved `max_tokens` and `reset_threshold`.
- `custom_parameters.json`: saved `query` and `allowed_serper_operations`.
- `context_runtime_state.json`: durable continuation/context state between runs.

## Prepare and Configure

```powershell
$Root = Join-Path (Get-Location) 'research_ops'
New-Item -ItemType Directory -Force -Path "$Root\memory\research_sweep" | Out-Null

harnessiq research-sweep prepare --agent ai-policy --memory-root "$Root\memory\research_sweep"

harnessiq research-sweep configure `
  --agent ai-policy `
  --memory-root "$Root\memory\research_sweep" `
  --query-file .\research\query.txt `
  --additional-prompt-file .\research\notes.md `
  --runtime-param max_tokens=90000 `
  --custom-param allowed_serper_operations='[\"search\",\"scrape\"]'
```

## Credentials

Bind the Serper API key once if you want to use the built-in provider credentials flow:

```powershell
harnessiq credentials bind research_sweep `
  --agent ai-policy `
  --memory-root "$Root\memory\research_sweep" `
  --env serper.api_key=SERPER_API_KEY
```

## Run Patterns

`harnessiq research-sweep run` currently requires `--model-factory`; unlike many other harnesses, it does not expose `--model` or `--profile` today.

```powershell
harnessiq research-sweep run `
  --agent ai-policy `
  --memory-root "$Root\memory\research_sweep" `
  --model-factory myproject.models:create_research_model `
  --serper-credentials-factory myproject.creds:create_serper_credentials `
  --runtime-param reset_threshold=0.8 `
  --custom-param query='\"What changed in US AI policy this quarter?\"' `
  --sink "jsonl:$Root\ledger\research.jsonl" `
  --max-cycles 30
```

## Inspect and Export

```powershell
harnessiq research-sweep show --agent ai-policy --memory-root "$Root\memory\research_sweep"
harnessiq export --ledger-path "$Root\ledger\research.jsonl" --format json --flatten-outputs > "$Root\exports\research.json"
harnessiq report --ledger-path "$Root\ledger\research.jsonl" --format markdown > "$Root\exports\research-report.md"
```
