# Spawn Specialized Subagents

`Spawn Specialized Subagents` is the built-in HarnessIQ orchestration harness for breaking an objective into worker assignments, collecting worker outputs, and integrating them into a final response.

See [README.md](./README.md) for shared install, model-profile, sink, export, and reporting flows.

## Quick Facts

| Item | Value |
| --- | --- |
| Inspect command | `harnessiq inspect spawn_specialized_subagents` |
| CLI surface | `harnessiq prepare spawn_specialized_subagents`, `harnessiq run spawn_specialized_subagents`, `harnessiq show spawn_specialized_subagents` |
| Default memory root | `memory/spawn_specialized_subagents` |
| Providers | none |
| Runtime parameters | `max_tokens`, `reset_threshold` |
| Custom parameters | `objective`, `available_agent_types` |
| Main outputs | `objective`, `immediate_local_step`, `assignment_count`, `worker_output_count`, `final_response` |

## Durable Files

The harness persists its working state under `memory/spawn_specialized_subagents/<agent>/`.

- `objective.md`: the primary orchestration objective.
- `current_context.md`: current context and constraints for the orchestrator.
- `additional_prompt.md`: optional extra operator guidance.
- `plan.json`: current delegation plan, assignments, and immediate local step.
- `worker_outputs.json`: collected worker outputs awaiting or after integration.
- `integration_summary.json`: integrated result and final response.
- `execution_log.jsonl`: append-only orchestration event log.
- `README.md`: human-readable orchestration summary.
- `runtime_parameters.json`: saved `max_tokens` and `reset_threshold`.
- `custom_parameters.json`: saved `objective` and `available_agent_types`.

## Prepare

Persist the typed objective and worker archetypes through `prepare`:

```powershell
$Root = Join-Path (Get-Location) 'subagent_ops'
New-Item -ItemType Directory -Force -Path "$Root\memory\spawn_specialized_subagents" | Out-Null

harnessiq prepare spawn_specialized_subagents `
  --agent release-audit `
  --memory-root "$Root\memory\spawn_specialized_subagents" `
  --objective "Audit the release readiness of the onboarding product and produce an integration summary." `
  --available-agent-types "researcher,reviewer,qa" `
  --max-tokens 90000 `
  --reset-threshold 0.8
```

If you want to seed more background before the first run, edit `current_context.md` or `additional_prompt.md` in the prepared memory folder.

## Run Patterns

Start the orchestration run:

```powershell
harnessiq run spawn_specialized_subagents `
  --agent release-audit `
  --memory-root "$Root\memory\spawn_specialized_subagents" `
  --model openai:gpt-5.4 `
  --sink "jsonl:$Root\ledger\spawn.jsonl" `
  --max-cycles 40
```

Resume the latest persisted run payload:

```powershell
harnessiq run spawn_specialized_subagents `
  --agent release-audit `
  --memory-root "$Root\memory\spawn_specialized_subagents" `
  --resume `
  --profile fast-grok
```

Override the objective or available worker types for one run only:

```powershell
harnessiq run spawn_specialized_subagents `
  --agent release-audit `
  --memory-root "$Root\memory\spawn_specialized_subagents" `
  --profile fast-grok `
  --objective "Compare two onboarding launch plans and recommend the lower-risk option." `
  --available-agent-types "researcher,reviewer,finance" `
  --run-arg ticket='PLAT-412'
```

Shared tool controls are available here as well:

```powershell
harnessiq run spawn_specialized_subagents `
  --agent release-audit `
  --memory-root "$Root\memory\spawn_specialized_subagents" `
  --profile fast-grok `
  --approval on-request `
  --allowed-tools context.*,reasoning.*,filesystem.* `
  --dynamic-tools
```

## Inspect

```powershell
harnessiq show spawn_specialized_subagents --agent release-audit --memory-root "$Root\memory\spawn_specialized_subagents"
```

That returns the saved `plan`, `worker_outputs`, `integration_summary`, and current state `snapshot`.
