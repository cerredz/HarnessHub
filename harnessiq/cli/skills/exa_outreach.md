# Exa Outreach

`Exa Outreach` is the built-in HarnessIQ harness for finding leads from an Exa query and optionally selecting/sending email templates through Resend.

See [README.md](./README.md) for shared install, model-profile, credential-binding, sink, export, and reporting flows.

## Quick Facts

| Item | Value |
| --- | --- |
| Inspect command | `harnessiq inspect exa_outreach` |
| CLI family | `harnessiq outreach` |
| Default memory root | `memory/outreach` |
| Providers | `exa`, `resend` |
| Runtime parameters | `max_tokens`, `reset_threshold` |
| Custom parameters | no typed custom parameters |
| Main outputs | `search_query`, `leads_found`, `emails_sent` |

## Durable Files

The harness persists its working state under `memory/outreach/<agent>/`.

- `query_config.json`: the saved search query and runtime settings.
- `agent_identity.txt`: optional system-identity override.
- `additional_prompt.txt`: free-form extra operator guidance.
- `runs/`: run-specific durable output and bookkeeping.

## Prepare and Configure

```powershell
$Root = Join-Path (Get-Location) 'outreach_ops'
New-Item -ItemType Directory -Force -Path "$Root\memory\outreach" | Out-Null

harnessiq outreach prepare --agent outbound-a --memory-root "$Root\memory\outreach"

harnessiq outreach configure `
  --agent outbound-a `
  --memory-root "$Root\memory\outreach" `
  --query-file .\queries\series_a_revops.txt `
  --runtime-param max_tokens=90000 `
  --agent-identity-file .\prompts\outreach_identity.txt `
  --additional-prompt-file .\prompts\outreach_constraints.txt
```

`query-file` or `query-text` should describe the audience you want Exa to search for.

## Credentials and Required Factories

At minimum, a full outreach run needs Exa credentials and usually Resend credentials plus email-template data.

Reusable bindings:

```powershell
harnessiq credentials bind exa_outreach `
  --agent outbound-a `
  --memory-root "$Root\memory\outreach" `
  --env exa.api_key=EXA_API_KEY `
  --env resend.api_key=RESEND_API_KEY
```

The `run` command also requires factory hooks:

- `--exa-credentials-factory module:callable`: required.
- `--resend-credentials-factory module:callable`: required unless `--search-only`.
- `--email-data-factory module:callable`: required unless `--search-only`; returns the email-template data used by the harness.

## Run Patterns

Search-only lead discovery:

```powershell
harnessiq outreach run `
  --agent outbound-a `
  --memory-root "$Root\memory\outreach" `
  --model grok:grok-4-1-fast-reasoning `
  --exa-credentials-factory myproject.creds:create_exa_credentials `
  --search-only `
  --sink "jsonl:$Root\ledger\outreach-search.jsonl" `
  --max-cycles 30
```

Full outreach flow with email templates:

```powershell
harnessiq outreach run `
  --agent outbound-a `
  --memory-root "$Root\memory\outreach" `
  --profile fast-grok `
  --exa-credentials-factory myproject.creds:create_exa_credentials `
  --resend-credentials-factory myproject.creds:create_resend_credentials `
  --email-data-factory myproject.outreach:create_email_templates `
  --sink "jsonl:$Root\ledger\outreach.jsonl" `
  --max-cycles 50
```

You can still use the shared tool/runtime controls:

```powershell
harnessiq outreach run `
  --agent outbound-a `
  --memory-root "$Root\memory\outreach" `
  --profile fast-grok `
  --exa-credentials-factory myproject.creds:create_exa_credentials `
  --search-only `
  --approval on-request `
  --allowed-tools exa.*,reasoning.* `
  --dynamic-tools
```

## Inspect and Export

```powershell
harnessiq outreach show --agent outbound-a --memory-root "$Root\memory\outreach"
harnessiq export --ledger-path "$Root\ledger\outreach.jsonl" --format json --flatten-outputs > "$Root\exports\outreach.json"
harnessiq report --ledger-path "$Root\ledger\outreach.jsonl" --format markdown > "$Root\exports\outreach-report.md"
```
