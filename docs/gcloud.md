# GCP Workflow

HarnessIQ's Google Cloud support follows the repository's existing manifest-backed and JSON-first conventions. The `harnessiq gcloud ...` commands manage deployment state, but they reuse the same harness manifests, harness profiles, and repo-local credential bindings that power the local platform-first workflow.

## What The GCP Layer Does

- Stores one deploy config per logical agent in `~/.harnessiq/gcloud/<agent>.json`
- Reuses repo-local harness credential bindings instead of introducing a second credential mapping format
- Builds and deploys a Cloud Run job from a manifest-backed deploy spec
- Syncs the harness memory directory to GCS before and after cloud execution so scheduled runs keep continuity

## Auth And Credentials

There are two different authentication surfaces:

1. Local Google Cloud auth for the operator
   - `gcloud auth login`
   - `gcloud auth application-default login`

2. Harness runtime credentials for the deployed job
   - repo-local binding inputs such as `ANTHROPIC_API_KEY`, `LINKEDIN_EMAIL`, `LINKEDIN_PASSWORD`, or other provider env vars
   - synchronized into Secret Manager by `harnessiq gcloud credentials sync`

The GCP layer intentionally reuses the repository's credential binding system. If a harness already resolves credentials locally through `harnessiq credentials bind ...`, the cloud deployment flow uses that same binding as the source of truth.

## Init And Credential Sync

Initialize one agent-specific deploy config:

```bash
harnessiq gcloud init \
  --agent candidate-a \
  --project-id proj-123 \
  --region us-central1 \
  --manifest-id research_sweep \
  --non-interactive
```

Inspect local-vs-GCP credential state:

```bash
harnessiq gcloud credentials status --agent candidate-a
```

Push repo-local credentials into Secret Manager:

```bash
harnessiq gcloud credentials sync --agent candidate-a --non-interactive
```

Check only the operator auth prerequisites:

```bash
harnessiq gcloud credentials check
```

All of these commands emit JSON. That is intentional and consistent with the rest of the HarnessIQ CLI.

## Build, Deploy, And Schedule

Build the configured container image:

```bash
harnessiq gcloud build --agent candidate-a --source-dir .
```

Deploy or update the Cloud Run job:

```bash
harnessiq gcloud deploy --agent candidate-a
```

Create or update the Cloud Scheduler trigger:

```bash
harnessiq gcloud schedule \
  --agent candidate-a \
  --cron "0 */4 * * *" \
  --timezone "America/Indianapolis"
```

Trigger a run manually:

```bash
harnessiq gcloud execute --agent candidate-a --wait
```

Read logs and inspect cost estimates:

```bash
harnessiq gcloud logs --agent candidate-a --limit 50 --freshness 1d
harnessiq gcloud cost --agent candidate-a
```

## Memory Continuity In Cloud Run

HarnessIQ does not flatten every harness into one shared `memory.json`. Instead, the cloud runtime syncs the harness memory directory itself.

The runtime wrapper:

1. resolves the saved GCP config and manifest-backed deploy spec
2. downloads the configured harness memory folder from GCS
3. runs the correct manifest-backed harness through the existing adapter flow
4. uploads the updated memory folder back to GCS

This preserves `.harnessiq-profile.json` plus harness-native files such as:

- `memory/research_sweep/<agent>/query.txt`
- `memory/research_sweep/<agent>/context_runtime_state.json`
- `memory/instagram/<agent>/lead_database.json`
- `memory/instagram/<agent>/icps/*.json`

The GCS object layout is derived from the serialized memory path and stored under the deployment bucket's `runtime-state/` prefix.

## Dry Runs

Use `--dry-run` on the deploy-side commands when you want the provider layer to render commands without mutating GCP resources:

```bash
harnessiq gcloud build --agent candidate-a --dry-run
harnessiq gcloud deploy --agent candidate-a --dry-run
harnessiq gcloud schedule --agent candidate-a --dry-run
harnessiq gcloud execute --agent candidate-a --dry-run
```

The JSON payloads still include the resolved agent, project, region, and command results, so they are safe to script against in CI or operator tooling.
