## Task

Add the following providers to the provider layer: Snov.io, LeadIQ, Salesforge, PhantomBuster, ZoomInfo, People Data Labs, Proxycurl, Coresignal. For each provider research their API/documentation extensively and build the full suite of their API into the provider layer. Each provider gets a subfolder under `harnessiq/providers/`. Credentials for each provider must be added to the config layer.

### 1a: Structural Survey

**Top-level architecture:**
- `harnessiq/` — installable Python SDK package
- `harnessiq/agents/` — provider-agnostic runtime base + concrete agent harnesses (Base, LinkedIn, Email)
- `harnessiq/tools/` — tool runtimes + third-party integrations (Resend, built-ins)
- `harnessiq/providers/` — API client implementations
  - `base.py` — shared translation helpers: `normalize_messages`, `build_openai_style_tool`, `build_anthropic_tool`, `build_gemini_tool_declaration`, `omit_none_values`, `ProviderFormatError`
  - `http.py` — `RequestExecutor` protocol, `ProviderHTTPError`, `request_json`, `join_url`, `_infer_provider_name`
  - `langsmith.py` — LangSmith tracing decorators
  - `anthropic/`, `openai/`, `grok/`, `gemini/` — LLM provider sub-packages
- `harnessiq/shared/` — reusable dataclasses, constants, protocols
- `harnessiq/cli/` — CLI entry points
- `harnessiq/config/` — **does not exist yet** (designed in memory/credential-config-loader/ and referenced in memory/add-service-providers/ticket-1.md, but never implemented)
- `tests/` — unittest suite, file-aligned coverage
- `memory/` — planning artifacts from prior tasks; prior `memory/add-service-providers/` tracked different providers (Creatify, Arcads, Instantly, Outreach, Lemlist, Exa) with GitHub issues #34–#40 and a config-layer ticket #34 that was never merged

**Provider sub-package conventions (strict pattern):**
Every LLM provider sub-package contains five files:
- `api.py` — `DEFAULT_BASE_URL`, `build_headers()`, URL builder functions per endpoint
- `client.py` — `@dataclass(frozen=True, slots=True)` client; fields: `api_key`, `base_url`, `timeout_seconds`, `request_executor`; one method per API operation delegating to request builders
- `requests.py` — pure request-payload builder functions; accept typed primitives, return `dict[str, object]`; use `omit_none_values()` for optional fields
- `helpers.py` — thin compatibility wrappers (`build_request`, `format_tool_definition`) re-exporting from requests.py/tools.py
- `tools.py` — tool format builders (`build_function_tool`, `build_tool_choice`, provider-specific built-in tool builders)
- `__init__.py` — explicit `__all__`, flat re-exports from all four modules

**Key conventions:**
- `from __future__ import annotations` at every module top
- `omit_none_values()` for optional payload fields (deepcopy inside)
- `deepcopy()` for mutable arguments passed into payload dicts
- Frozen dataclasses with slots for client/config objects
- `RequestExecutor = request_json` as default in client dataclass
- `ProviderHTTPError` raised by `request_json` with structured fields
- `_infer_provider_name()` in `http.py` maps hostnames to provider names for error attribution
- Tests: `unittest.TestCase`, mock `request_executor`, assert on payload shapes

**Config layer (designed, not yet built):**
Design lives in `memory/credential-config-loader/clarifications.md` and `memory/add-service-providers/tickets/ticket-1.md`:
- Location: `harnessiq/config/`
- `loader.py` — `CredentialLoader` class (not a dataclass): `load(key) -> str`, `load_all(keys) -> dict[str, str]`. Reads repo `.env` line by line (no external deps). Raises `FileNotFoundError` on missing `.env`, `KeyError` on missing variable.
- `models.py` — `ProviderCredentialConfig` base TypedDict (pattern anchor)
- Each provider's concrete credential TypedDict lives in its own provider package as `credentials.py`
- `harnessiq/__init__.py` lazy-loads `config` via `_EXPORTED_MODULES`

**Important observations/inconsistencies:**
- The 8 new providers are REST/data service APIs (not LLM completion APIs). They do not implement the `ProviderMessage`→completion interface. They are external service clients (like Resend) placed in the provider layer by user directive.
- These providers do NOT need `tools.py` or `helpers.py` (no LLM tool format conversion needed).
- `_infer_provider_name()` in `http.py` currently maps only: openai, anthropic/claude, grok, gemini, resend. All 8 new provider hostnames need entries.

---

### 1b: Task Cross-Reference

**Files to create — config layer foundation:**
- `harnessiq/config/__init__.py`
- `harnessiq/config/loader.py`
- `harnessiq/config/models.py`
- `tests/test_config_loader.py`

**Files to create — provider sub-packages (pattern: api.py, client.py, requests.py, credentials.py, __init__.py):**
- `harnessiq/providers/snovio/` (5 files)
- `harnessiq/providers/leadiq/` (5 files)
- `harnessiq/providers/salesforge/` (5 files)
- `harnessiq/providers/phantombuster/` (5 files)
- `harnessiq/providers/zoominfo/` (5 files)
- `harnessiq/providers/peopledatalabs/` (5 files)
- `harnessiq/providers/proxycurl/` (5 files)
- `harnessiq/providers/coresignal/` (5 files)

**Files to create — tests:**
- `tests/test_snovio_provider.py`
- `tests/test_leadiq_provider.py`
- `tests/test_salesforge_provider.py`
- `tests/test_phantombuster_provider.py`
- `tests/test_zoominfo_provider.py`
- `tests/test_peopledatalabs_provider.py`
- `tests/test_proxycurl_provider.py`
- `tests/test_coresignal_provider.py`

**Files to modify:**
- `harnessiq/providers/http.py` — add 8 hostname entries to `_infer_provider_name()`
- `harnessiq/__init__.py` — add `"config"` to `_EXPORTED_MODULES`
- `artifacts/file_index.md` — register `harnessiq/config/` and all 8 new provider packages

**Behavior to preserve:**
- All existing provider implementations (anthropic, openai, grok, gemini) untouched
- All existing tests green
- `request_json` and `ProviderHTTPError` behavior unchanged
- Existing `_infer_provider_name()` mappings unchanged (additions only)

**Blast radius:**
- Medium-high. 9 new sub-packages, 9 test files, 3 shared file edits. All new code; no modification of existing behavior except additive `_infer_provider_name()` entries and lazy-load registration.

**Prior work note:**
`memory/add-service-providers/` planned a config layer (ticket #34) for different providers (Creatify, Arcads, Instantly, Outreach, Lemlist, Exa). None of it was implemented. The config layer design from that ticket is compatible with this task and will be adopted verbatim. The hostname entries from that prior ticket (#34) are NOT included here — they are for different providers.

---

### 1c: Assumption & Risk Inventory

**Assumptions:**
1. "Full suite of their API" = all documented public REST endpoints grouped into coherent client methods. For ZoomInfo (enterprise API with 30+ endpoints) and People Data Labs (20+ endpoints), this means every documented endpoint category gets a client method.
2. Snov.io uses OAuth 2.0 (client_id + client_secret → access_token). The client will expose a `get_access_token()` method and accept access tokens directly for other calls.
3. LeadIQ uses GraphQL (single POST /graphql endpoint). The client wrapper will expose typed helper methods for each operation query, hiding the GraphQL layer.
4. ZoomInfo requires a two-step auth: POST /authenticate to exchange username+password for a JWT, then use JWT as Bearer. The client will handle this and accept the JWT directly for other operations.
5. Coresignal uses JWT Bearer auth. The client accepts the token directly.
6. These providers do NOT need `tools.py` or `helpers.py` since they are not LLM providers.
7. `credentials.py` lives in each provider package (not in `harnessiq/config/models.py`).
8. The credential TypedDicts are annotation-only TypedDicts (not dataclasses) following the pattern from the planned config layer.
9. `.env`-backed resolution is handled by `CredentialLoader` in `harnessiq/config/`; the provider clients themselves accept raw strings.

**Risks:**
- API documentation accuracy: my knowledge of exact endpoint paths/schemas may be slightly outdated for some providers. Verification steps during quality pipeline should catch any issues.
- LeadIQ GraphQL: wrapping GraphQL queries in Python request builders is non-standard in this codebase. The approach must stay consistent with the REST pattern (typed builder functions returning dicts) while encoding the GraphQL query string.
- ZoomInfo enterprise tier: the ZoomInfo API is enterprise-only. Smoke verification can confirm payload shape but cannot verify against a live API without credentials.
- Salesforge API: documentation is sparse; the client will cover documented endpoints from public API docs.
- Naming: `snovio` (not `snov_io`) follows Python package naming conventions; `peopledatalabs` (one word) is cleaner than `people_data_labs`.

**Decisions:**
- Provider package names: `snovio`, `leadiq`, `salesforge`, `phantombuster`, `zoominfo`, `peopledatalabs`, `proxycurl`, `coresignal`
- No `tools.py` for service providers (correct — LLM tool format conversion is not needed)
- No `helpers.py` unless a `build_request()` compatibility shim is needed later (omit for now to avoid premature abstraction)

Phase 1 complete.
