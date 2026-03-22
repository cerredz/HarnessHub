# Harnessiq

Harnessiq is a Python SDK for building production-grade tool-using agents. It ships a complete agent runtime, a large library of injectable tools, MCP-style factories for 14+ external service APIs, four concrete agent harnesses, and a scriptable CLI — all composable without framework lock-in.

---

## Table of Contents

- [Install](#install)
- [Quick Start](#quick-start)
- [Agent Runtime](#agent-runtime)
  - [BaseAgent](#baseagent)
  - [BaseEmailAgent](#baseemailagent)
- [Concrete Agents](#concrete-agents)
  - [LinkedInJobApplierAgent](#linkedinjobapplieragent)
  - [KnowtAgent](#knowtagent)
  - [ExaOutreachAgent](#exaoutreachagent)
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

---

## Quick Start

```python
from harnessiq.tools import ECHO_TEXT, create_builtin_registry

registry = create_builtin_registry()
result = registry.execute(ECHO_TEXT, {"text": "hello"})
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
| **Exa** | `EXA_REQUEST` | `create_exa_tools()` | 15 | API key (`x-api-key` header) |
| **Snov.io** | `SNOVIO_REQUEST` | `create_snovio_tools()` | 23 | OAuth2 — client ID + secret, token exchange is transparent |
| **LeadIQ** | `LEADIQ_REQUEST` | `create_leadiq_tools()` | 12 | API key (GraphQL `Authorization: Bearer`) |
| **ZoomInfo** | `ZOOMINFO_REQUEST` | `create_zoominfo_tools()` | 12 | JWT — username + password, token exchange is transparent |
| **People Data Labs** | `PEOPLEDATALABS_REQUEST` | `create_peopledatalabs_tools()` | 11 | API key |
| **Coresignal** | `CORESIGNAL_REQUEST` | `create_coresignal_tools()` | 9 | API key |
| **Proxycurl** *(deprecated)* | `PROXYCURL_REQUEST` | `create_proxycurl_tools()` | 11 | Bearer token — provider shut down January 2025, preserved for reference |

**Exa operation categories:** Search, Contents, Find Similar, Answer, Research (search + contents), Webset management (create, update, delete, list, items, searches).

Import constants: `from harnessiq.shared.tools import EXA_REQUEST, SNOVIO_REQUEST, LEADIQ_REQUEST, ...`

### Sales Engagement Providers

| Provider | Tool key constant | Factory | Operations | Auth mechanism |
|----------|-------------------|---------|-----------|----------------|
| **Instantly** | `INSTANTLY_REQUEST` | `create_instantly_tools()` | 75 | API key |
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

The `harnessiq` CLI is installed automatically with the package. All commands emit structured JSON to stdout.

```bash
harnessiq --help
harnessiq linkedin --help
harnessiq outreach --help
```

### LinkedIn Commands

#### `harnessiq linkedin prepare`

Create or refresh a LinkedIn agent memory folder.

```bash
harnessiq linkedin prepare \
  --agent candidate-a \
  --memory-root ./memory/linkedin
```

#### `harnessiq linkedin configure`

Write job preferences, user profile, agent identity, runtime parameters, custom parameters, and managed files.

```bash
harnessiq linkedin configure \
  --agent candidate-a \
  --memory-root ./memory/linkedin \
  --job-preferences-text "Staff platform engineering roles in New York" \
  --user-profile-file ./profile.md \
  --agent-identity-text "A meticulous job applicant who only applies to matching roles." \
  --additional-prompt-text "Prefer companies with fewer than 500 employees." \
  --runtime-param max_tokens=80000 \
  --runtime-param notify_on_pause=true \
  --runtime-param pause_webhook=https://hooks.example.com/notify \
  --custom-param target_team=platform \
  --import-file ./resume.pdf \
  --inline-file cover-letter.txt="Short cover letter text here"
```

**Supported `--runtime-param` keys:** `max_tokens`, `reset_threshold`, `action_log_window`, `linkedin_start_url`, `notify_on_pause`, `pause_webhook`.

#### `harnessiq linkedin show`

Render the current LinkedIn agent state as JSON.

```bash
harnessiq linkedin show --agent candidate-a
```

#### `harnessiq linkedin run`

Run the LinkedIn agent from persisted CLI state.

```bash
harnessiq linkedin run \
  --agent candidate-a \
  --model-factory harnessiq.integrations.grok_model:create_grok_model \
  --browser-tools-factory harnessiq.integrations.linkedin_playwright:create_browser_tools \
  --runtime-param max_tokens=60000 \
  --max-cycles 30
```

`--model-factory` and `--browser-tools-factory` accept `module:callable` import paths. The factory callable must return an `AgentModel` instance or an iterable of `RegisteredTool` objects respectively.

#### `harnessiq linkedin init-browser`

Open a persistent Playwright browser session, wait for LinkedIn login, and save the session for future `run` invocations.

```bash
harnessiq linkedin init-browser --agent candidate-a
```

Requires: `pip install playwright && python -m playwright install chromium`

---

### Outreach Commands

#### `harnessiq outreach prepare`

Create or refresh an outreach agent memory folder.

```bash
harnessiq outreach prepare \
  --agent campaign-a \
  --memory-root ./memory/outreach
```

#### `harnessiq outreach configure`

Write the search query, agent identity, runtime parameters, and additional prompt.

```bash
harnessiq outreach configure \
  --agent campaign-a \
  --memory-root ./memory/outreach \
  --query-text "VP of Engineering at Series B SaaS startups in New York" \
  --agent-identity-text "A concise, value-first outreach specialist." \
  --additional-prompt-text "Keep emails under 100 words. Always mention a specific detail from their profile." \
  --runtime-param max_tokens=80000 \
  --runtime-param reset_threshold=0.9
```

**Supported `--runtime-param` keys:** `max_tokens`, `reset_threshold`.

#### `harnessiq outreach show`

Render the current outreach agent state as JSON.

```bash
harnessiq outreach show --agent campaign-a
```

#### `harnessiq outreach run`

Run the outreach agent from persisted CLI state.

```bash
harnessiq outreach run \
  --agent campaign-a \
  --model-factory my_module:create_model \
  --exa-credentials-factory my_module:create_exa_credentials \
  --resend-credentials-factory my_module:create_resend_credentials \
  --email-data-factory my_module:load_email_templates \
  --max-cycles 50
```

Each `--X-factory` flag accepts a `module:callable` import path.

`--email-data-factory` must return a `list[dict]`, where each dict has at minimum: `id`, `title`, `subject`, `description`, `actual_email`. Each run writes a `run_N.json` file under `memory_path/runs/`. Leads and sent emails are logged deterministically inside tool handlers.

---

## Configuration and Credentials

`CredentialLoader` resolves named keys from a repo-local `.env` file.

```python
from harnessiq.config.loader import CredentialLoader

loader = CredentialLoader()            # defaults to .env in cwd
api_key = loader.load("EXA_API_KEY")

creds = loader.load_all(["EXA_API_KEY", "RESEND_API_KEY"])
```

`.env` format:

```
# Search and intelligence
EXA_API_KEY=your_exa_key
SNOVIO_CLIENT_ID=...
SNOVIO_CLIENT_SECRET=...
LEADIQ_API_KEY=...
ZOOMINFO_USERNAME=...
ZOOMINFO_PASSWORD=...
PEOPLEDATALABS_API_KEY=...
CORESIGNAL_API_KEY=...

# Sales engagement
INSTANTLY_API_KEY=...
OUTREACH_ACCESS_TOKEN=...
LEMLIST_API_KEY=...
SALESFORGE_API_KEY=...
PHANTOMBUSTER_API_KEY=...

# Video and creative
CREATIFY_API_ID=...
CREATIFY_API_KEY=...
ARCADS_API_KEY=...

# Email delivery
RESEND_API_KEY=re_...
```

- Lines beginning with `#` are comments.
- Values may be wrapped in single or double quotes (stripped automatically).
- `load()` raises `KeyError` for missing keys and `FileNotFoundError` if `.env` does not exist.

---

## Further Reading

- `docs/tools.md` — tool API reference and composition patterns
- `docs/agent-runtime.md` — context window mechanics, compaction strategies, and pause/reset flow
- `docs/linkedin-agent.md` — LinkedIn agent CLI workflow and Playwright browser integration guide
