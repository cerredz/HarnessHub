# Mission Driven

`Mission Driven` is the built-in HarnessIQ long-running mission harness for decomposing a mission goal, maintaining a durable task plan, and keeping a resumable mission artifact on disk.

See [README.md](./README.md) for shared install, model-profile, sink, export, and reporting flows.

## Quick Facts

| Item | Value |
| --- | --- |
| Inspect command | `harnessiq inspect mission_driven` |
| CLI surface | `harnessiq prepare mission_driven`, `harnessiq run mission_driven`, `harnessiq show mission_driven` |
| Default memory root | `memory/mission_driven` |
| Providers | none |
| Runtime parameters | `max_tokens`, `reset_threshold` |
| Custom parameters | `mission_goal`, `mission_type` |
| Main outputs | `mission_status`, `mission_goal`, `mission_type`, `current_task_pointer`, `next_actions`, `task_count`, `completed_task_count`, `blocked_task_count`, `artifact_count`, `file_record_count`, `research_entry_count`, `tool_call_count` |

## Durable Files

The harness persists its working state under `memory/mission_driven/<agent>/`.

- `mission.json`: mission definition and top-level status.
- `task_plan.json`: hierarchical task list and current task pointer.
- `memory_store.json`: durable fact registry.
- `decision_log.json`: decision records and rationale.
- `file_manifest.json`: files created or modified by the mission.
- `error_log.json`: blockers, failures, and retries.
- `feedback_log.json`: human input/approval records.
- `test_results.json`: verification history.
- `artifacts.json`: registered outputs and deliverables.
- `tool_call_history.json`: durable tool-call history.
- `research_log.json`: durable research findings.
- `next_actions.json`: prioritized next step queue.
- `mission_status.json`: status snapshot.
- `progress_log.jsonl`: append-only event journal.
- `README.md`: human-readable mission summary.
- `checkpoints/`: checkpoint snapshots for resumability.
- `additional_prompt.md`: optional extra operator guidance you can edit directly.
- `runtime_parameters.json`: saved `max_tokens` and `reset_threshold`.
- `custom_parameters.json`: saved `mission_goal` and `mission_type`.

## Prepare

Because this harness uses the generic manifest surface, you persist the typed mission inputs directly through `prepare`:

```powershell
$Root = Join-Path (Get-Location) 'mission_ops'
New-Item -ItemType Directory -Force -Path "$Root\memory\mission_driven" | Out-Null

harnessiq prepare mission_driven `
  --agent docs-site `
  --memory-root "$Root\memory\mission_driven" `
  --mission-goal "Create a durable documentation site for the sales engineering team." `
  --mission-type app_build `
  --max-tokens 90000 `
  --reset-threshold 0.8
```

If you want extra operator instructions beyond the typed parameters, edit `additional_prompt.md` inside the prepared memory folder before running.

## Run Patterns

Start a run from the persisted mission definition:

```powershell
harnessiq run mission_driven `
  --agent docs-site `
  --memory-root "$Root\memory\mission_driven" `
  --model openai:gpt-5.4 `
  --sink "jsonl:$Root\ledger\mission.jsonl" `
  --max-cycles 50
```

Resume the latest persisted run payload for the same mission profile:

```powershell
harnessiq run mission_driven `
  --agent docs-site `
  --memory-root "$Root\memory\mission_driven" `
  --resume `
  --profile fast-grok
```

Override typed parameters for one run only:

```powershell
harnessiq run mission_driven `
  --agent docs-site `
  --memory-root "$Root\memory\mission_driven" `
  --profile fast-grok `
  --mission-goal "Audit and improve the docs IA for the support portal." `
  --mission-type app_build `
  --run-arg checkpoint_label='before_handoff'
```

Shared tool controls are also available:

```powershell
harnessiq run mission_driven `
  --agent docs-site `
  --memory-root "$Root\memory\mission_driven" `
  --profile fast-grok `
  --approval on-request `
  --allowed-tools context.*,reasoning.*,filesystem.* `
  --dynamic-tools
```

## Inspect

```powershell
harnessiq show mission_driven --agent docs-site --memory-root "$Root\memory\mission_driven"
```

That returns the current `mission`, `task_plan`, state `snapshot`, and saved `readme`.
