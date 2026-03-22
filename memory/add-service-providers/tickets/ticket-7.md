# Ticket 7: Exa Provider

## Title
Add `harnessiq/providers/exa/` with full search API operation catalog, client, and credential model

## Intent
Exa (exa.ai) is an AI-powered neural web search API that enables semantic search, content extraction, similarity-based discovery, direct answer generation, and asynchronous deep research. Its API surface is compact but distinctive — five primary endpoints plus team/API-key management and an emerging Websets capability. This ticket adds the Exa provider with `x-api-key` header authentication and an operation catalog covering the full documented endpoint set. Exa is the only provider in this group focused on information retrieval rather than outreach or content creation.

## Scope
**Creates:**
- `harnessiq/providers/exa/__init__.py`
- `harnessiq/providers/exa/api.py`
- `harnessiq/providers/exa/client.py`
- `harnessiq/providers/exa/operations.py`
- `tests/test_exa_provider.py`

## Relevant Files
| File | Change |
|---|---|
| `harnessiq/providers/exa/__init__.py` | Create: curated exports |
| `harnessiq/providers/exa/api.py` | Create: DEFAULT_BASE_URL, build_headers(), URL builders |
| `harnessiq/providers/exa/client.py` | Create: ExaCredentials, ExaClient |
| `harnessiq/providers/exa/operations.py` | Create: operation catalog, tool definition, factory |
| `tests/test_exa_provider.py` | Create: unit tests |

## Approach

**Authentication:** Custom API key header. Header: `x-api-key: <api_key>`. Note lowercase header name (distinct from `X-API-KEY` used by Creatify).

**Base URL:** `https://api.exa.ai`

**ExaCredentials (frozen dataclass):**
```
api_key: str
base_url: str = DEFAULT_BASE_URL
timeout_seconds: float = 60.0
```
`__post_init__`: validate non-blank. `masked_api_key()` + `as_redacted_dict()`.

**Operation catalog** — all documented Exa endpoints:

| Category | Operation | Method | Path |
|---|---|---|---|
| Search | search | POST | /search |
| Contents | get-contents | POST | /contents |
| Find Similar | find-similar | POST | /findSimilar |
| Answer | answer | POST | /answer |
| Research | create-research-task | POST | /research/create |
| Research | get-research-task | GET | /research/get |
| Research | list-research-tasks | GET | /research/list |
| Team | list-api-keys | GET | /team/api-keys |
| Team | create-api-key | POST | /team/api-keys |
| Team | get-api-key | GET | /team/api-keys/{id} |
| Team | update-api-key | PATCH | /team/api-keys/{id} |
| Team | delete-api-key | DELETE | /team/api-keys/{id} |
| Team | get-api-key-usage | GET | /team/api-keys/{id}/usage |

**Key request parameters (passed through `payload`):**

- `search`: `query` (required), `type` (`"auto" | "instant" | "deep" | "fast"`), `numResults`, `includeDomains`, `excludeDomains`, `startPublishedDate`, `endPublishedDate`, `category`, `contents` (inline content extraction config)
- `get-contents`: `urls` (required, array), `text`, `highlights`, `summary`, `livecrawl`
- `find-similar`: `url` (required), `numResults`, `includeDomains`, `excludeDomains`, `contents`
- `answer`: `query` (required), `text`, `stream` (note: streaming not handled by this client — synchronous only)
- `create-research-task`: `query` (required), `outputSchema` (optional JSON schema for structured output)
- `get-research-task` / `get-api-key`: `id` or `taskId` via `path_params`

**Async research pattern:** `create-research-task` returns a `taskId`. The caller polls `get-research-task` until the task status is `completed`. No special polling logic in the client.

**Tool definition:** `EXA_REQUEST` key. MCP-style with `operation` enum, `path_params`, `query`, `payload`.

## Assumptions
- Ticket 1 is merged.
- Lowercase `x-api-key` header is the documented Exa auth header; this is intentional and correct.
- Streaming (`/answer` with `stream: true`) is not supported in this client — the `stream` parameter is accepted in the payload but the client does not handle chunked responses.
- Websets API (create/manage web data collections) is in beta and not included in the stable operation catalog.

## Acceptance Criteria
- [ ] `from harnessiq.providers.exa import ExaCredentials, ExaClient, create_exa_tools` works
- [ ] `ExaCredentials(api_key="")` raises `ValueError`
- [ ] `build_headers(api_key)` returns `{"x-api-key": "<key>"}` (lowercase)
- [ ] `build_exa_operation_catalog()` covers all 13 operations across 4 categories
- [ ] `prepare_request("search", payload={"query": "AI news"})` builds `POST https://api.exa.ai/search`
- [ ] `prepare_request("get-research-task", path_params={"taskId": "t1"})` builds correct GET URL
- [ ] `create_exa_tools(credentials=...)` returns registerable tuple
- [ ] All new and existing tests pass

## Verification Steps
1. `python -m pytest tests/test_exa_provider.py -v`
2. `python -m pytest tests/ -v`
3. `python -m py_compile harnessiq/providers/exa/*.py`
4. `python -c "from harnessiq.providers.exa import ExaCredentials; print(ExaCredentials(api_key='k').as_redacted_dict())"`

## Dependencies
- Ticket 1

## Drift Guard
This ticket must not implement streaming response handling, Websets API operations (beta), or any changes outside the `exa/` subfolder and its test file. The lowercase header name is correct and intentional — do not normalize it to title case.
