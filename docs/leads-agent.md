# Leads Agent

`LeadsAgent` is a rotating multi-ICP prospect discovery harness. It keeps one durable memory folder, swaps the active ICP in and out of the parameter sections, persists each search attempt, compacts older searches into summaries, and deduplicates saved leads through a pluggable storage backend.

## What It Persists

Under `memory_path/` the agent stores:

- `run_config.json`: company background, ICP list, platform list, and search-compaction settings
- `run_state.json`: current run id, active ICP index, and lifecycle status
- `icps/*.json`: per-ICP search history, summaries, saved lead keys, and completion state
- `lead_storage/saved_leads.json`: cross-run deduplicated lead records
- `lead_storage/runs/`: default filesystem backend event logs

This separation matters because transcript pruning only removes ephemeral conversation history. Durable search state stays outside the model transcript and is re-injected as parameter sections on every turn.

## SDK Example

```python
from pathlib import Path

from harnessiq.agents import LeadsAgent
from harnessiq.providers.apollo.client import ApolloCredentials

agent = LeadsAgent(
    model=model,
    company_background="We sell outbound infrastructure to B2B SaaS revenue teams.",
    icps=(
        "VP Sales at Series A SaaS companies",
        "Head of Revenue at 50-200 employee SaaS companies",
    ),
    platforms=("apollo",),
    provider_credentials={
        "apollo": ApolloCredentials(api_key="apollo_..."),
    },
    memory_path=Path("./memory/leads/campaign-a"),
    prune_search_interval=25,
    prune_token_limit=60_000,
    search_summary_every=250,
    search_tail_size=15,
    max_leads_per_icp=50,
)

result = agent.run(max_cycles=40)
print(result.status)
```

The harness automatically injects four internal tools:

- `leads.log_search`
- `leads.compact_search_history`
- `leads.check_seen_lead`
- `leads.save_leads`

## Storage Backend Injection

The default backend is `FileSystemLeadsStorageBackend`, but any object satisfying the `LeadsStorageBackend` protocol can be supplied:

```python
from harnessiq.shared.leads import LeadRecord, LeadSaveResult

class MyLeadWarehouse:
    def start_run(self, run_id: str, metadata: dict) -> None: ...
    def finish_run(self, run_id: str, completed_at: str) -> None: ...
    def save_leads(self, run_id: str, icp_key: str, leads, metadata=None) -> tuple[LeadSaveResult, ...]: ...
    def has_seen_lead(self, dedupe_key: str) -> bool: ...
    def list_leads(self, *, icp_key: str | None = None) -> list[LeadRecord]: ...
    def current_run_id(self) -> str | None: ...

agent = LeadsAgent(..., storage_backend=MyLeadWarehouse())
```

## CLI Workflow

Prepare memory:

```bash
harnessiq leads prepare \
  --agent campaign-a \
  --memory-root ./memory/leads
```

Persist configuration:

```bash
harnessiq leads configure \
  --agent campaign-a \
  --memory-root ./memory/leads \
  --company-background-file ./company_background.md \
  --icp-text "VP Sales at Series A SaaS companies" \
  --icp-text "Head of Revenue at 50-200 employee SaaS companies" \
  --platform apollo \
  --runtime-param search_summary_every=250 \
  --runtime-param search_tail_size=15 \
  --runtime-param max_tokens=80000 \
  --runtime-param prune_search_interval=25
```

Run the agent from persisted state:

```bash
harnessiq leads run \
  --agent campaign-a \
  --memory-root ./memory/leads \
  --model openai:gpt-5.4 \
  --provider-credentials-factory apollo=my_module:create_apollo_credentials \
  --storage-backend-factory my_module:create_leads_storage_backend \
  --max-cycles 40
```

If `--provider-tools-factory` is omitted, the CLI constructs provider tools from the configured `platforms` list plus any injected provider credentials or prebuilt clients. Use `harnessiq models add ...` plus `--profile <name>` when you want reusable model defaults instead of repeating them inline.
