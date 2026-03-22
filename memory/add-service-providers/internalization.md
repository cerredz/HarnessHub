## Task

Add six new service providers (creatify, arcards, instantly.ai, outreach.io, lemlist, exa) into the `harnessiq/providers/` layer, with a subfolder per provider and full API surface coverage. Add credentials for each provider into the config layer (which does not yet exist and must be created as `harnessiq/config/`).

---

### 1a: Structural Survey

**Top-level architecture:**

- `harnessiq/` is the installable Python SDK package (setuptools, Python ≥3.11, single runtime dependency: `langsmith`).
- `harnessiq/agents/`: provider-agnostic agent runtime base (`BaseAgent`) plus concrete harnesses (`EmailAgent`, `LinkedInJobApplierAgent`).
- `harnessiq/tools/`: tool runtime layer. Contains built-in tools, general-purpose helpers, filesystem tools, context compaction tools, prompting tools, and third-party service integrations. Currently `harnessiq/tools/resend.py` is the only external-service integration.
- `harnessiq/providers/`: provider-specific HTTP client wrappers and request builders for AI LLM APIs. Currently four providers: `anthropic/`, `openai/`, `grok/`, `gemini/`. Also contains shared `base.py` (message normalization, tool-payload builders), `http.py` (stdlib `RequestExecutor` protocol + `ProviderHTTPError`), and `langsmith.py` (tracing decorators).
- `harnessiq/shared/`: shared type aliases, constants, TypedDicts (`providers.py`, `tools.py`, `agents.py`, `linkedin.py`).
- `harnessiq/cli/`: CLI entrypoints. Root dispatch in `main.py`; LinkedIn-specific commands under `cli/linkedin/`.
- `harnessiq/config/`: **does not yet exist**. Was planned in the credential-config-loader task (issues #28–30, unimplemented) to store credential bindings sourced from a repo-local `.env` file.

**Technology stack:**
- Python 3.11+, stdlib-only networking (no `httpx`, no `requests`), frozen dataclasses, `unittest` test suite
- `langsmith` for tracing; no other external dependencies
- `setuptools` packaging with `harnessiq*` glob — a new `harnessiq/config/` package will be auto-included

**Current provider architecture (under `harnessiq/providers/`):**

Each AI provider has a consistent sub-module layout:
```
{provider}/
  __init__.py     — curated exports
  api.py          — DEFAULT_BASE_URL, build_headers(), URL helper functions
  client.py       — XClient frozen dataclass; _request() delegates to RequestExecutor
  requests.py     — request payload builders (build_X_request, build_X_response, etc.)
  tools.py        — tool-payload translators (build_function_tool, format_tool_definition)
  helpers.py      — provider-specific content/config builders
  messages.py     — (Anthropic only) message/system prompt builders
  content.py      — (Gemini only) content part builders
```

**Resend pattern (the applicable template for new service providers):**

`harnessiq/tools/resend.py` is the canonical example of a non-LLM external API integration. Its pattern:
1. `XCredentials` — frozen dataclass; `api_key`, `base_url`, `user_agent`, `timeout_seconds`; `__post_init__` validation; `masked_api_key()` and `as_redacted_dict()` safety methods
2. `XOperation` — frozen dataclass; `name`, `category`, `method`, `path_hint`, `path_builder`, required/optional path params, payload shape, header flags
3. `XPreparedRequest` — frozen dataclass; validated ready-to-execute request value object
4. `XClient` — frozen dataclass; `credentials` + `request_executor: RequestExecutor`; `prepare_request()` + `execute_operation()`
5. `build_x_operation_catalog()` — returns all supported operations as a tuple
6. `get_x_operation(name)` — operation lookup with clear error
7. `build_x_request_tool_definition(...)` — returns `ToolDefinition` for the MCP-style tool
8. `create_x_tools(...)` — factory that returns `tuple[RegisteredTool, ...]` backed by a client

**HTTP transport:**
- `harnessiq/providers/http.py` contains `request_json()` (stdlib urllib), `join_url()`, `ProviderHTTPError`, and `RequestExecutor` protocol
- `ProviderHTTPError._infer_provider_name()` currently maps known hostnames only — will need updates for each new provider
- All clients inject the `RequestExecutor` protocol for testability (fake executor in tests)

**Credential-config layer (planned, unimplemented):**
- Ticket #28: add `harnessiq/config/` with `.env`-backed credential models and loader store
- Ticket #29: wire agent constructors to accept stored credentials
- Ticket #30: CLI credential management commands
- Clarified design: resolve credentials from repo-local `.env` file; raise if `.env` missing or variable absent; store environment-variable name references, not literal secrets
- `harnessiq/config/` does not yet exist — must be created as part of this task

**Conventions in use:**
- Frozen, slot-based dataclasses for all value/config objects
- `__post_init__` validation with descriptive `ValueError` messages
- `omit_none_values()` to strip `None` keys from payloads
- All public surfaces declared in `__all__` in `__init__.py`
- Test pattern: fake `request_executor` injected via dataclass field; behavior tests, not implementation tests
- No external HTTP library; pure stdlib urllib

**Observed inconsistencies:**
- New service providers (non-LLM) are architecturally more like Resend (in `tools/`) but the user explicitly wants them in `providers/`. The providers layer will therefore contain both LLM provider clients and external-service API clients going forward.
- `ProviderHTTPError._infer_provider_name()` uses hostname sniffing — new providers will need entries added.

---

### 1b: Task Cross-Reference

**Six new service providers requested:**

| Provider | Domain | Category |
|---|---|---|
| creatify | creatify.ai | AI video creation |
| arcards | arcards.io (unconfirmed) | unknown — requires research/clarification |
| instantly.ai | instantly.ai | Cold email / outreach automation |
| outreach.io | outreach.io | Sales engagement platform |
| lemlist | lemlist.com | Cold email / outreach automation |
| exa | exa.ai | AI-powered neural web search |

**Files to be created per provider (6 × ~4 files = ~24 new files):**
```
harnessiq/providers/{provider}/
  __init__.py
  api.py          — DEFAULT_BASE_URL, build_headers(), URL builders
  client.py       — XCredentials, XClient dataclasses
  operations.py   — XOperation catalog, XPreparedRequest, build_x_operation_catalog(), etc.
```

**Files to be created for config layer:**
```
harnessiq/config/
  __init__.py     — exports
  loader.py       — CredentialLoader: reads .env, resolves named vars, raises on missing
  models.py       — ProviderCredentialConfig: stores env-var name references per provider
```

**Files to be modified:**

1. `harnessiq/providers/__init__.py` — update `__all__` to expose new providers (currently exports only shared primitives, not individual provider packages — so probably no change needed here; provider sub-packages are self-contained)
2. `harnessiq/providers/http.py` — `_infer_provider_name()` needs entries for all 6 new provider hostnames
3. `harnessiq/__init__.py` — add `"config"` to `_EXPORTED_MODULES` frozenset
4. `artifacts/file_index.md` — update to document new provider subfolders and `harnessiq/config/`
5. `tests/` — new test file per provider + config layer tests

**Behavior that must be preserved:**
- All existing provider clients (anthropic, openai, grok, gemini) unchanged
- Resend tooling in `harnessiq/tools/resend.py` unchanged
- All existing tests pass
- `harnessiq/__init__.py` lazy-load mechanism unchanged

**Net-new behavior:**
- 6 provider packages under `harnessiq/providers/` each with credentials, client, operation catalog, tool factory
- `harnessiq/config/` package with `.env`-backed credential loading for all new providers

**Blast radius:**
- Medium-to-large: 24+ new files, 6 test files, config layer creation, http.py hostname map update
- Zero risk to existing functionality — all additions are additive

---

### 1c: Assumption & Risk Inventory

**Assumptions:**

1. "Providers layer" means `harnessiq/providers/` subfolders — not `harnessiq/tools/` even though the Resend pattern lives there
2. "Full functionality" means covering all major documented API resource endpoints per provider (CRUD for all resources), not literal 100% endpoint parity
3. The config layer should be created in this task (it was planned but never implemented in credential-config-loader tickets #28–30)
4. Credentials for these providers should follow the `.env`-backed pattern resolved in the credential-config-loader clarifications
5. "arcards" is assumed to be a specific API service — requires research and/or clarification since it's not a widely documented API

**Risks:**

1. **arcards identity unclear**: "arcards" is not a well-known API service. This is the highest-risk item. If the web search doesn't find it, clarification is needed before implementation can proceed.
2. **API surface depth**: "full functionality" for Outreach.io (enterprise sales engagement, 100+ endpoints) could be far more complex than Exa (a few search endpoints). Scoping the operation catalog to "all documented resource categories, primary CRUD actions" is the correct boundary.
3. **Authentication variety**: instantly.ai and lemlist use API-key-based auth; Outreach.io uses OAuth 2.0 in addition to API keys. OAuth flows are outside the scope of an HTTP client that uses static credentials — the client should accept a token string and leave OAuth flow to the caller.
4. **Rate limits and pagination**: Some providers (Outreach, Lemlist) have complex cursor/page-based pagination. The operation catalog approach (pass query params through) handles this without special-casing.
5. **Config layer scope creep**: The credential-config-loader was a multi-ticket effort. For this task, a minimal config layer (credential models + `.env` loader) is appropriate — not the full CLI commands from ticket #30.
6. **Provider module naming**: "instantly.ai" contains a dot; Python module names can't contain dots. The module name must be `instantly` or `instantlyai`.

Phase 1 complete.
