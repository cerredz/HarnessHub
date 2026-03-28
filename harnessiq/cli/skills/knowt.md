# Knowt Content Creator

`Knowt Content Creator` is the built-in HarnessIQ content-creation harness for generating a script, an avatar description, and a durable creation log for the Knowt/TikTok-style workflow.

See [README.md](./README.md) for shared install, model-profile, credential-binding, sink, export, and reporting flows.

## Quick Facts

| Item | Value |
| --- | --- |
| Inspect command | `harnessiq inspect knowt` |
| CLI surface | `harnessiq prepare knowt`, `harnessiq run knowt`, `harnessiq show knowt` |
| Default memory root | `memory/knowt` |
| Providers | `creatify` |
| Runtime parameters | `max_tokens`, `reset_threshold` |
| Custom parameters | no typed custom parameters |
| Main outputs | `script`, `avatar_description`, `creation_log` |

## Durable Files

The harness persists its working state under `memory/knowt/<agent>/`.

- `current_script.md`: the latest generated script.
- `current_avatar_description.md`: the latest generated avatar description.
- `creation_log.jsonl`: append-only creation pipeline log.

There is no dedicated `configure` command for this harness. The generic prepare/run/show surface is the supported CLI path.

## Prepare and Credentials

```powershell
$Root = Join-Path (Get-Location) 'knowt_ops'
New-Item -ItemType Directory -Force -Path "$Root\memory\knowt" | Out-Null

harnessiq prepare knowt `
  --agent knowt-a `
  --memory-root "$Root\memory\knowt" `
  --max-tokens 90000 `
  --reset-threshold 0.85
```

Bind the Creatify credentials once:

```powershell
harnessiq credentials bind knowt `
  --agent knowt-a `
  --memory-root "$Root\memory\knowt" `
  --env creatify.api_id=CREATIFY_API_ID `
  --env creatify.api_key=CREATIFY_API_KEY
```

Inspect or validate the stored bindings:

```powershell
harnessiq credentials show knowt --agent knowt-a --memory-root "$Root\memory\knowt"
harnessiq credentials test knowt --agent knowt-a --memory-root "$Root\memory\knowt"
```

## Run Patterns

Run with an inline provider-backed model:

```powershell
harnessiq run knowt `
  --agent knowt-a `
  --memory-root "$Root\memory\knowt" `
  --model openai:gpt-5.4 `
  --sink "jsonl:$Root\ledger\knowt.jsonl" `
  --max-cycles 10
```

Run with a reusable model profile:

```powershell
harnessiq run knowt `
  --agent knowt-a `
  --memory-root "$Root\memory\knowt" `
  --profile fast-grok `
  --approval on-request `
  --allowed-tools knowt.*,creatify.*,reasoning.* `
  --dynamic-tools
```

The generic surface also supports `--model-factory`, `--run <N>`, and `--resume` if you want to reuse the last persisted run payload for the same profile.

## Inspect

```powershell
harnessiq show knowt --agent knowt-a --memory-root "$Root\memory\knowt"
```

That output summarizes the current `script`, `avatar_description`, and recent `creation_log` entries.
