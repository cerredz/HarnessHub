# Harnessiq

Harnessiq is a Python SDK for building durable, tool-using agents with manifest-backed harnesses, provider-backed tool factories, and a scriptable CLI.

The agent, provider, and CLI tables below are generated from live repository code by `python scripts/sync_repo_docs.py`.
---

## Table of Contents

- [Install](#install)
- [Quick Start](#quick-start)
- [Agent Runtime](#agent-runtime)
  - [BaseAgent](#baseagent)
  - [BaseEmailAgent](#baseemailagent)
  - [Provider Base Harnesses](#provider-base-harnesses)
- [Concrete Agents](#concrete-agents)
  - [LinkedInJobApplierAgent](#linkedinjobapplieragent)
  - [KnowtAgent](#knowtagent)
  - [ExaOutreachAgent](#exaoutreachagent)
  - [LeadsAgent](#leadsagent)
- [Tool Layer](#tool-layer)
  - [Built-in Tools](#built-in-tools)
  - [Context Compaction Tools](#context-compaction-tools)
  - [Filesystem Tools](#filesystem-tools)
  - [General-Purpose Tools](#general-purpose-tools)
  - [Prompting Tools](#prompting-tools)
  - [Reasoning Tools](#reasoning-tools)
  - [Resend Email Tools](#resend-email-tools)
- [External Service Provider Tools](#external-service-provider-tools)
  - [AI / LLM Providers](#ai--llm-providers)
  - [Search and Intelligence Providers](#search-and-intelligence-providers)
  - [Sales Engagement Providers](#sales-engagement-providers)
  - [Video and Creative Providers](#video-and-creative-providers)
- [Master Prompts](#master-prompts)
- [CLI](#cli)
  - [LinkedIn Commands](#linkedin-commands)
  - [Leads Commands](#leads-commands)
  - [Outreach Commands](#outreach-commands)
- [Configuration and Credentials](#configuration-and-credentials)
- [Further Reading](#further-reading)

---

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
| Concrete harness manifests | 6 |
| Top-level CLI commands | 15 |
| Registered CLI command paths | 101 |
| Model providers | 4 |
| Service provider packages | 25 |
| Tool-only external service surfaces | 1 |
| Built-in sink types | 8 |
| Test modules | 71 |

## Agent Matrix

| Harness | CLI | Import | Memory Root | Runtime Params | Custom Params | Providers |
| --- | --- | --- | --- | --- | --- | --- |
| Exa Outreach | `outreach` | `harnessiq.agents.exa_outreach:ExaOutreachAgent` | `memory/outreach` | max_tokens, reset_threshold | - | exa, resend |
| Instagram Keyword Discovery | `instagram` | `harnessiq.agents.instagram:InstagramKeywordDiscoveryAgent` | `memory/instagram` | max_tokens, recent_result_window, recent_search_window, reset_threshold, search_result_limit | - | playwright |
| Knowt Content Creator | - | `harnessiq.agents.knowt:KnowtAgent` | `memory/knowt` | max_tokens, reset_threshold | - | creatify |
| Leads Agent | `leads` | `harnessiq.agents.leads:LeadsAgent` | `memory/leads` | max_tokens, reset_threshold, prune_search_interval, prune_token_limit, search_summary_every, search_tail_size, max_leads_per_icp | - | apollo, arcads, arxiv, attio, coresignal, creatify, exa, expandi, inboxapp, instantly, leadiq, lemlist, lusha, outreach, paperclip, peopledatalabs, phantombuster, proxycurl, resend, salesforge, serper, smartlead, snovio, zerobounce, zoominfo |
| LinkedIn Job Applier | `linkedin` | `harnessiq.agents.linkedin:LinkedInJobApplierAgent` | `memory/linkedin` | max_tokens, reset_threshold, action_log_window, linkedin_start_url, notify_on_pause, pause_webhook | - | playwright |
| Google Maps Prospecting | `prospecting` | `harnessiq.agents.prospecting:GoogleMapsProspectingAgent` | `memory/prospecting` | max_tokens, reset_threshold | qualification_threshold, summarize_at_x, max_searches_per_run, max_listings_per_search, website_inspect_enabled, sink_record_type, eval_system_prompt | playwright |

## Provider Surface

Harnessiq currently ships 4 model-provider adapters, 25 service provider packages under `harnessiq/providers/`, and 1 tool-only external service surface outside the provider package tree.

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
| coresignal | 9 | `harnessiq/providers/coresignal` | `harnessiq/tools/coresignal/operations.py` |
| creatify | 58 | `harnessiq/providers/creatify` | `harnessiq/tools/creatify/operations.py` |
| exa | 15 | `harnessiq/providers/exa` | `harnessiq/tools/exa/operations.py` |
| expandi | 22 | `harnessiq/providers/expandi` | `harnessiq/tools/expandi/operations.py` |
| google_drive | 3 | `harnessiq/providers/google_drive` | `harnessiq/tools/google_drive/operations.py` |
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
print(result.output)  # {"text": "hello"}
```

Build a minimal custom agent:

```python
from harnessiq.agents import BaseAgent, AgentParameterSection
from harnessiq.agents import AgentModelRequest, AgentModelResponse
from harnessiq.tools.registry import create_builtin_registry


class MyModel:
    def generate_turn(self, request: AgentModelRequest) -> AgentModelResponse:
        return AgentModelResponse(assistant_message="Done.", should_continue=False)


class MyAgent(BaseAgent):
    def build_system_prompt(self) -> str:
        return "You are a helpful agent."

    def load_parameter_sections(self) -> list[AgentParameterSection]:
        return []


agent = MyAgent(
    name="my-agent",
    model=MyModel(),
    tool_executor=create_builtin_registry(),
)
result = agent.run(max_cycles=5)
print(result.status)  # "completed"
```

---

## Agent Runtime

### BaseAgent

`harnessiq.agents.BaseAgent` is the abstract base for all agents. It provides the full agent loop, context-window management, automatic context reset, and compaction integration.

```python
from harnessiq.agents import BaseAgent, AgentRuntimeConfig, AgentParameterSection

class MyAgent(BaseAgent):
    def build_system_prompt(self) -> str: ...
    def load_parameter_sections(self) -> list[AgentParameterSection]: ...
    def prepare(self) -> None: ...  # optional one-time setup
```

| Concept | Description |
|---------|-------------|
| `run(max_cycles=N)` | Run the loop until completion, pause signal, or max cycles |
| `AgentRuntimeConfig(max_tokens, reset_threshold)` | Controls context window budget and auto-reset trigger |
| `AgentPauseSignal` | Returned by a tool handler to halt the loop and surface a reason to the caller |
| `AgentRunResult` | Contains `status`, `cycles_completed`, `resets`, `pause_reason` |
| Parameter sections | Durable state injected at the front of every context window before the transcript |

**Context window ordering:** parameter sections (durable state) → transcript (assistant messages, tool calls, tool results).

**Instance identity and default memory layout:** every constructed agent resolves a stable `instance_id`, `instance_name`, and `instance_record`. The shared registry is persisted at `memory/agent_instances.json`, and default SDK-managed memory paths resolve under `memory/agents/<agent_name>/<instance_id>/`.

**Compaction tools** available in every built-in registry: `context.remove_tool_results`, `context.remove_tools`, `context.heavy_compaction`, `context.log_compaction`.

### BaseEmailAgent

`harnessiq.agents.BaseEmailAgent` extends `BaseAgent` with wired Resend email capabilities. The full Resend operation catalog is registered automatically.

```python
from harnessiq.agents import BaseEmailAgent, EmailAgentConfig
from harnessiq.tools.resend import ResendCredentials

class MyEmailAgent(BaseEmailAgent):
    def email_objective(self) -> str:
        return "Send weekly digest emails to subscribers."

    def load_email_parameter_sections(self):
        return []

config = EmailAgentConfig(
    resend_credentials=ResendCredentials(api_key="re_..."),
    allowed_resend_operations=("send_email",),
)
agent = MyEmailAgent(name="mailer", model=model, config=config)
```

### Provider Base Harnesses

`harnessiq.agents.BaseProviderToolAgent` is the reusable scaffold for provider-backed harnesses. It standardizes system-prompt structure, provider credential parameter sections, default tool registration, and allowed-operation filtering so provider-specific bases can stay thin.

The initial provider-backed SDK bases are exported directly from `harnessiq.agents`:

- `BaseApolloAgent` with `ApolloAgentConfig`
- `BaseExaAgent` with `ExaAgentConfig`
- `BaseInstantlyAgent` with `InstantlyAgentConfig`
- `BaseOutreachAgent` with `OutreachAgentConfig`

Each provider base wires its tool factory automatically, renders redacted provider credentials in the parameter sections, and lets downstream harnesses narrow the exposed provider operations through the corresponding `allowed_<provider>_operations` config field.

```python
from harnessiq.agents import BaseApolloAgent, ApolloAgentConfig
from harnessiq.providers.apollo import ApolloCredentials

class ApolloProspector(BaseApolloAgent):
    def apollo_objective(self) -> str:
        return "Find qualified VP Sales prospects."

    def load_apollo_parameter_sections(self):
        return []

agent = ApolloProspector(
    name="apollo-prospector",
    model=model,
    config=ApolloAgentConfig(
        apollo_credentials=ApolloCredentials(api_key="apollo_..."),
        allowed_apollo_operations=("search_people", "get_person"),
    ),
)
```

---

## Concrete Agents

### LinkedInJobApplierAgent

A loop agent for autonomous LinkedIn job applications. Maintains durable file-backed memory: job preferences, user profile, applied-jobs log, action log, managed files, and screenshots. Browser automation tools are injected at runtime via `browser_tools`.

```python
from harnessiq.agents import LinkedInJobApplierAgent

agent = LinkedInJobApplierAgent(
    model=model,
    max_tokens=80_000,
    reset_threshold=0.9,
    notify_on_pause=True,
    pause_webhook="https://hooks.example.com/notify",
)
result = agent.run(max_cycles=30)
print(agent.instance_id)
print(agent.memory_path)
```

Pass `memory_path` explicitly when you want to bind the agent to a pre-existing CLI-managed folder such as `./memory/linkedin/candidate-a`.

**Instantiate from persisted CLI state:**

```python
agent = LinkedInJobApplierAgent.from_memory(
    model=model,
    memory_path="./memory/linkedin/candidate-a",
    browser_tools=my_playwright_tools,
)
```

**Memory files** (all under `memory_path/`):

| File | Purpose |
|------|---------|
| `job_preferences.txt` | Target role criteria |
| `user_profile.md` | Candidate profile used to populate application fields |
| `agent_identity.txt` | Customizable agent persona |
| `applied_jobs.jsonl` | Append-only application log |
| `action_log.jsonl` | Semantic action log reinjected on context reset |
| `runtime_parameters.json` | Persisted runtime overrides |
| `custom_parameters.json` | User-defined key/value pairs |
| `managed_files/` | Imported files (resume, cover letter, etc.) |
| `screenshots/` | Browser state snapshots |

**Internal tools:** `append_action`, `append_company`, `update_job_status`, `read_memory_file`, `save_screenshot_to_memory`, `pause_and_notify`, `mark_job_skipped`.

---

### KnowtAgent

A content creation agent for Knowt TikTok workflows. Enforces a deterministic pipeline (brainstorm → create_script → create_avatar_description → create_video) backed by a file-based memory store. The system prompt is loaded at runtime from `harnessiq/agents/knowt/prompts/master_prompt.md`.

```python
from harnessiq.agents import KnowtAgent
from harnessiq.providers.creatify.client import CreatifyCredentials

agent = KnowtAgent(
    model=model,
    memory_path="./memory/knowt/my-channel",
    creatify_credentials=CreatifyCredentials(api_id="...", api_key="..."),
)
result = agent.run(max_cycles=20)
```

**Tools wired automatically:** three core reasoning tools (`reason.brainstorm`, `reason.chain_of_thought`, `reason.critique`) plus the Knowt tool suite (`knowt.create_script`, `knowt.create_avatar_description`, `knowt.create_video`, `knowt.create_file`, `knowt.edit_file`).

---

### ExaOutreachAgent

A loop agent for automated prospect discovery and cold email outreach. Uses Exa neural search to find and enrich leads, selects email templates from the injected `email_data`, deduplicates against prior runs, sends via Resend, and deterministically logs every lead found and email sent into a per-run JSON file.

```python
from harnessiq.agents.exa_outreach import ExaOutreachAgent
from harnessiq.shared.exa_outreach import EmailTemplate
from harnessiq.providers.exa.client import ExaCredentials
from harnessiq.tools.resend import ResendCredentials
from pathlib import Path

email_data = [
    EmailTemplate(
        id="cold-intro",
        title="Cold Intro",
        subject="Quick intro",
        description="Short cold intro for VPs of Engineering",
        actual_email="Hi {{name}},\n\nI came across your profile and wanted to reach out...",
        icp="Series B SaaS, 50-200 employees",
        pain_points=("slow hiring", "tooling fragmentation"),
    )
]

agent = ExaOutreachAgent(
    model=model,
    exa_credentials=ExaCredentials(api_key="..."),
    resend_credentials=ResendCredentials(api_key="re_..."),
    email_data=email_data,
    search_query="VP of Engineering at Series B SaaS startups in New York",
    memory_path=Path("./memory/outreach/campaign-a"),
)
result = agent.run(max_cycles=50)
```

**EmailTemplate fields:**

| Field | Required | Description |
|-------|----------|-------------|
| `id` | yes | Unique template identifier |
| `title` | yes | Human-readable template name |
| `subject` | yes | Email subject line |
| `description` | yes | When to use this template |
| `actual_email` | yes | Template body (use `{{name}}` etc. for personalization) |
| `links` | no | Relevant URLs to include |
| `pain_points` | no | Target pain points for this template |
| `icp` | no | Ideal customer profile description |
| `extra` | no | Any additional metadata as a dict |

**Per-run output** (`memory_path/runs/run_N.json`):

```json
{
  "run_id": "run_1",
  "started_at": "2025-03-16T12:00:00Z",
  "completed_at": "2025-03-16T12:08:30Z",
  "query": "VP of Engineering at Series B SaaS startups in New York",
  "leads_found": [
    {"url": "...", "name": "Jane Doe", "email_address": "jane@example.com", "found_at": "..."}
  ],
  "emails_sent": [
    {"to_email": "jane@example.com", "to_name": "Jane Doe", "subject": "Quick intro",
     "template_id": "cold-intro", "sent_at": "..."}
  ]
}
```

**Internal tools:** `exa_outreach.list_templates`, `exa_outreach.get_template`, `exa_outreach.check_contacted`, `exa_outreach.log_lead`, `exa_outreach.log_email_sent`.

**Pluggable storage via `StorageBackend` protocol.** The default is `FileSystemStorageBackend`. Implement the protocol to route results to any backend:

```python
from harnessiq.shared.exa_outreach import StorageBackend, LeadRecord, EmailSentRecord

class MyDatabaseBackend:
    def start_run(self, run_id: str, query: str) -> None: ...
    def finish_run(self, run_id: str, completed_at: str) -> None: ...
    def log_lead(self, run_id: str, lead: LeadRecord) -> None: ...
    def log_email_sent(self, run_id: str, record: EmailSentRecord) -> None: ...
    def is_contacted(self, url: str) -> bool: ...
    def current_run_id(self) -> str | None: ...

agent = ExaOutreachAgent(..., storage_backend=MyDatabaseBackend())
```

### LeadsAgent

A rotating multi-ICP prospect discovery harness. One agent instance works through a list of ICPs, injects provider tools by family (`apollo`, `leadiq`, `lemlist`, `zoominfo`, and others already registered in the SDK), persists every search deterministically, compacts older search history into summaries, and deduplicates saved leads through a pluggable `LeadsStorageBackend`.

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
```

**Durable memory layout** (`memory_path/`):

| File or folder | Purpose |
|----------------|---------|
| `run_config.json` | Company background, ICP list, provider platform list, and durable search-compaction settings |
| `run_state.json` | Active ICP index and overall run lifecycle state |
| `icps/*.json` | Per-ICP state: raw searches, search summaries, saved lead keys, completion markers |
| `lead_storage/saved_leads.json` | Cross-run deduplicated saved leads |
| `lead_storage/runs/` | Per-run event log emitted by the default filesystem backend |

**Internal tools:** `leads.log_search`, `leads.compact_search_history`, `leads.check_seen_lead`, `leads.save_leads`.

**Pluggable storage via `LeadsStorageBackend` protocol.** The default backend is `FileSystemLeadsStorageBackend`, but the harness can save into any custom store:

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

---

## Tool Layer

Tools are `RegisteredTool(definition, handler)` objects stored in a `ToolRegistry`. Keys follow the `namespace.tool_name` convention.

```python
from harnessiq.tools.registry import ToolRegistry, create_builtin_registry
from harnessiq.shared.tools import RegisteredTool, ToolDefinition

registry = create_builtin_registry()

custom = ToolRegistry([
    RegisteredTool(
        definition=ToolDefinition(
            key="my.tool",
            name="my_tool",
            description="Does something useful.",
            input_schema={
                "type": "object",
                "properties": {"x": {"type": "string"}},
                "required": ["x"],
                "additionalProperties": False,
            },
        ),
        handler=lambda args: {"result": args["x"].upper()},
    )
])
result = custom.execute("my.tool", {"x": "hello"})
```

### Built-in Tools

| Key | Name | Description |
|-----|------|-------------|
| `core.echo_text` | `echo_text` | Return provided text unchanged |
| `core.add_numbers` | `add_numbers` | Add two numeric values |

### Context Compaction Tools

Manage long transcripts to stay within context limits.

| Key | Description |
|-----|-------------|
| `context.remove_tool_results` | Strip tool result entries from the transcript |
| `context.remove_tools` | Strip tool call entries from the transcript |
| `context.heavy_compaction` | Collapse the full transcript to a compact summary |
| `context.log_compaction` | Replace transcript with a structured log-style summary |

```python
from harnessiq.tools import create_context_compaction_tools
tools = create_context_compaction_tools()
```

### Filesystem Tools

Non-destructive filesystem access for agents operating on local files.

| Key | Description |
|-----|-------------|
| `filesystem.get_current_directory` | Return the process working directory |
| `filesystem.path_exists` | Check whether a path exists |
| `filesystem.list_directory` | List directory contents |
| `filesystem.read_text_file` | Read a UTF-8 text file |
| `filesystem.write_text_file` | Write (overwrite) a text file |
| `filesystem.append_text_file` | Append text to an existing file |
| `filesystem.make_directory` | Create a directory (equivalent to mkdir -p) |
| `filesystem.copy_path` | Copy a file or directory |

```python
from harnessiq.tools import create_filesystem_tools
tools = create_filesystem_tools()
```

### General-Purpose Tools

Text manipulation, record processing, and control-flow tools.

**Text tools:**

| Key | Description |
|-----|-------------|
| `text.normalize_whitespace` | Collapse and trim whitespace in a string |
| `text.regex_extract` | Extract capture groups using a regex pattern |
| `text.truncate_text` | Truncate to N characters from head, tail, or middle |

**Record tools** (operate on lists of dicts):

| Key | Description |
|-----|-------------|
| `records.select_fields` | Keep only specified keys in each record |
| `records.filter_records` | Filter by field value with operators: `eq`, `ne`, `lt`, `gt`, `contains`, `not_contains` |
| `records.sort_records` | Sort records by one or more fields |
| `records.limit_records` | Keep the first N records |
| `records.unique_records` | Deduplicate records by a specified field |
| `records.count_by_field` | Count records grouped by a field value |

**Control tools:**

| Key | Description |
|-----|-------------|
| `control.pause_for_human` | Emit an `AgentPauseSignal` to halt the agent loop |

```python
from harnessiq.tools import create_general_purpose_tools
tools = create_general_purpose_tools()
```

### Prompting Tools

| Key | Description |
|-----|-------------|
| `prompt.create_system_prompt` | Generate a structured system prompt from labelled sections |

```python
from harnessiq.tools import create_prompt_tools
tools = create_prompt_tools()
```

### Reasoning Tools

Three high-level injectable reasoning tools plus 50 cognitive scaffolding lens tools.

**Core reasoning tools:**

| Key | Description |
|-----|-------------|
| `reason.brainstorm` | Generate N ideas (count presets: `"small"` = 3, `"medium"` = 7, `"large"` = 12) |
| `reason.chain_of_thought` | Work through a problem step by step |
| `reason.critique` | Produce a structured critique of a claim or plan |

**50 reasoning lens tools** across 8 cognitive categories:

| Category | Lenses (sample) |
|----------|-----------------|
| Core logical | `step_by_step`, `tree_of_thoughts`, `first_principles`, `backward_chaining`, `forward_chaining`, `graph_of_thoughts` |
| Analytical | `root_cause_analysis`, `pareto_analysis`, `cost_benefit_analysis`, `constraint_mapping`, `bottleneck_identification` |
| Perspective | `red_teaming`, `devils_advocate`, `steelmanning`, `six_thinking_hats`, `stakeholder_analysis`, `persona_adoption` |
| Creative | `lateral_thinking`, `scamper`, `worst_idea_generation`, `provocation_operation`, `role_storming`, `morphological_analysis` |
| Systems | `feedback_loop_identification`, `second_order_effects`, `network_mapping`, `butterfly_effect_trace`, `cynefin_categorization` |
| Temporal | `backcasting`, `trend_extrapolation`, `scenario_planning`, `pre_mortem`, `post_mortem` |
| Evaluative | `self_critique`, `bias_detection`, `confidence_calibration`, `fact_checking`, `tradeoff_evaluation`, `blindspot_check` |
| Scientific | `hypothesis_generation`, `falsification_test`, `abductive_reasoning`, `variable_isolation`, `divide_and_conquer` |

All lens keys are prefixed `reasoning.` (e.g. `reasoning.red_teaming`). All constants are exported from `harnessiq.shared.tools`.

```python
from harnessiq.tools import create_reasoning_tools
tools = create_reasoning_tools()  # returns all 53 tools (3 core + 50 lenses)
```

### Resend Email Tools

MCP-style unified tool for the full Resend email API. A single `resend.request` tool with an `operation` argument selects the endpoint.

```python
from harnessiq.tools import create_resend_tools, ResendCredentials

tools = create_resend_tools(
    credentials=ResendCredentials(api_key="re_..."),
    allowed_operations=("send_email", "batch_send_email", "get_email"),
)
```

`ResendCredentials` fields: `api_key`, `base_url`, `user_agent`, `timeout_seconds`.

---

## External Service Provider Tools

All external providers follow the MCP-style pattern: a single `create_X_tools()` factory that returns one `RegisteredTool`. The `operation` argument selects the API endpoint.

```python
from harnessiq.providers.exa.client import ExaCredentials
from harnessiq.tools.exa.operations import create_exa_tools

tools = create_exa_tools(
    credentials=ExaCredentials(api_key="..."),
    allowed_operations=("search", "get_contents"),
)
```

### AI / LLM Providers

| Provider | Package | Key helpers |
|----------|---------|-------------|
| Anthropic | `harnessiq.providers.anthropic` | `build_anthropic_request`, `translate_anthropic_tools`, `AnthropicClient` |
| OpenAI | `harnessiq.providers.openai` | `build_openai_request`, `translate_openai_tools`, `OpenAIClient` |
| Grok (xAI) | `harnessiq.providers.grok` | `build_grok_request`, `GrokClient`; agent integration: `harnessiq.integrations.grok_model.GrokAgentModel` |
| Gemini | `harnessiq.providers.gemini` | `build_gemini_content`, `translate_gemini_tools`, `GeminiClient` |

### Search and Intelligence Providers

| Provider | Tool key constant | Factory | Operations | Auth mechanism |
|----------|-------------------|---------|-----------|----------------|
| **Apollo.io** | `APOLLO_REQUEST` | `create_apollo_tools()` | 25 | API key (`X-Api-Key` header) |
| **Exa** | `EXA_REQUEST` | `create_exa_tools()` | 15 | API key (`x-api-key` header) |
| **Serper** | `SERPER_REQUEST` | `create_serper_tools()` | 10 | API key (`X-API-KEY` header) |
| **Snov.io** | `SNOVIO_REQUEST` | `create_snovio_tools()` | 23 | OAuth2 — client ID + secret, token exchange is transparent |
| **LeadIQ** | `LEADIQ_REQUEST` | `create_leadiq_tools()` | 12 | API key (GraphQL `Authorization: Bearer`) |
| **ZoomInfo** | `ZOOMINFO_REQUEST` | `create_zoominfo_tools()` | 12 | JWT — username + password, token exchange is transparent |
| **People Data Labs** | `PEOPLEDATALABS_REQUEST` | `create_peopledatalabs_tools()` | 11 | API key |
| **Coresignal** | `CORESIGNAL_REQUEST` | `create_coresignal_tools()` | 9 | API key |
| **Proxycurl** *(deprecated)* | `PROXYCURL_REQUEST` | `create_proxycurl_tools()` | 11 | Bearer token — provider shut down January 2025, preserved for reference |

**Exa operation categories:** Search, Contents, Find Similar, Answer, Research (search + contents), Webset management (create, update, delete, list, items, searches).

Import constants: `from harnessiq.shared.tools import APOLLO_REQUEST, EXA_REQUEST, SNOVIO_REQUEST, LEADIQ_REQUEST, ...`

### Sales Engagement Providers

| Provider | Tool key constant | Factory | Operations | Auth mechanism |
|----------|-------------------|---------|-----------|----------------|
| **Instantly** | `INSTANTLY_REQUEST` | `create_instantly_tools()` | 75 | API key |
| **Attio** | `ATTIO_REQUEST` | `create_attio_tools()` | 7 | Bearer token |
| **InboxApp** | `INBOXAPP_REQUEST` | `create_inboxapp_tools()` | 9 | Bearer token |
| **Outreach** | `OUTREACH_REQUEST` | `create_outreach_tools()` | 65 | OAuth Bearer token |
| **Lemlist** | `LEMLIST_REQUEST` | `create_lemlist_tools()` | 34 | Basic Auth (API key as username, empty password) |
| **Salesforge** | `SALESFORGE_REQUEST` | `create_salesforge_tools()` | 22 | API key |
| **PhantomBuster** | `PHANTOMBUSTER_REQUEST` | `create_phantombuster_tools()` | 15 | API key (`X-Phantombuster-Key` header) |

### Video and Creative Providers

| Provider | Tool key constant | Factory | Operations | Auth mechanism |
|----------|-------------------|---------|-----------|----------------|
| **Creatify** | `CREATIFY_REQUEST` | `create_creatify_tools()` | 58 | API ID + API key (`X-API-ID`, `X-API-KEY` headers) |
| **Arcads** | `ARCADS_REQUEST` | `create_arcads_tools()` | 10 | Basic Auth (API key) |

**Creatify operation categories:** lipsync, URL-to-video, batch video, avatar, voice, template, preview, and export operations.

---

## Master Prompts

`MasterPromptRegistry` loads JSON-packaged system prompts bundled with the SDK.

```python
from harnessiq.master_prompts.registry import MasterPromptRegistry

registry = MasterPromptRegistry()

# List all available prompts
for prompt in registry.list():
    print(prompt.key, "—", prompt.title)

# Get a specific prompt
prompt = registry.get("create_master_prompts")
system_text = prompt.prompt

# Convenience — just the text
text = registry.get_prompt_text("create_master_prompts")
```

**Available prompts:**

| Key | Description |
|-----|-------------|
| `create_master_prompts` | System prompt for generating new master prompt JSON files |

Add new prompts by dropping a `.json` file with `title`, `description`, and `prompt` fields under `harnessiq/master_prompts/prompts/`. The registry discovers them automatically on next instantiation.

---

## CLI

The generated command catalog lives at `artifacts/commands.md`. Use it as the high-signal reference for the live command tree.

| Command | Direct Subcommands | Description |
| --- | --- | --- |
| harnessiq connect | confluence, discord, linear, notion, obsidian, slack, supabase | Configure a global output sink connection |
| harnessiq connections | list, remove, test | Inspect or manage configured sink connections |
| harnessiq credentials | bind, show, test | Manage persisted harness credential bindings |
| harnessiq export | - | Export ledger entries in a structured format |
| harnessiq inspect | exa_outreach (outreach), instagram, knowt, leads, linkedin, prospecting | Inspect one harness manifest and generated CLI surface |
| harnessiq instagram | configure, get-emails, prepare, run, show | Manage and run the Instagram keyword discovery agent |
| harnessiq leads | configure, prepare, run, show | Manage and run the leads discovery agent |
| harnessiq linkedin | configure, init-browser, prepare, run, show | Manage and run the LinkedIn agent |
| harnessiq logs | - | Inspect the local audit ledger |
| harnessiq outreach | configure, prepare, run, show | Manage and run the ExaOutreach agent |
| harnessiq prepare | exa_outreach (outreach), instagram, knowt, leads, linkedin, prospecting | Prepare and persist generic config for a harness |
| harnessiq prospecting | configure, init-browser, prepare, run, show | Manage and run the Google Maps prospecting agent |
| harnessiq report | - | Build a cross-agent report from the local ledger |
| harnessiq run | exa_outreach (outreach), instagram, knowt, leads, linkedin, prospecting | Run a harness through the platform-first CLI |
| harnessiq show | exa_outreach (outreach), instagram, knowt, leads, linkedin, prospecting | Show persisted platform config and harness state |

## Repo Docs

- `docs/agent-runtime.md`: Runtime loop, manifests, and durable parameter sections.
- `docs/tools.md`: Tool registry composition and provider-backed tool usage.
- `docs/output-sinks.md`: Ledger/output-sink injection and sink connection commands.
- `docs/linkedin-agent.md`: LinkedIn harness usage and browser session workflow.
- `docs/leads-agent.md`: Leads harness memory model and CLI workflow.
- `artifacts/file_index.md`: Generated architecture map for the live repository.
- `artifacts/commands.md`: Generated CLI command catalog.
- `artifacts/live_inventory.json`: Machine-readable source of truth for generated repo docs.
