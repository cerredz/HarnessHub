# Harnessiq

Harnessiq is a Python SDK for building durable, tool-using agents with manifest-backed harnesses, catalog-driven tool composition, provider-backed service surfaces, post-run output sinks, and a scriptable CLI.

The inventory tables and SDK examples below are generated from live repository code by `python scripts/sync_repo_docs.py`.

## Install

```bash
pip install harnessiq
```

For local development from this repository:

```bash
pip install -e .
```

## Quick Start

```python
from harnessiq.tools import ECHO_TEXT, create_builtin_registry

registry = create_builtin_registry()
result = registry.execute(ECHO_TEXT, {"text": "hello"})
print(result.output)
```

## SDK Surface

Harnessiq is usable as a library even when you are not driving it through the CLI. The primary SDK layers are:

| Module | Purpose |
| --- | --- |
| `harnessiq.agents` | Provider-agnostic runtime bases, concrete harnesses, manifests, and durable memory helpers. |
| `harnessiq/toolset/` | Static tool-catalog and dynamic-tool-selection infrastructure layered beneath the executable tool registries. |
| `harnessiq.tools` | Executable tool registries plus built-in tool families and provider-backed tool factories. |
| `harnessiq.providers` | Model adapters, external service clients, output-sink transports, and Playwright/browser runtimes. |
| `harnessiq.utils` | Agent instance ids, run storage, ledger export/report helpers, stats projection, and built-in sinks. |
| `harnessiq.master_prompts` | Bundled prompt assets and the prompt registry used to load them programmatically. |

The current repository snapshot includes 10 concrete harness manifests, 27 service provider packages, 1 tool-only external service surface, and 10 built-in output sink types.

- Manifest-backed harnesses with durable memory roots and persisted runtime/custom parameter surfaces.
- Static tool registries plus optional dynamic per-turn narrowing through the tool-selection layer.
- Provider-backed request tools for model providers, research/search APIs, CRM/outbound platforms, browser automation, creative generation, and delivery systems.
- Post-run audit ledger exports, sink connections, and stats snapshots that stay outside the model loop.
- Google Cloud deployment support for running manifest-backed harnesses as Cloud Run jobs while preserving harness-native durable state.

## Registry Composition Example

Compose built-ins with provider-backed request tools by constructing a `ToolRegistry` directly.

```python
from harnessiq.tools import ToolRegistry, create_general_purpose_tools
from harnessiq.tools.exa import create_exa_tools
from harnessiq.providers.exa.client import ExaCredentials

registry = ToolRegistry([
    *create_general_purpose_tools(),
    *create_exa_tools(
        credentials=ExaCredentials(api_key="exa_..."),
        allowed_operations=("search", "get_contents"),
    ),
])

print(registry.keys())
result = registry.execute("text.normalize_whitespace", {"text": "  too   much   space  "})
print(result.output)
```

## Custom Tool Example

You can define strict-schema custom tools and compose them into a fixed runtime registry.

```python
from harnessiq.shared.tools import RegisteredTool, ToolDefinition
from harnessiq.tools import ToolRegistry, create_builtin_registry

slugify_tool = RegisteredTool(
    definition=ToolDefinition(
        key="custom.slugify",
        name="slugify",
        description="Normalize text into a URL slug.",
        input_schema={
            "type": "object",
            "properties": {"text": {"type": "string", "description": "Input text to normalize."}},
            "required": ["text"],
            "additionalProperties": False,
        },
    ),
    handler=lambda args: {"slug": str(args["text"]).strip().lower().replace(" ", "-")},
)

builtins = create_builtin_registry()
registry = ToolRegistry([*builtins.select(builtins.keys()), slugify_tool])
result = registry.execute("custom.slugify", {"text": "HarnessIQ SDK"})
print(result.output["slug"])  # "harnessiq-sdk"
```

The static toolset layer can still describe or retrieve tool families, but `ToolRegistry` is the direct execution surface used by harnesses and custom SDK code.

## Runtime, Hooks, and Output Sink Example

`AgentRuntimeConfig` is where SDK consumers tune token limits, allowed tool patterns, dynamic selection, hooks, output sinks, tracing, and session identity.

```python
from harnessiq.agents import AgentRuntimeConfig
from harnessiq.utils import JSONLLedgerSink, ObsidianSink, list_output_sink_types

runtime = AgentRuntimeConfig(
    max_tokens=80_000,
    reset_threshold=0.9,
    allowed_tools=("filesystem.*", "reason.*", "exa.request"),
    output_sinks=(
        JSONLLedgerSink(path="./artifacts/runs.jsonl"),
        ObsidianSink(vault_path="~/Documents/Vault", note_folder="HarnessIQ Runs"),
    ),
    include_default_output_sink=False,
)

print(runtime.allowed_tools)
print(list_output_sink_types())
```

## Bundled Prompt Example

Bundled prompts are also addressable through a registry API, so you can inspect or reuse prompt assets directly from Python.

```python
from harnessiq.master_prompts.registry import MasterPromptRegistry

registry = MasterPromptRegistry()
print(registry.keys())
prompt = registry.get("create_master_prompts")
print(prompt.title)
print(prompt.description)
```

## Dynamic Tool Selection

Harnessiq keeps the static tool path by default. When you need to narrow a large tool surface per turn, opt into dynamic tool selection through `AgentRuntimeConfig.tool_selection` or the `--dynamic-tools` CLI flags.

See `docs/dynamic-tool-selection.md` for the runtime contract, CLI flags, embedding-model configuration, and the boundary between existing tool keys and Python-only custom callables.

## Google Cloud Integration

Harnessiq ships a dedicated Google Cloud deployment surface for running manifest-backed harnesses as Cloud Run jobs without introducing a second runtime model.

- `harnessiq gcloud init` saves one JSON deploy config per logical agent under `~/.harnessiq/gcloud/<agent>.json`, including region, Artifact Registry, Cloud Run, Scheduler, model-selection, sink, and parameter settings.
- `harnessiq gcloud health` and `harnessiq gcloud credentials check` validate operator prerequisites such as the `gcloud` CLI, active auth, ADC, required APIs, and Secret Manager access.
- `harnessiq gcloud credentials ...` reuses repo-local harness credential bindings and syncs runtime secrets into Secret Manager through `status`, `sync`, `set`, and `remove` flows.
- Manifest-backed deploy specs are derived from the harness manifest plus saved profile state, so remote runs preserve model selection, runtime/custom parameters, adapter arguments, sink specs, provider families, and declared durable memory files.
- `build`, `deploy`, `schedule`, and `execute` cover the Cloud Build, Cloud Run Jobs, and Cloud Scheduler lifecycle, while `logs` and `cost` provide runtime observability and monthly cost estimation.
- The Cloud Run runtime wrapper syncs the harness memory directory to GCS before and after execution, preserving harness-native durable state rather than flattening everything into one blob.
- The GCloud command family emits JSON and supports `--dry-run` on the mutating operations, so it stays scriptable in CI and operator tooling.

## Live Snapshot

| Metric | Count |
| --- | --- |
| Concrete harness manifests | 10 |
| Top-level CLI commands | 24 |
| Registered CLI command paths | 199 |
| Model providers | 4 |
| Service provider packages | 27 |
| Tool-only external service surfaces | 1 |
| Built-in sink types | 10 |
| Test modules | 138 |

## Agent Matrix

| Harness | CLI | Import | Memory Root | Runtime Params | Custom Params | Providers |
| --- | --- | --- | --- | --- | --- | --- |
| Exa Outreach | `outreach` | `harnessiq.agents.exa_outreach:ExaOutreachAgent` | `memory/outreach` | max_tokens, reset_threshold | - | exa, resend |
| Email Campaign | `email` | `harnessiq.agents.email:EmailCampaignAgent` | `memory/email` | max_tokens, reset_threshold, batch_size, recipient_limit | open-ended | resend |
| Instagram Keyword Discovery | `instagram` | `harnessiq.agents.instagram:InstagramKeywordDiscoveryAgent` | `memory/instagram` | max_tokens, recent_result_window, recent_search_window, reset_threshold, search_result_limit | open-ended | playwright |
| Knowt Content Creator | - | `harnessiq.agents.knowt:KnowtAgent` | `memory/knowt` | max_tokens, reset_threshold | - | creatify |
| Leads Agent | `leads` | `harnessiq.agents.leads:LeadsAgent` | `memory/leads` | max_tokens, reset_threshold, prune_search_interval, prune_token_limit, search_summary_every, search_tail_size, max_leads_per_icp | - | apollo, arcads, arxiv, attio, browser_use, coresignal, creatify, exa, expandi, hunter, inboxapp, instantly, leadiq, lemlist, lusha, outreach, paperclip, peopledatalabs, phantombuster, proxycurl, resend, salesforge, serper, smartlead, snovio, zerobounce, zoominfo |
| LinkedIn Job Applier | `linkedin` | `harnessiq.agents.linkedin:LinkedInJobApplierAgent` | `memory/linkedin` | max_tokens, reset_threshold, action_log_window, linkedin_start_url, notify_on_pause, pause_webhook | open-ended | playwright |
| Mission Driven | - | `harnessiq.agents.mission_driven:MissionDrivenAgent` | `memory/mission_driven` | max_tokens, reset_threshold | mission_goal, mission_type | - |
| Google Maps Prospecting | `prospecting` | `harnessiq.agents.prospecting:GoogleMapsProspectingAgent` | `memory/prospecting` | max_tokens, reset_threshold | qualification_threshold, summarize_at_x, max_searches_per_run, max_listings_per_search, website_inspect_enabled, sink_record_type, eval_system_prompt | playwright |
| Research Sweep | `research-sweep` | `harnessiq.agents.research_sweep:ResearchSweepAgent` | `memory/research_sweep` | max_tokens, reset_threshold | query, allowed_serper_operations | serper |
| Spawn Specialized Subagents | - | `harnessiq.agents.spawn_specialized_subagents:SpawnSpecializedSubagentsAgent` | `memory/spawn_specialized_subagents` | max_tokens, reset_threshold | objective, available_agent_types | - |

## Provider Surface

Harnessiq currently ships 4 model-provider adapters, 27 service provider packages under `harnessiq/providers/`, and 1 tool-only external service surface outside the provider package tree.

### Model Providers

| Provider | Package |
| --- | --- |
| anthropic | `harnessiq/providers/anthropic/` |
| openai | `harnessiq/providers/openai/` |
| grok | `harnessiq/providers/grok/` |
| gemini | `harnessiq/providers/gemini/` |

### Service Providers

| Family | Ops | Provider Package | Tool Factory |
| --- | --- | --- | --- |
| apollo | 13 | `harnessiq/providers/apollo` | `harnessiq/tools/apollo/operations.py` |
| arcads | 10 | `harnessiq/providers/arcads` | `harnessiq/tools/arcads/operations.py` |
| arxiv | 4 | `harnessiq/providers/arxiv` | `harnessiq/tools/arxiv/operations.py` |
| attio | 7 | `harnessiq/providers/attio` | `harnessiq/tools/attio/operations.py` |
| browser_use | 43 | `harnessiq/providers/browser_use` | `harnessiq/tools/browser_use/operations.py` |
| coresignal | 9 | `harnessiq/providers/coresignal` | `harnessiq/tools/coresignal/operations.py` |
| creatify | 58 | `harnessiq/providers/creatify` | `harnessiq/tools/creatify/operations.py` |
| exa | 15 | `harnessiq/providers/exa` | `harnessiq/tools/exa/operations.py` |
| expandi | 22 | `harnessiq/providers/expandi` | `harnessiq/tools/expandi/operations.py` |
| google_drive | 10 | `harnessiq/providers/google_drive` | `harnessiq/tools/google_drive/operations.py` |
| hunter | 14 | `harnessiq/providers/hunter` | `harnessiq/tools/hunter/operations.py` |
| inboxapp | 9 | `harnessiq/providers/inboxapp` | `harnessiq/tools/inboxapp/operations.py` |
| instantly | 75 | `harnessiq/providers/instantly` | `harnessiq/tools/instantly/operations.py` |
| leadiq | 12 | `harnessiq/providers/leadiq` | `harnessiq/tools/leadiq/operations.py` |
| lemlist | 34 | `harnessiq/providers/lemlist` | `harnessiq/tools/lemlist/operations.py` |
| lusha | 40 | `harnessiq/providers/lusha` | `harnessiq/tools/lusha/operations.py` |
| outreach | 65 | `harnessiq/providers/outreach` | `harnessiq/tools/outreach/operations.py` |
| paperclip | 48 | `harnessiq/providers/paperclip` | `harnessiq/tools/paperclip/operations.py` |
| peopledatalabs | 11 | `harnessiq/providers/peopledatalabs` | `harnessiq/tools/peopledatalabs/operations.py` |
| phantombuster | 15 | `harnessiq/providers/phantombuster` | `harnessiq/tools/phantombuster/operations.py` |
| proxycurl | 11 | `harnessiq/providers/proxycurl` | `harnessiq/tools/proxycurl/operations.py` |
| salesforge | 22 | `harnessiq/providers/salesforge` | `harnessiq/tools/salesforge/operations.py` |
| serper | 10 | `harnessiq/providers/serper` | `harnessiq/tools/serper/operations.py` |
| smartlead | 48 | `harnessiq/providers/smartlead` | `harnessiq/tools/smartlead/operations.py` |
| snovio | 23 | `harnessiq/providers/snovio` | `harnessiq/tools/snovio/operations.py` |
| zerobounce | 22 | `harnessiq/providers/zerobounce` | `harnessiq/tools/zerobounce/operations.py` |
| zoominfo | 12 | `harnessiq/providers/zoominfo` | `harnessiq/tools/zoominfo/operations.py` |

### Tool-Only External Surfaces

| Family | Ops | Tool Surface |
| --- | --- | --- |
| resend | 64 | `harnessiq/tools/resend.py` |

## CLI

The generated command catalog lives at `artifacts/commands.md`. Use it as the high-signal reference for the live command tree.

| Command | Direct Subcommands | Description |
| --- | --- | --- |
| harnessiq agents | list, show | Inspect registered harness manifests |
| harnessiq connect | confluence, discord, google_sheets, linear, mongodb, notion, obsidian, slack, supabase | Configure a global output sink connection |
| harnessiq connections | list, remove, test | Inspect or manage configured sink connections |
| harnessiq credentials | bind, show, test | Manage persisted harness credential bindings |
| harnessiq email | configure, get-recipients, prepare, run, show | Manage and run the email campaign agent |
| harnessiq export | - | Export ledger entries in a structured format |
| harnessiq gcloud | build, cost, credentials, deploy, execute, health, init, logs, schedule | Manage Google Cloud deployment configuration and operations |
| harnessiq inspect | email, exa_outreach (outreach), instagram, knowt, leads, linkedin, mission_driven, prospecting, research_sweep (research-sweep), spawn_specialized_subagents | Inspect one harness manifest and generated CLI surface |
| harnessiq instagram | configure, get-emails, prepare, run, show | Manage and run the Instagram keyword discovery agent |
| harnessiq leads | configure, prepare, run, show | Manage and run the leads discovery agent |
| harnessiq linkedin | configure, init-browser, prepare, run, show | Manage and run the LinkedIn agent |
| harnessiq logs | - | Inspect the local audit ledger |
| harnessiq models | add, export, import, list, remove, show, validate | Manage reusable provider-backed model profiles |
| harnessiq outreach | configure, prepare, run, show | Manage and run the ExaOutreach agent |
| harnessiq prepare | email, exa_outreach (outreach), instagram, knowt, leads, linkedin, mission_driven, prospecting, research_sweep (research-sweep), spawn_specialized_subagents | Prepare and persist generic config for a harness |
| harnessiq prompts | activate, clear, current, list, search, show, text | Inspect bundled master prompts |
| harnessiq prospecting | configure, init-browser, prepare, run, show | Manage and run the Google Maps prospecting agent |
| harnessiq providers | list, show | Inspect provider-backed tool families |
| harnessiq report | - | Build a cross-agent report from the local ledger |
| harnessiq research-sweep | configure, prepare, run, show | Manage and run the ResearchSweepAgent harness |
| harnessiq run | email, exa_outreach (outreach), instagram, knowt, leads, linkedin, mission_driven, prospecting, research_sweep (research-sweep), spawn_specialized_subagents | Run a harness through the platform-first CLI |
| harnessiq show | email, exa_outreach (outreach), instagram, knowt, leads, linkedin, mission_driven, prospecting, research_sweep (research-sweep), spawn_specialized_subagents | Show persisted platform config and harness state |
| harnessiq stats | agent, export, instance, rebuild, session, summary | Inspect local stats and analytics snapshots |
| harnessiq tools | families, import, list, show, validate | Inspect the registered HarnessIQ tool catalog |

## Repo Docs

- `docs/agent-runtime.md`: Runtime loop, manifests, and durable parameter sections.
- `docs/dynamic-tool-selection.md`: Opt-in per-turn tool narrowing on top of the static runtime tool surface.
- `docs/gcloud.md`: Google Cloud deployment workflow, credential sync, and GCS-backed runtime memory continuity.
- `docs/tools.md`: Tool registry composition and provider-backed tool usage.
- `docs/output-sinks.md`: Ledger/output-sink injection and sink connection commands.
- `docs/linkedin-agent.md`: LinkedIn harness usage and browser session workflow.
- `docs/leads-agent.md`: Leads harness memory model and CLI workflow.
- `artifacts/file_index.md`: Generated architecture map for the live repository.
- `artifacts/commands.md`: Generated CLI command catalog.
