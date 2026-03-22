# Internalization — ExaOutreach Agent + README Update

---

### 1a: Structural Survey

**Technology stack:**
- Python 3.11+, setuptools build system, no external runtime dependencies beyond `langsmith`
- All HTTP calls go through `harnessiq/providers/http.py` (`request_json`)
- Tests use `pytest` with no database, no real HTTP calls (mock `request_executor` everywhere)

**Top-level architecture:**

```
harnessiq/
  agents/         — Concrete agent harnesses + base classes
  cli/            — argparse CLI entrypoints (harnessiq linkedin ...)
  config/         — Credential loader + .env parsing
  integrations/   — Playwright browser session + GrokAgentModel
  master_prompts/ — JSON-backed MasterPrompt registry
  providers/      — AI LLM providers + 14 external service providers
  shared/         — Cross-cutting data models, constants, tool keys
  tools/          — Tool definitions, factories, and execution logic
```

**Agent architecture (invariants to match):**
- All agents extend `BaseAgent` from `harnessiq/agents/base/agent.py`
- Constructor: `super().__init__(name=, model=, tool_executor=ToolRegistry(...), runtime_config=AgentRuntimeConfig(...))`
- Abstract methods: `build_system_prompt() -> str` and `load_parameter_sections() -> Sequence[AgentParameterSection]`
- `prepare()` hook for one-time setup (memory dir creation)
- Memory stores are dataclasses with a `prepare()` method that creates directories and default files
- System prompts use bracketed section pattern: `[IDENTITY]`, `[GOAL]`, `[TOOLS]`, `[BEHAVIORAL RULES]`, `[INPUT DESCRIPTION]`
- Tool keys follow `namespace.tool_name` convention

**Tool architecture (invariants to match):**
- `RegisteredTool(definition=ToolDefinition(...), handler=callable)` stored in `ToolRegistry`
- Provider tools are `create_X_tools(credentials=..., client=..., allowed_operations=...)` returning `tuple[RegisteredTool, ...]`
- Internal agent tools inline their definition using a `_tool_definition()` helper
- Constants for tool keys live in `harnessiq/shared/tools.py` and are re-exported from `harnessiq/tools/__init__.py`

**CLI architecture (invariants to match):**
- Each command group has `register_X_commands(subparsers)` registered in `cli/main.py`
- Commands: `prepare`, `configure`, `show`, `run`
- `--agent` + `--memory-root` resolve the agent's memory path
- `--model-factory` takes `module:callable` import path
- `--runtime-param KEY=VALUE` for typed overrides

**Conventions observed:**
- `from __future__ import annotations` in all files
- `__all__` list at end of every module
- frozen dataclasses with `slots=True` for value objects
- `memory_path = Path(__file__).parent / "memory"` as default memory location
- JSONL for append-only logs, JSON for single documents
- Credential objects have `as_redacted_dict()` and `masked_api_key()` methods

**Providers present (relevant to this task):**
- `harnessiq/providers/exa/` — ExaCredentials, ExaClient, operations catalog (search, get_contents, find_similar, get_answer, search_and_contents, webset operations)
- `harnessiq/tools/exa/operations.py` — `create_exa_tools()` factory
- `harnessiq/tools/resend.py` — `create_resend_tools()`, `ResendCredentials`, `ResendClient`
- `harnessiq/agents/email/agent.py` — `BaseEmailAgent` wraps Resend tools

**Master prompts:**
- Single JSON file currently: `create_master_prompts.json`
- Loaded via `MasterPromptRegistry.get(key).prompt`
- Knowt agent uses a `master_prompt.md` file instead (loaded at runtime from disk)

---

### 1b: Task Cross-Reference

**Task 1 — Update README.md:**
- File: `README.md` (root)
- Currently: minimal (install, quick start, one CLI example, pointer to docs)
- Must cover: all agents, all provider tools, all built-in tool families, master prompts, CLI
- No code changes — documentation only
- Reference files: `harnessiq/shared/tools.py` (all tool key constants), `harnessiq/providers/*/operations.py` (operation catalogs), `harnessiq/tools/*/operations.py` (tool factories), `harnessiq/agents/` (all agents), `harnessiq/cli/` (CLI commands)

**Task 2 — ExaOutreach agent:**

New files required:
- `harnessiq/shared/exa_outreach.py` — `ExaOutreachMemoryStore`, `ExaOutreachAgentConfig`, `OutreachLogEntry`, filename constants
- `harnessiq/agents/exa_outreach/__init__.py`
- `harnessiq/agents/exa_outreach/agent.py` — `ExaOutreachAgent`
- `harnessiq/agents/exa_outreach/prompts/master_prompt.md` — system prompt loaded from disk (Knowt pattern)
- `harnessiq/cli/exa_outreach/__init__.py`
- `harnessiq/cli/exa_outreach/commands.py` — `register_exa_outreach_commands()`
- `tests/test_exa_outreach_agent.py`

Files to modify:
- `harnessiq/agents/__init__.py` — export `ExaOutreachAgent`, `ExaOutreachMemoryStore`
- `harnessiq/cli/main.py` — register exa_outreach commands
- `artifacts/file_index.md` — update with new modules
- `harnessiq/shared/tools.py` — add `EXA_OUTREACH_*` tool key constants

**Agent tool set:**
1. Exa tools (via `create_exa_tools()`) — existing, injected with `allowed_operations=("search", "get_contents", "search_and_contents")`
2. Resend tools (via `create_resend_tools()`) — existing, same as BaseEmailAgent
3. Internal outreach memory tools:
   - `exa_outreach.check_already_contacted` — check JSON log by email
   - `exa_outreach.log_outreach` — append to outreach_log.json
   - `exa_outreach.read_outreach_log` — read outreach_log.json summary

**Memory files:**
- `outreach_log.json` — JSON array of OutreachLogEntry objects (email, name, sent_at, subject, exa_url, run_id, notes)
- `query_config.json` — persisted search query and runtime parameters
- `agent_identity.txt` — customizable persona
- `additional_prompt.txt` — extra instructions

---

### 1c: Assumption & Risk Inventory

**A1 — Email address source:**
The design doc mentions Hunter.io for email lookup, but there is no Hunter.io provider in this repo. The user said "tools that interact with exa, then tools for sending emails (can either input email exactly or description of what email should be)". Assumption: Exa's `search` operation returns LinkedIn/web profile URLs with enough context for the agent to draft outreach emails. The "email address" must either be found by Exa (some profiles include contact info) or provided directly via agent config/tool call. We are NOT adding a Hunter.io provider — this is out of scope per the user's description which focuses on Exa + email sending.

**A2 — "Email description" interpretation:**
The user said the tool can take "a description of what email should be." Assumption: this means the agent itself (as an LLM) drafts the email body based on enriched profile context — NOT a separate tool that calls an LLM API internally. The resend tool already accepts subject + body; the agent composes them.

**A3 — Memory format: JSON vs JSONL:**
The user said "json file/files". Assumption: use a JSON array file (`outreach_log.json`) rather than JSONL. This is different from LinkedIn which uses JSONL. Trade-off: JSON array requires read-modify-write but is more readable as a log. Decision: use JSON array for the outreach log to honor user's explicit "json file/files" request.

**A4 — CLI sub-command name:**
Design doc suggests `harnessiq outreach`. Assumption: use `harnessiq outreach` as the CLI sub-command (parallel to `harnessiq linkedin`).

**A5 — Looping behavior:**
The agent inherits the base loop from `BaseAgent.run(max_cycles=N)`. The "loop" is the standard agent loop — the system prompt instructs the agent to continuously search → enrich → check memory → compose → send → log. No custom loop logic needed.

**A6 — No external email finder API:**
We are not adding Hunter.io. The agent uses Exa to find profiles that may contain email addresses, or the user pre-configures target email addresses in query_config. Clarification needed: should the agent be able to accept a list of explicit (name, email) pairs as seed data, or must it discover emails via Exa?

**Phase 1 complete.**
