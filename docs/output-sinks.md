# Output Sinks

HarnessIQ now includes a framework-level audit ledger and post-run output sink layer.

## Core Behavior

- Every terminal agent run emits a `LedgerEntry` envelope after `BaseAgent.run()` exits.
- The ledger hook runs after execution and never participates in model turns, transcript mutation, or tool execution.
- Sink failures are logged and swallowed. A completed run stays completed even if one or more sinks fail.
- The default baseline sink is append-only JSONL stored in the HarnessIQ home directory. If the preferred home path is not writable, the runtime falls back to a local `.harnessiq/` directory.

## Injection Paths

Programmatic injection:

```python
from harnessiq.agents import AgentRuntimeConfig
from harnessiq.utils import ObsidianSink, SlackSink

runtime_config = AgentRuntimeConfig(
    output_sinks=(
        ObsidianSink(vault_path="~/Documents/Vault", note_folder="Agent Runs"),
        SlackSink(webhook_url="https://hooks.slack.com/services/..."),
    )
)
```

Custom sink types can also be registered once and then resolved through the same builder path as built-ins:

```python
from harnessiq.utils import build_output_sinks, register_output_sink


class WarehouseSink:
    def __init__(self, table: str) -> None:
        self.table = table

    def on_run_complete(self, entry) -> None:
        print(self.table, entry.run_id)


register_output_sink(
    "warehouse",
    lambda config: WarehouseSink(table=str(config["table"])),
)

sinks = build_output_sinks(sink_specs=("warehouse:table=agent_runs",))
```

Global CLI injection:

```bash
harnessiq connect obsidian --vault-path ~/Documents/Vault --note-folder "Agent Runs"
harnessiq connect slack --webhook-url "https://hooks.slack.com/services/..."
harnessiq connect google_sheets \
  --client-id "<google-client-id>" \
  --client-secret "<google-client-secret>" \
  --refresh-token "<google-refresh-token>" \
  --spreadsheet-id "<sheet-id>" \
  --sheet-name "Prospecting Leads" \
  --explode-field "outputs.qualified_leads"
```

Per-run CLI injection:

```bash
harnessiq linkedin run --agent candidate-a \
  --model openai:gpt-5.4 \
  --sink "obsidian:vault_path=C:/Users/me/Vault,note_folder=Runs"
```

## Built-In Sinks

- `JSONLLedgerSink`: append-only baseline ledger
- `ObsidianSink`: one Markdown note per run
- `SlackSink`: webhook completion summary
- `DiscordSink`: webhook completion summary
- `NotionSink`: create a page in a Notion database
- `ConfluenceSink`: create a Confluence page per run
- `SupabaseSink`: insert a row into a Supabase table
- `LinearSink`: create one or more Linear issues from a run
- `GoogleSheetsSink`: append one or more rows to a Google Sheet

Use `list_output_sink_types()` to inspect the full set of built-in plus custom-registered sink names.

## Global Connections

Global sink connections are stored in `connections.json` under the HarnessIQ home directory and loaded automatically by CLI agent runs. The current commands are:

```bash
harnessiq connect <sink> ...
harnessiq connections list
harnessiq connections test <name>
harnessiq connections remove <name>
```

For `google_sheets`, the configured OAuth refresh token must have Google Sheets access. If an existing Google token was minted only for Drive scopes, re-authorize it with Sheets scope before using the sink.

## Ledger CLI

The local JSONL ledger can be queried directly:

```bash
harnessiq logs --format json
harnessiq export --agent linkedin_job_applier --format csv --flatten-outputs
harnessiq report --format markdown
```
