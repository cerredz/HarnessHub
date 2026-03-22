# Ticket 2: Creatify Provider

## Title
Add `harnessiq/providers/creatify/` with full API operation catalog, client, and credential model

## Intent
Creatify (creatify.ai) is an AI video creation platform. This ticket adds a fully typed Creatify provider under `harnessiq/providers/creatify/` covering the complete documented API surface: URL-to-video, AI avatar generation, text-to-speech, asset creation, custom templates, and workspace management. The provider follows the same frozen-dataclass + operation-catalog + MCP-tool-factory pattern established by the existing providers and the Resend integration, making Creatify operations available to any agent that registers the Creatify tool.

## Scope
**Creates:**
- `harnessiq/providers/creatify/__init__.py`
- `harnessiq/providers/creatify/api.py`
- `harnessiq/providers/creatify/client.py`
- `harnessiq/providers/creatify/operations.py`
- `tests/test_creatify_provider.py`

**Does not touch:** any existing provider, any agent module, `harnessiq/tools/`, `harnessiq/config/` (config credential model added here but the loader itself is ticket 1's domain).

## Relevant Files
| File | Change |
|---|---|
| `harnessiq/providers/creatify/__init__.py` | Create: curated exports |
| `harnessiq/providers/creatify/api.py` | Create: DEFAULT_BASE_URL, build_headers(), URL builders |
| `harnessiq/providers/creatify/client.py` | Create: CreatifyCredentials, CreatifyClient |
| `harnessiq/providers/creatify/operations.py` | Create: operation catalog, tool definition, tool factory |
| `tests/test_creatify_provider.py` | Create: unit tests |

## Approach

**Authentication:** Creatify uses two custom headers: `X-API-ID` and `X-API-KEY`. Both are required on every request. `build_headers()` in `api.py` accepts both and returns the header dict.

**Base URL:** `https://api.creatify.ai`

**CreatifyCredentials (frozen dataclass):**
```
api_id: str
api_key: str
base_url: str = DEFAULT_BASE_URL
timeout_seconds: float = 60.0
```
`__post_init__`: validate both non-blank. `masked_api_key()` and `as_redacted_dict()` for safe logging.

**CreatifyClient (frozen dataclass):** `credentials` + `request_executor: RequestExecutor = request_json`. Exposes `prepare_request()` + `execute_operation()` following the ResendClient pattern.

**Operation catalog** — all resources documented in the Creatify API:

| Category | Operations |
|---|---|
| Link to Video | create (POST /api/link_to_videos/), get (GET /api/link_to_videos/{id}/), preview (POST /api/link_to_videos/{id}/preview/), render (POST /api/link_to_videos/{id}/render/) |
| Aurora Avatar | create (POST /api/aurora/), get (GET /api/aurora/{id}/), preview, render |
| AI Avatar v1 | create (POST /api/lipsyncs/), get (GET /api/lipsyncs/{id}/), preview, render |
| AI Avatar v2 | create (POST /api/lipsyncs_v2/), get (GET /api/lipsyncs_v2/{id}/), preview, render |
| AI Shorts | create (POST /api/ai-shorts/), get (GET /api/ai-shorts/{id}/), preview, render |
| AI Scripts | create (POST /api/ai-scripts/), get (GET /api/ai-scripts/{id}/) |
| AI Editing | create (POST /api/ai_editing/), get (GET /api/ai_editing/{id}/), preview, render |
| Ad Clone | create (POST /api/ad-clone/), get (GET /api/ad-clone/{id}/) |
| Asset Generator | create (POST /api/ai-generation/), get (GET /api/ai-generation/{id}/) |
| Custom Templates | list (GET /api/custom-templates/), get (GET /api/custom-templates/{id}/), create job (POST /api/custom-template-jobs/), get job (GET /api/custom-template-jobs/{id}/) |
| IAB Images | create (POST /api/iab-images/), get (GET /api/iab-images/{id}/) |
| Inspiration | create (POST /api/inspiration/), get (GET /api/inspiration/{id}/), list (GET /api/inspiration/) |
| Product to Video | create (POST /api/product_to_videos/), get (GET /api/product_to_videos/{id}/), preview, render |
| Links | list (GET /api/links/), create (POST /api/links/), update (PUT /api/links/{id}/) |
| Music | list (GET /api/musics/), list categories (GET /api/music-categories/) |
| Custom Avatars | list (GET /api/personas/), create (POST /api/personas/), delete (DELETE /api/personas/{id}/) |
| Text-to-Speech | create (POST /api/text_to_speech/), get (GET /api/text_to_speech/{id}/) |
| Voices | list (GET /api/voices/), create/clone (POST /api/voices/), delete (DELETE /api/voices/{id}/), get quota (GET /api/voices/quota/) |
| Workspace | get credits (GET /api/remaining-credits/) |

**Async job pattern:** Many Creatify operations are async (preview, render). The operation catalog represents these as standard POST/GET operations. The caller polls the GET endpoint to check job status (`pending`, `in_queue`, `running`, `failed`, `done`). No async client machinery is needed — the operation catalog simply models the two-step request.

**Tool definition:** `CREATIFY_REQUEST` tool key. Single MCP-style tool with `operation` enum over all operation names. `path_params`, `query`, `payload` follow the Resend pattern.

## Assumptions
- Ticket 1 is merged — `harnessiq/providers/http.py` already maps `"creatify"` in `_infer_provider_name()`.
- Creatify's API follows the documented REST paths exactly. Minor path variations resolved against official docs.
- `X-API-ID` and `X-API-KEY` are stable identifiers per Creatify's dashboard; no OAuth flow needed.
- The `webhook_url` parameter (present in text-to-speech and others) is passed through in the payload, not handled by the client.

## Acceptance Criteria
- [ ] `from harnessiq.providers.creatify import CreatifyCredentials, CreatifyClient, create_creatify_tools` works
- [ ] `CreatifyCredentials(api_id="", api_key="key")` raises `ValueError`
- [ ] `CreatifyCredentials(api_id="id", api_key="key").as_redacted_dict()` does not include raw key
- [ ] `build_creatify_operation_catalog()` returns operations for all 19 resource categories
- [ ] `CreatifyClient.prepare_request("create_link_to_video", payload={...})` builds correct URL + headers
- [ ] `create_creatify_tools(credentials=...)` returns a `RegisteredTool` tuple registerable in `ToolRegistry`
- [ ] Fake executor injected via `CreatifyClient(request_executor=fake)` is called with correct URL and headers
- [ ] All new tests pass; all existing tests pass

## Verification Steps
1. `python -m pytest tests/test_creatify_provider.py -v`
2. `python -m pytest tests/ -v` — full suite green
3. `python -m py_compile harnessiq/providers/creatify/*.py`
4. `python -c "from harnessiq.providers.creatify import CreatifyCredentials; c = CreatifyCredentials(api_id='id', api_key='key'); print(c.as_redacted_dict())"`

## Dependencies
- Ticket 1 (hostname map must be in place)

## Drift Guard
This ticket must not modify any existing provider, add any CLI command, touch `harnessiq/agents/`, or introduce any external HTTP library. The Creatify provider is purely additive.
