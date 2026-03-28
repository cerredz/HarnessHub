# HarnessIQ CLI Skills

This directory contains packaged markdown skill files for every built-in HarnessIQ harness. Each file is a concrete CLI playbook: what the harness does, which durable files it keeps, how to prepare/configure it, how to run it with different levels of customization, and how to inspect or export the results later.

## Shared Workflow

### 1. Install HarnessIQ and choose a durable working root

Use the published package:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install harnessiq
```

Or install the local checkout while you are developing against unreleased code:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e C:\Users\422mi\HarnessHub
```

Many browser-backed harnesses also need Playwright browsers installed:

```powershell
python -m playwright install chromium
```

For each harness, create a durable root folder that will hold the harness memory, any ledger exports, and other run artifacts. The per-agent skill files below show a concrete folder layout for each harness.

### 2. Inspect the live harness contract before you configure it

The manifest-backed inspect command is the fastest way to verify the current CLI surface, providers, runtime parameters, and memory files for any built-in harness:

```powershell
harnessiq inspect instagram
harnessiq inspect mission_driven
harnessiq inspect spawn_specialized_subagents
```

Use the manifest ID with `inspect`, even when the harness also has a friendlier top-level command such as `outreach` or `research-sweep`.

### 3. Prepare memory before running

Every harness persists durable state. Dedicated command families expose `prepare` under the command family itself:

```powershell
harnessiq instagram prepare --agent ig-demo --memory-root .\memory\instagram
harnessiq leads prepare --agent outbound-a --memory-root .\memory\leads
```

Generic harnesses use the platform-first manifest surface:

```powershell
harnessiq prepare knowt --agent knowt-a --memory-root .\memory\knowt
harnessiq prepare mission_driven --agent mission-a --memory-root .\memory\mission_driven --mission-goal "Build a docs site" --mission-type app_build
```

### 4. Persist reusable credentials

When a harness depends on provider credentials, bind environment variables to the harness/profile once and reuse them later:

```powershell
harnessiq credentials bind email --agent campaign-a --memory-root .\memory\email --env resend.api_key=RESEND_API_KEY
harnessiq credentials bind knowt --agent knowt-a --memory-root .\memory\knowt --env creatify.api_id=CREATIFY_API_ID --env creatify.api_key=CREATIFY_API_KEY
```

Inspect or validate the stored bindings with:

```powershell
harnessiq credentials show email --agent campaign-a --memory-root .\memory\email
harnessiq credentials test knowt --agent knowt-a --memory-root .\memory\knowt
```

Playwright/browser-backed harnesses typically do not require API credential bindings, but they may require browser bootstrap steps such as `init-browser`.

### 5. Reuse model selection with profiles

Most run commands accept either `--model provider:model_name`, `--profile <name>`, or `--model-factory module:callable`.

Persist a reusable profile when you do not want to repeat model settings:

```powershell
harnessiq models add --name fast-grok --model grok:grok-4-1-fast-reasoning --reasoning-effort high
harnessiq models list
```

Then use it in runs:

```powershell
harnessiq linkedin run --agent candidate-a --memory-root .\memory\linkedin --profile fast-grok --browser-tools-factory myproject.browser:create_tools
```

### 6. Shared run-time controls

Across the CLI you will see the same control patterns repeatedly:

- `--runtime-param KEY=VALUE`: override one persisted typed runtime parameter for this run only.
- `--custom-param KEY=VALUE`: override one persisted typed or open-ended custom parameter for this run only when the harness supports it.
- `--sink kind:value` or `--sink kind:key=value,key=value`: add a per-run output sink override for harnesses that expose sink support.
- `--approval`, `--allowed-tools`, `--dynamic-tools`, `--dynamic-tool-candidates`, `--dynamic-tool-top-k`, `--dynamic-tool-embedding-model`: control tool approval and dynamic tool selection on supported run commands.
- `--resume` and `--run <N>`: available on the generic persisted-run harnesses such as `mission_driven` and `spawn_specialized_subagents`.

### 7. Export, report, logs, and stats

Most harnesses emit useful results into the local audit ledger. Common post-run commands:

```powershell
harnessiq export --format json --flatten-outputs --ledger-path .\ledger\instagram.jsonl
harnessiq report --format markdown --ledger-path .\ledger\instagram.jsonl
harnessiq logs
harnessiq stats summary
```

`export` supports `json`, `jsonl`, `csv`, and `markdown`. `report` supports `markdown` and `json`.

### 8. Output sink connections

If you want runs to write to shared sinks such as Linear, Slack, Notion, MongoDB, or Supabase, configure a connection once:

```powershell
harnessiq connect linear
harnessiq connections list
harnessiq connections test --help
```

Then pass per-run `--sink` overrides on harnesses that support them.

## Built-In Harness Skills

| Harness | CLI Surface | Skill File |
| --- | --- | --- |
| Exa Outreach | `harnessiq outreach ...` plus `harnessiq inspect exa_outreach` | [`exa_outreach.md`](./exa_outreach.md) |
| Email Campaign | `harnessiq email ...` plus `harnessiq inspect email` | [`email.md`](./email.md) |
| Instagram Keyword Discovery | `harnessiq instagram ...` plus `harnessiq inspect instagram` | [`instagram.md`](./instagram.md) |
| Knowt Content Creator | `harnessiq prepare/run/show knowt ...` plus `harnessiq inspect knowt` | [`knowt.md`](./knowt.md) |
| Leads Agent | `harnessiq leads ...` plus `harnessiq inspect leads` | [`leads.md`](./leads.md) |
| LinkedIn Job Applier | `harnessiq linkedin ...` plus `harnessiq inspect linkedin` | [`linkedin.md`](./linkedin.md) |
| Mission Driven | `harnessiq prepare/run/show mission_driven ...` plus `harnessiq inspect mission_driven` | [`mission_driven.md`](./mission_driven.md) |
| Google Maps Prospecting | `harnessiq prospecting ...` plus `harnessiq inspect prospecting` | [`prospecting.md`](./prospecting.md) |
| Research Sweep | `harnessiq research-sweep ...` plus `harnessiq inspect research_sweep` | [`research_sweep.md`](./research_sweep.md) |
| Spawn Specialized Subagents | `harnessiq prepare/run/show spawn_specialized_subagents ...` plus `harnessiq inspect spawn_specialized_subagents` | [`spawn_specialized_subagents.md`](./spawn_specialized_subagents.md) |
