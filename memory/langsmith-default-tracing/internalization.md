### 1a: Structural Survey

The repository is a Python SDK and CLI centered on `harnessiq/`. Agent runtime primitives live under `harnessiq/agents/`, shared immutable-ish data models and config live under `harnessiq/shared/`, provider and tracing helpers live under `harnessiq/providers/`, and command entrypoints live under `harnessiq/cli/`. Tests are primarily `unittest`-based under `tests/`.

Relevant architectural observations:

- `harnessiq/agents/base/agent.py` owns the generic run loop, transcript management, parameter refresh, compaction handling, and reset/prune logic. This is the narrowest shared place to guarantee default tracing for every agent.
- `harnessiq/shared/agents.py` defines `AgentRuntimeConfig`. Concrete agents reconstruct this config from scalar constructor arguments, so any new tracing fields added here must be preserved when agents rebuild runtime config.
- Concrete agents currently include `LinkedInJobApplierAgent`, `InstagramKeywordDiscoveryAgent`, `KnowtAgent`, `LeadsAgent`, `ExaOutreachAgent`, and `BaseEmailAgent`.
- `harnessiq/providers/langsmith.py` already exposes sync/async tracing wrappers for agent runs, model calls, and tool calls. Today those helpers assume tracing is available and do not intentionally fail open when credentials are absent or tracing transport fails.
- `harnessiq/integrations/grok_model.py` already emits model spans through `trace_model_call`, but it relies on environment variables. There is no shared CLI bootstrap that loads LangSmith credentials from repo-local `.env`, so CLI runs can miss tracing even when credentials are stored locally.
- CLI commands are implemented per agent family (`linkedin`, `instagram`, `leads`, `outreach`). There is no Knowt CLI in the current `main` branch, so CLI work only applies to the command surfaces that actually exist.
- Tests cover the shared agent runtime, provider tracing helpers, and the LinkedIn/Instagram CLI and agent harnesses. That gives a direct regression surface for this task.

Codebase conventions relevant to this change:

- Runtime behavior is configured with small frozen dataclasses and passed explicitly.
- Agents prefer constructor-time wiring and `from_memory(...)` helpers for CLI-backed flows.
- Existing code uses repo-local `.env` parsing through `harnessiq.config.credentials.parse_dotenv_file`.
- The repository favors deterministic, fail-open runtime behavior around optional integrations.

### 1b: Task Cross-Reference

User request: make LinkedIn, Instagram, Knowt, and ultimately all agents use the LangChain/LangSmith tracing provider by default across SDK, CLI, and the base agent class; tracing must fail open when credentials are absent.

Concrete code mapping:

- Default agent-level tracing belongs in `harnessiq/agents/base/agent.py`.
  - Root agent runs can be wrapped here so every agent invocation produces a top-level trace by default.
  - Tool execution can be wrapped here so tool spans are also universal.
- Tracing configuration belongs in `harnessiq/shared/agents.py`.
  - `AgentRuntimeConfig` needs a place to carry explicit tracing settings for SDK users.
  - Because concrete agents rebuild `AgentRuntimeConfig`, they must preserve tracing fields instead of dropping them.
- Fail-open semantics belong in `harnessiq/providers/langsmith.py`.
  - This is the shared boundary for root runs, tool calls, and the existing Grok model span integration.
  - Making this layer credential-aware and resilient prevents both SDK and CLI runs from failing when tracing is unavailable.
- CLI auto-wiring belongs in existing command modules.
  - `harnessiq/cli/linkedin/commands.py`
  - `harnessiq/cli/instagram/commands.py`
  - `harnessiq/cli/leads/commands.py`
  - `harnessiq/cli/exa_outreach/commands.py`
  - These run paths need to seed LangSmith-related environment variables from repo-local `.env` before model factories are created, and should pass a tracing-aware runtime config into agents where supported.
- Agent constructor propagation must be updated in:
  - `harnessiq/agents/linkedin/agent.py`
  - `harnessiq/agents/instagram/agent.py`
  - `harnessiq/agents/knowt/agent.py`
  - `harnessiq/agents/leads/agent.py`
  - `harnessiq/agents/exa_outreach/agent.py`
  - `harnessiq/agents/email/agent.py`
  - These are the agents that currently reconstruct `AgentRuntimeConfig` or need a `runtime_config` entry point added.
- Test blast radius:
  - `tests/test_agents_base.py`
  - `tests/test_providers.py`
  - `tests/test_linkedin_cli.py`
  - `tests/test_instagram_cli.py`
  - `tests/test_linkedin_agent.py`
  - `tests/test_instagram_agent.py`
  - `tests/test_knowt_agent.py`

Behavior to preserve:

- Agent runs must continue to work with no LangSmith credentials present.
- Existing Grok model tracing should continue to work, but become safe when credentials are absent.
- Existing CLI flows and agent constructor defaults must remain backward compatible.

### 1c: Assumption & Risk Inventory

Assumptions:

- The user said “langchain provider,” but the repository’s actual tracing integration is `langsmith`. I am interpreting the request as “LangSmith traces visible in the user’s LangChain account,” because that is what the current code and dependency graph support.
- Repo-local `.env` is the expected CLI credential source when credentials are not already exported in the shell.
- Supporting both `LANGSMITH_*` and legacy `LANGCHAIN_*` environment names is useful because the user’s wording mixes the two brands.
- There is no separate Knowt CLI on current `main`, so “CLI” coverage applies to the existing command surfaces.

Risks:

- Wrapping the whole run loop and tool execution in tracing can accidentally swallow real agent errors if the fail-open logic is too broad.
- Adding tracing fields to `AgentRuntimeConfig` can break constructors if not propagated through all agent wrappers.
- CLI env loading can accidentally overwrite explicitly exported shell credentials if implemented incorrectly.
- If both base-agent tracing and model-adapter tracing emit overlapping spans, nested traces must remain coherent rather than duplicative in a confusing way.
- The local dirty root worktree contains related files, so implementation must remain isolated to the clean worktree off updated `main`.

Phase 1 complete.
