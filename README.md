# Harnessiq

Harnessiq is a Python SDK for building durable, tool-using agents with manifest-backed harnesses, provider-backed tool factories, and a scriptable CLI.

The agent, provider, and CLI tables below are generated from live repository code by `python scripts/sync_repo_docs.py`.

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
| Top-level CLI commands | 21 |
| Registered CLI command paths | 181 |
| Model providers | 4 |
| Service provider packages | 27 |
| Tool-only external service surfaces | 1 |
| Built-in sink types | 10 |
| Test modules | 124 |

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
| harnessiq models | add, list | Manage reusable provider-backed model profiles |
| harnessiq outreach | configure, prepare, run, show | Manage and run the ExaOutreach agent |
| harnessiq prepare | email, exa_outreach (outreach), instagram, knowt, leads, linkedin, mission_driven, prospecting, research_sweep (research-sweep), spawn_specialized_subagents | Prepare and persist generic config for a harness |
| harnessiq prompts | activate, clear, current, list, show, text | Inspect bundled master prompts |
| harnessiq prospecting | configure, init-browser, prepare, run, show | Manage and run the Google Maps prospecting agent |
| harnessiq report | - | Build a cross-agent report from the local ledger |
| harnessiq research-sweep | configure, prepare, run, show | Manage and run the ResearchSweepAgent harness |
| harnessiq run | email, exa_outreach (outreach), instagram, knowt, leads, linkedin, mission_driven, prospecting, research_sweep (research-sweep), spawn_specialized_subagents | Run a harness through the platform-first CLI |
| harnessiq show | email, exa_outreach (outreach), instagram, knowt, leads, linkedin, mission_driven, prospecting, research_sweep (research-sweep), spawn_specialized_subagents | Show persisted platform config and harness state |
| harnessiq stats | agent, export, instance, rebuild, session, summary | Inspect local stats and analytics snapshots |

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
