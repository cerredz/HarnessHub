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

## Live Snapshot

| Metric | Count |
| --- | --- |
| Concrete harness manifests | 7 |
| Top-level CLI commands | 18 |
| Registered CLI command paths | 131 |
| Model providers | 4 |
| Service provider packages | 26 |
| Tool-only external service surfaces | 1 |
| Built-in sink types | 9 |
| Test modules | 87 |

## Agent Matrix

| Harness | CLI | Import | Memory Root | Runtime Params | Custom Params | Providers |
| --- | --- | --- | --- | --- | --- | --- |
| Exa Outreach | `outreach` | `harnessiq.agents.exa_outreach:ExaOutreachAgent` | `memory/outreach` | max_tokens, reset_threshold | - | exa, resend |
| Instagram Keyword Discovery | `instagram` | `harnessiq.agents.instagram:InstagramKeywordDiscoveryAgent` | `memory/instagram` | max_tokens, recent_result_window, recent_search_window, reset_threshold, search_result_limit | open-ended | playwright |
| Knowt Content Creator | - | `harnessiq.agents.knowt:KnowtAgent` | `memory/knowt` | max_tokens, reset_threshold | - | creatify |
| Leads Agent | `leads` | `harnessiq.agents.leads:LeadsAgent` | `memory/leads` | max_tokens, reset_threshold, prune_search_interval, prune_token_limit, search_summary_every, search_tail_size, max_leads_per_icp | - | apollo, arcads, arxiv, attio, browser_use, coresignal, creatify, exa, expandi, inboxapp, instantly, leadiq, lemlist, lusha, outreach, paperclip, peopledatalabs, phantombuster, proxycurl, resend, salesforge, serper, smartlead, snovio, zerobounce, zoominfo |
| LinkedIn Job Applier | `linkedin` | `harnessiq.agents.linkedin:LinkedInJobApplierAgent` | `memory/linkedin` | max_tokens, reset_threshold, action_log_window, linkedin_start_url, notify_on_pause, pause_webhook | open-ended | playwright |
| Google Maps Prospecting | `prospecting` | `harnessiq.agents.prospecting:GoogleMapsProspectingAgent` | `memory/prospecting` | max_tokens, reset_threshold | qualification_threshold, summarize_at_x, max_searches_per_run, max_listings_per_search, website_inspect_enabled, sink_record_type, eval_system_prompt | playwright |
| Research Sweep | `research-sweep` | `harnessiq.agents.research_sweep:ResearchSweepAgent` | `memory/research_sweep` | max_tokens, reset_threshold | query, allowed_serper_operations | serper |

## Provider Surface

Harnessiq currently ships 4 model-provider adapters, 26 service provider packages under `harnessiq/providers/`, and 1 tool-only external service surface outside the provider package tree.

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
| harnessiq connect | confluence, discord, google_sheets, linear, notion, obsidian, slack, supabase | Configure a global output sink connection |
| harnessiq connections | list, remove, test | Inspect or manage configured sink connections |
| harnessiq credentials | bind, show, test | Manage persisted harness credential bindings |
| harnessiq export | - | Export ledger entries in a structured format |
| harnessiq inspect | exa_outreach (outreach), instagram, knowt, leads, linkedin, prospecting, research_sweep (research-sweep) | Inspect one harness manifest and generated CLI surface |
| harnessiq instagram | configure, get-emails, prepare, run, show | Manage and run the Instagram keyword discovery agent |
| harnessiq leads | configure, prepare, run, show | Manage and run the leads discovery agent |
| harnessiq linkedin | configure, init-browser, prepare, run, show | Manage and run the LinkedIn agent |
| harnessiq logs | - | Inspect the local audit ledger |
| harnessiq models | add, list | Manage reusable provider-backed model profiles |
| harnessiq outreach | configure, prepare, run, show | Manage and run the ExaOutreach agent |
| harnessiq prepare | exa_outreach (outreach), instagram, knowt, leads, linkedin, prospecting, research_sweep (research-sweep) | Prepare and persist generic config for a harness |
| harnessiq prompts | activate, clear, current, list, show, text | Inspect bundled master prompts |
| harnessiq prospecting | configure, init-browser, prepare, run, show | Manage and run the Google Maps prospecting agent |
| harnessiq report | - | Build a cross-agent report from the local ledger |
| harnessiq research-sweep | configure, prepare, run, show | Manage and run the ResearchSweepAgent harness |
| harnessiq run | exa_outreach (outreach), instagram, knowt, leads, linkedin, prospecting, research_sweep (research-sweep) | Run a harness through the platform-first CLI |
| harnessiq show | exa_outreach (outreach), instagram, knowt, leads, linkedin, prospecting, research_sweep (research-sweep) | Show persisted platform config and harness state |

## Repo Docs

- `docs/agent-runtime.md`: Runtime loop, manifests, and durable parameter sections.
- `docs/tools.md`: Tool registry composition and provider-backed tool usage.
- `docs/output-sinks.md`: Ledger/output-sink injection and sink connection commands.
- `docs/linkedin-agent.md`: LinkedIn harness usage and browser session workflow.
- `docs/leads-agent.md`: Leads harness memory model and CLI workflow.
- `artifacts/file_index.md`: Generated architecture map for the live repository.
- `artifacts/commands.md`: Generated CLI command catalog.
