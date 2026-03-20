## Task
Register any missing providers from the user-supplied GTM stack list that have usable APIs, then register their API capabilities into the tooling layer. Adhere to `artifacts/file_index.md`.

### 1a: Structural Survey

Repository shape:

- `harnessiq/` is the shipped SDK package.
- `harnessiq/providers/` contains third-party API integrations and model provider helpers.
- `harnessiq/tools/` contains executable tool factories, including provider-backed MCP-style `*.request` tools.
- `harnessiq/toolset/` contains the static tool catalog and lazy provider-family resolver.
- `harnessiq/shared/` contains constants, shared dataclasses, and provider/tool identifiers.
- `tests/` contains focused unit coverage per provider/tool family plus higher-level registry/package smoke tests.
- `artifacts/file_index.md` is the architectural source of truth for repo structure and expectations.
- `docs/` and `README.md` document the public SDK surface.

Provider/tool conventions observed:

- Each external service usually has:
  - `harnessiq/providers/<provider>/api.py`
  - `harnessiq/providers/<provider>/client.py`
  - `harnessiq/providers/<provider>/operations.py`
  - `harnessiq/providers/<provider>/__init__.py`
  - `harnessiq/tools/<provider>/operations.py`
  - `harnessiq/tools/<provider>/__init__.py`
  - `tests/test_<provider>_provider.py`
- Provider operations are declared in stable ordered catalogs with explicit metadata.
- Provider tools are usually a single MCP-style `namespace.request` tool with:
  - `operation`
  - optional `path_params`
  - optional `query`
  - optional `payload`
- Shared registration points:
  - `harnessiq/shared/tools.py` for `*_REQUEST` constants
  - `harnessiq/toolset/catalog.py` for `ToolEntry` metadata and `PROVIDER_FACTORY_MAP`
  - sometimes `README.md` and docs for discoverability
- Existing provider families are concentrated in search/intelligence, sales engagement, creative/video, Google Drive, and LLM vendors.

Testing strategy:

- Provider-specific tests validate credentials, auth header construction, operation catalog coverage, request preparation, and tool execution.
- `tests/test_toolset_registry.py` validates provider catalog registration.
- `tests/test_sdk_package.py` provides packaging/import smoke coverage.

Observed repository constraints and risks:

- The git worktree is already dirty with many unrelated tracked and untracked changes.
- This task must avoid reverting or colliding with unrelated user work.
- `artifacts/file_index.md` emphasizes provider-backed tools and discourages ad hoc direct API calls.

Relevant existing providers already present in this repo:

- `exa`
- `instantly`
- `leadiq`
- `lemlist`
- `outreach`
- `salesforge`
- `phantombuster`
- `snovio`
- `zoominfo`
- `peopledatalabs`
- `coresignal`
- `proxycurl`
- `arcads`
- `creatify`
- `google_drive`

### 1b: Task Cross-Reference

User-supplied product list:

1. Bitscale
2. Floqer
3. Exa
4. Serper
5. Trellus
6. Replit
7. Attio
8. Kondo
9. InboxApp
10. LeadDelta

Current codebase mapping:

- `Exa` is already implemented in:
  - `harnessiq/providers/exa/`
  - `harnessiq/tools/exa/`
  - `tests/test_exa_provider.py`
- `Instantly` is already implemented but is not part of the numbered list the user asked to diff against.
- No provider families currently exist for:
  - `attio`
  - `inboxapp`
  - `serper`
  - `bitscale`
  - `floqer`
  - `trellus`
  - `replit`
  - `kondo`
  - `leaddelta`

Files likely touched for any confirmed additions:

- `harnessiq/shared/tools.py`
- `harnessiq/toolset/catalog.py`
- `harnessiq/providers/<new_provider>/...`
- `harnessiq/tools/<new_provider>/...`
- `tests/test_<new_provider>_provider.py`
- likely `README.md`

External API verification from official sources during Phase 1:

- `Exa`: confirmed public API and already present in repo.
- `Attio`: confirmed public REST API via `docs.attio.com/rest-api/endpoint-reference/...`.
- `InboxApp`: confirmed public API via `docs.inboxapp.com/` and endpoint reference pages.
- `Serper`: official site clearly markets a Google SERP API (`serper.dev`), but the endpoint reference is less directly indexed than Attio/Inbox.
- `Bitscale`: official docs show integrations, API-key integrations, webhooks, and custom HTTP integrations, but Phase 1 did not confirm a clearly documented public Bitscale service API surface equivalent to existing Harnessiq provider patterns.
- `Floqer`: Phase 1 did not find clearly indexed official public API docs.
- `Trellus`: official API docs found, but the surfaced product appears to be a delivery/logistics API and may not be the same `Trellus` dialer referenced by the user.
- `Replit`: official docs exist, but Phase 1 did not confirm a clean external GTM-service API surface appropriate for this provider layer request.
- `Kondo`: Phase 1 did not find clearly indexed official public API docs.
- `LeadDelta`: Phase 1 did not find clearly indexed official public API docs.

Blast radius:

- Low-to-moderate if limited to new provider families plus shared registration points.
- Higher if the task requires disputed or poorly documented providers, because that would force guessing on endpoint shape, auth model, or product identity.

Behavior that must be preserved:

- Existing provider families and their tests.
- `ToolsetRegistry` catalog invariants.
- Single-tool MCP-style design for provider-backed tools.
- Stable naming and import patterns used across current providers.

### 1c: Assumption & Risk Inventory

Assumptions currently required to proceed:

1. The user wants only products from the numbered list diffed against existing repo support.
2. "Have an API" means a documented public or at least clearly usable product API, not merely webhook support or the ability to connect to other vendors via API keys.
3. It is acceptable to skip products whose official public API surface is unclear or ambiguous instead of reverse-engineering private endpoints.
4. `InboxApp` should be modeled as `inboxapp` in code even though the docs brand the API as `Inbox API`.
5. `Serper` can be implemented from official product information plus stable public endpoint behavior if its formal docs remain less directly indexed than other providers.

Material risks:

1. `Trellus` may refer to a different product than the official API docs found in Phase 1.
2. `Bitscale`, `Floqer`, `Kondo`, and `LeadDelta` may have private or partner-only APIs that are not discoverable from public docs; implementing them would require guesswork.
3. The repo is already dirty, so implementation must be isolated and non-destructive.
4. The `world-class-software-engineer` workflow asks for GitHub issues/worktrees/PRs; local repo state or `gh` auth may block those steps.
5. `Serper` is likely implementable, but the official endpoint reference is less explicit than Attio/Inbox, so operation scope should stay conservative.

Decision boundary after Phase 1:

- Clear additions without guesswork: `attio`, `inboxapp`.
- Likely addition with bounded research risk: `serper`.
- Already present: `exa`.
- Not safe to implement without more direction or stronger official API evidence: `bitscale`, `floqer`, `trellus`, `replit`, `kondo`, `leaddelta`.

Phase 1 complete.
