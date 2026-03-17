# LinkedIn Browser Agent — Internalization

## 1a: Structural Survey

### Package layout
- `harnessiq/agents/linkedin/agent.py` — `LinkedInJobApplierAgent` harness (already built); full browser stub tools + durable memory tools
- `harnessiq/agents/base/agent.py` — `BaseAgent` loop: calls `model.generate_turn(request)`, executes tools, resets context on threshold
- `harnessiq/cli/linkedin/commands.py` — argparse CLI: `prepare`, `configure`, `show`, `run` subcommands; `run` uses `--model-factory` and `--browser-tools-factory` import-path strings
- `harnessiq/providers/grok/` — xAI/Grok HTTP client + request builders (OpenAI-compatible)
- `harnessiq/providers/langsmith.py` — `trace_model_call` and `trace_agent_run` wrappers using LangSmith SDK
- `harnessiq/shared/agents.py` — `AgentModel` protocol (`generate_turn`), `AgentModelRequest`, `AgentModelResponse`, `ToolCall`
- `harnessiq/shared/providers.py` — `ProviderMessage` TypedDict (role: "user"|"assistant"|"system", content: str)

### Key interfaces
- `AgentModel.generate_turn(request: AgentModelRequest) -> AgentModelResponse`
- `AgentModelRequest`: has `system_prompt`, `parameter_sections`, `transcript`, `tools`; `render_parameter_block()`, `render_transcript()`, `estimated_tokens()`
- `AgentModelResponse`: `assistant_message`, `tool_calls: tuple[ToolCall, ...]`, `should_continue`, `pause_reason`
- `ToolCall`: `tool_key` (registry key like "linkedin.navigate"), `arguments`
- `GrokClient.create_chat_completion(model_name, system_prompt, messages, tools, ...)` — builds OpenAI-style request
- Browser tools: 14 stub tools in `build_linkedin_browser_tool_definitions()`; replaced by live Playwright handlers at runtime
- `--model-factory` and `--browser-tools-factory` in CLI `run` command both take `module:callable` strings; factories called with zero args

### Missing pieces (what needs to be built)
1. `GrokAgentModel` — implements `AgentModel`, converts `AgentModelRequest` → Grok messages, parses response → `AgentModelResponse`, wraps with `trace_model_call`
2. Playwright browser session — opens real browser, waits for user login, provides handlers for all 14 browser tools
3. `init-browser` CLI command — standalone browser init with persistent session saved to memory
4. `_handle_run` updates — auto-set `HARNESSIQ_BROWSER_SESSION_DIR` from memory, print applied jobs after run

## 1b: Task Cross-Reference

| Task requirement | File(s) touched | Status |
|---|---|---|
| GrokAgentModel with grok-4-1-fast | `harnessiq/integrations/grok_model.py` (new) | net-new |
| LangSmith tracing | uses existing `trace_model_call` | uses existing |
| Browser init (real browser + login wait) | `harnessiq/integrations/linkedin_playwright.py` (new) | net-new |
| `init-browser` CLI command | `harnessiq/cli/linkedin/commands.py` | modify |
| Print applied jobs after run | `harnessiq/cli/linkedin/commands.py` | modify |
| Auto-set browser session from memory | `harnessiq/cli/linkedin/commands.py` | modify |
| max_turns=20 | `--max-cycles 20` CLI arg | existing |

## 1c: Assumption & Risk Inventory

1. Model name: user says "grok 4.1 fast non reasoning" → using `grok-4-1-fast`; exact xAI API model name may differ
2. Tool name→key mapping: transcript stores `tool_key` ("linkedin.navigate"); Grok API returns tool `name` ("navigate"); need reverse lookup
3. Message format: base agent transcript stores text, not structured tool_calls; using text-flattened alternating user/assistant messages for multi-turn context
4. Factory call signature: current CLI calls factory with zero args; using env var `HARNESSIQ_BROWSER_SESSION_DIR` to pass session dir
5. `should_continue` logic: set to True when tool_calls present OR finish_reason == "tool_calls"; False on "stop"
