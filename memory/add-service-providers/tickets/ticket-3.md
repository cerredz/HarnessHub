# Ticket 3: Arcads Provider

## Title
Add `harnessiq/providers/arcads/` with full API operation catalog, client, and credential model

## Intent
Arcads (arcads.ai) is an AI-powered video ad creation platform that converts scripts and actor selections into marketing videos. Its API enables programmatic product management, script authoring, folder organization, situation browsing, and video generation. This ticket adds the Arcads provider following the same frozen-dataclass + operation-catalog pattern, with Basic-Auth credential handling (clientId:clientSecret, Base64-encoded) distinct from the Bearer and API-key patterns used elsewhere in the SDK.

## Scope
**Creates:**
- `harnessiq/providers/arcads/__init__.py`
- `harnessiq/providers/arcads/api.py`
- `harnessiq/providers/arcads/client.py`
- `harnessiq/providers/arcads/operations.py`
- `tests/test_arcads_provider.py`

**Does not touch:** any existing provider, any agent, `harnessiq/tools/`, config layer.

## Relevant Files
| File | Change |
|---|---|
| `harnessiq/providers/arcads/__init__.py` | Create: curated exports |
| `harnessiq/providers/arcads/api.py` | Create: DEFAULT_BASE_URL, build_headers(), URL builders |
| `harnessiq/providers/arcads/client.py` | Create: ArcadsCredentials, ArcadsClient |
| `harnessiq/providers/arcads/operations.py` | Create: operation catalog, tool definition, tool factory |
| `tests/test_arcads_provider.py` | Create: unit tests |

## Approach

**Authentication:** Arcads uses HTTP Basic Auth. The `Authorization` header value is `Basic <base64(clientId:clientSecret)>`. This encoding is performed at credentials time (in `build_headers()`) so the raw secret never flows through the request path as a plain string.

```python
import base64
token = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
headers = {"Authorization": f"Basic {token}"}
```

**Base URL:** `https://external-api.arcads.ai`

**ArcadsCredentials (frozen dataclass):**
```
client_id: str
client_secret: str
base_url: str = DEFAULT_BASE_URL
timeout_seconds: float = 60.0
```
`__post_init__`: validate both non-blank. `as_redacted_dict()` masks the client_secret (shows first 3 chars + asterisks + last 4).

**Operation catalog** — all documented Arcads API resources:

| Category | Operations |
|---|---|
| Products | create (POST /v1/products), list (GET /v1/products) |
| Folders | create (POST /v1/folders), list by product (GET /v1/products/{productId}/folders) |
| Situations | list (GET /v1/situations, paginated) |
| Scripts | create (POST /v1/scripts), list by folder (GET /v1/folders/{folderId}/scripts), update (PUT /v1/scripts/{scriptId}), generate video (POST /v1/scripts/{scriptId}/generate) |
| Videos | list by script (GET /v1/scripts/{scriptId}/videos) |

**Note on the `generate` operation:** `POST /v1/scripts/{scriptId}/generate` initiates async video generation. The caller polls `GET /v1/scripts/{scriptId}/videos` to monitor status and retrieve the download link once complete.

**Tool definition:** `ARCADS_REQUEST` tool key. MCP-style tool with `operation` enum, `path_params`, `payload`.

## Assumptions
- Ticket 1 is merged.
- The documented endpoints from the Arcads help center (intercom.help/arcads) represent the stable public API surface.
- `clientId` and `clientSecret` are issued from the Arcads dashboard.
- Pagination for `/v1/situations` is passed through via `query` params (no special pagination handling in the client).

## Acceptance Criteria
- [ ] `from harnessiq.providers.arcads import ArcadsCredentials, ArcadsClient, create_arcads_tools` works
- [ ] `ArcadsCredentials(client_id="", client_secret="x")` raises `ValueError`
- [ ] `ArcadsCredentials.as_redacted_dict()` does not expose raw `client_secret`
- [ ] `build_headers()` produces a valid `Authorization: Basic <...>` header
- [ ] `build_arcads_operation_catalog()` covers all 5 resource categories
- [ ] `prepare_request("create_product", payload={...})` builds correct URL and Basic Auth header
- [ ] `prepare_request("generate_video", path_params={"scriptId": "s1"})` builds correct POST URL
- [ ] `create_arcads_tools(credentials=...)` returns a registerable `RegisteredTool` tuple
- [ ] All new tests pass; all existing tests pass

## Verification Steps
1. `python -m pytest tests/test_arcads_provider.py -v`
2. `python -m pytest tests/ -v`
3. `python -m py_compile harnessiq/providers/arcads/*.py`
4. `python -c "from harnessiq.providers.arcads import ArcadsCredentials; c = ArcadsCredentials(client_id='cid', client_secret='csec'); print(c.as_redacted_dict())"`

## Dependencies
- Ticket 1

## Drift Guard
This ticket must not touch any existing provider. The Basic Auth encoding logic must live in `api.py`, not in the client or operations layer. No external base64 libraries — use stdlib `base64`.
