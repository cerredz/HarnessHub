# Email Campaign

`Email Campaign` is the built-in HarnessIQ harness for pulling a recipient batch from MongoDB, selecting the unsent records, and sending or staging campaign output through the email workflow.

See [README.md](./README.md) for shared install, model-profile, credential-binding, sink, export, and reporting flows.

## Quick Facts

| Item | Value |
| --- | --- |
| Inspect command | `harnessiq inspect email` |
| CLI family | `harnessiq email` |
| Default memory root | `memory/email` |
| Providers | `resend` |
| Runtime parameters | `max_tokens`, `reset_threshold`, `batch_size`, `recipient_limit` |
| Custom parameters | open-ended `--custom-param KEY=VALUE` payload |
| Main outputs | `campaign`, `delivery_records`, `recipient_batch` |

## Durable Files

The harness persists its working state under `memory/email/<agent>/` by default.

- `source_config.json`: MongoDB source configuration and recipient lookup settings.
- `campaign_config.json`: sender metadata plus the authored campaign body/subject.
- `sent_history.json`: append-only record of which recipients were already sent.
- `runtime_parameters.json`: persisted typed overrides for `max_tokens`, `reset_threshold`, `batch_size`, and `recipient_limit`.
- `custom_parameters.json`: open-ended custom payload that you can pass with `--custom-param`.
- `agent_identity.txt`: optional system-identity override.
- `additional_prompt.txt`: free-form extra prompt content.

## Prepare and Configure

Create the durable memory folder first:

```powershell
$Root = Join-Path (Get-Location) 'email_ops'
New-Item -ItemType Directory -Force -Path "$Root\memory\email" | Out-Null

harnessiq email prepare --agent campaign-a --memory-root "$Root\memory\email"
```

Persist the MongoDB source, campaign body, and runtime knobs:

```powershell
harnessiq email configure `
  --agent campaign-a `
  --memory-root "$Root\memory\email" `
  --mongodb-uri-env MONGODB_URI `
  --mongodb-database growth `
  --mongodb-collection prospects `
  --source-filter-text '{\"status\":\"ready_to_email\"}' `
  --email-path email `
  --name-path full_name `
  --from-address 'HarnessIQ <ops@example.com>' `
  --reply-to ops@example.com `
  --subject 'Quick intro from HarnessIQ' `
  --text-body-file .\campaigns\intro.txt `
  --html-body-file .\campaigns\intro.html `
  --runtime-param batch_size=50 `
  --runtime-param recipient_limit=200 `
  --custom-param campaign_owner='\"growth\"'
```

If you want the harness to use a different authoring voice, add:

```powershell
--agent-identity-file .\prompts\email_identity.txt `
--additional-prompt-file .\prompts\email_notes.txt
```

## Credentials

Bind the Resend API key once:

```powershell
harnessiq credentials bind email `
  --agent campaign-a `
  --memory-root "$Root\memory\email" `
  --env resend.api_key=RESEND_API_KEY
```

Validate the stored binding later:

```powershell
harnessiq credentials show email --agent campaign-a --memory-root "$Root\memory\email"
harnessiq credentials test email --agent campaign-a --memory-root "$Root\memory\email"
```

## Run Patterns

Run with an inline provider-backed model:

```powershell
harnessiq email run `
  --agent campaign-a `
  --memory-root "$Root\memory\email" `
  --model openai:gpt-5.4 `
  --max-cycles 25
```

Run with a reusable model profile and a one-off runtime override:

```powershell
harnessiq email run `
  --agent campaign-a `
  --memory-root "$Root\memory\email" `
  --profile fast-grok `
  --runtime-param batch_size=25 `
  --custom-param send_reason='\"follow_up_wave_2\"'
```

Shared safety/tool controls are available here too:

```powershell
harnessiq email run `
  --agent campaign-a `
  --memory-root "$Root\memory\email" `
  --profile fast-grok `
  --approval on-request `
  --allowed-tools reasoning.*,resend.* `
  --dynamic-tools `
  --dynamic-tool-top-k 12
```

## Inspect and Export

Preview the deduplicated unsent batch without running the full harness:

```powershell
harnessiq email get-recipients --agent campaign-a --memory-root "$Root\memory\email" --limit 20
```

Inspect the currently persisted state:

```powershell
harnessiq email show --agent campaign-a --memory-root "$Root\memory\email"
```

Export or report on ledger output after runs:

```powershell
harnessiq export --ledger-path "$Root\ledger\email.jsonl" --format csv --flatten-outputs > "$Root\exports\email.csv"
harnessiq report --ledger-path "$Root\ledger\email.jsonl" --format markdown > "$Root\exports\email-report.md"
```
