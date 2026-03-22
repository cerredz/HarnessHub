## Task

Add five new providers to the provider layer and tool layer: Apollo.io, ZeroBounce, Expandi, Smartlead, Lusha. Each provider requires extensive API research to cover the full suite of capabilities.

---

### 1a: Structural Survey

HarnessHub (`harnessiq`) is a production Python SDK for AI agent pipelines. The codebase already has 15 providers implemented (arcads, coresignal, creatify, exa, instantly, leadiq, lemlist, outreach, peopledatalabs, phantombuster, proxycurl, resend, salesforge, snovio, zoominfo).

**Provider Layer** (`harnessiq/providers/{name}/`): 4-file package pattern:
- `api.py` — `DEFAULT_BASE_URL`, `build_headers()`, `url()` helper using `join_url`
- `client.py` — `{Name}Credentials` (frozen/slots dataclass with `__post_init__` validation, `masked_api_key()`, `as_redacted_dict()`), `{Name}Client` (frozen/slots dataclass with `credentials` + `request_executor: RequestExecutor = request_json`)
- `operations.py` — `{Name}Operation` dataclass, `{Name}PreparedRequest`, `_EXA_CATALOG`-style `OrderedDict`, `_op()` helper, `build_{name}_operation_catalog()`, `get_{name}_operation()`, `build_{name}_request_tool_definition()`, `create_{name}_tools()`, `_build_prepared_request()`, helper functions
- `__init__.py` — public re-exports of credentials, client, key types

**Tool Layer** (`harnessiq/tools/{name}/`): 2-file package:
- `operations.py` — mirrors provider operations, duplicates `build_{name}_request_tool_definition()` and `create_{name}_tools()` with richer descriptions, imports from provider layer for operation catalog
- `__init__.py` — re-exports from operations.py

**Registration** (2 shared files per provider):
1. `harnessiq/shared/tools.py` — add `{NAME}_REQUEST = "{name}.request"` constant + add to `__all__`
2. `harnessiq/toolset/catalog.py` — add `ToolEntry` to `PROVIDER_ENTRIES` + entry to `PROVIDER_FACTORY_MAP`

**Tests**: `tests/test_{name}_provider.py` — unittest.TestCase; covers credentials validation, API builders, operation catalog, client (mock executor)

**Auth patterns in use:**
- Header `x-api-key`: Exa
- Header `X-Api-Key` or `api-key`: Apollo.io
- Query param `api_key=`: Instantly, Salesforge, Smartlead, ZeroBounce
- Dual query params `key=&secret=`: Expandi v1
- Dual header credentials (`api_id`+`api_key`): Creatify, Arcads
- Header `api_key`: Lusha
- OAuth2 Bearer: Outreach, Snovio

**HTTP transport**: `harnessiq/providers/http.py` — `RequestExecutor` protocol, `request_json()`, `join_url(base, path, query=None)`, `ProviderHTTPError`

**Key conventions**:
- All dataclasses `frozen=True, slots=True`
- `join_url()` handles query string building
- Tool key format: `{provider}.request`
- Tool factory signature: `create_{name}_tools(*, credentials=None, client=None, allowed_operations=None) -> tuple[RegisteredTool, ...]`
- Operations are declared as `OrderedDict` with `_op()` factory helper

---

### 1b: Task Cross-Reference

**5 providers to add:**

| Provider | Base URL | Auth | Key Patterns |
|----------|----------|------|--------------|
| Apollo.io | `https://api.apollo.io/api/v1` | Header `X-Api-Key` | People search/enrich, org search/enrich, contacts CRUD, sequences, email accounts, deals, tasks, calls |
| ZeroBounce | `https://api.zerobounce.net` (+ `https://bulkapi.zerobounce.net`) | Query `api_key=` | Email validation, bulk file ops, scoring, email finder, activity data, credits |
| Expandi | `https://api.liaufa.com/api/v1` | Query params `key=&secret=` (v1) or headers (v2) | Campaigns, campaign contacts, LinkedIn accounts, messaging, webhooks |
| Smartlead | `https://server.smartlead.ai/api/v1` | Query `api_key=` | Campaigns CRUD, sequences, email accounts, leads, analytics, webhooks, client mgmt |
| Lusha | `https://api.lusha.com` | Header `api_key` | Person enrich, company enrich, bulk enrich, prospecting search, signals, lookalikes, webhooks |

**Files created per provider (×5):**
- `harnessiq/providers/{name}/api.py`
- `harnessiq/providers/{name}/client.py`
- `harnessiq/providers/{name}/operations.py`
- `harnessiq/providers/{name}/__init__.py`
- `harnessiq/tools/{name}/operations.py`
- `harnessiq/tools/{name}/__init__.py`
- `tests/test_{name}_provider.py`

**Files modified (×5, once per provider ticket):**
- `harnessiq/shared/tools.py` — add constant, add to `__all__`
- `harnessiq/toolset/catalog.py` — add `ToolEntry` + `PROVIDER_FACTORY_MAP` entry

**Special cases:**
- **ZeroBounce**: needs `bulk_base_url` second credential field; operations routed to correct base URL
- **Expandi**: needs `api_key` + `api_secret` dual credentials, passed as query params `key=&secret=`

---

### 1c: Assumption & Risk Inventory

1. **ZeroBounce dual base URL**: Handled by adding `bulk_base_url: str = DEFAULT_BULK_BASE_URL` to `ZeroBounceCredentials`. Operations have a `use_bulk_base: bool` flag; `_build_prepared_request` selects the correct base URL.

2. **Expandi dual credentials**: `api_key` + `api_secret` both required, appended as `?key=&secret=` to every request. Models after Creatify's `api_id`+`api_key` pattern but renamed semantically.

3. **Apollo master key docs note**: Documented in operation descriptions; transparent to the HTTP layer. The credential is just an API key string.

4. **ZeroBounce filter allowlist (form-encoded)**: The `/v2/filters/add` and `/v2/filters/delete` endpoints use `application/x-www-form-urlencoded`. Our HTTP layer only sends JSON. We include these operations but pass the data as query params which ZeroBounce also accepts.

5. **Smartlead `api_key` is a query param, not a header**: Handled in `build_headers()` by returning minimal headers and appending `api_key` to the URL via `join_url(base, path, query={api_key: ...})`.

6. **No ambiguities require user input**: All APIs are publicly documented with clear auth patterns, endpoint structures, and base URLs. Proceeding directly to Phase 3.

**Phase 1 complete.**
