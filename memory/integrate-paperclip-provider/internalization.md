### 1a: Structural Survey

Top-level architecture:
- `harnessiq/` is the SDK package. Core public seams for this task are `providers/`, `tools/`, `toolset/`, and `shared/`.
- `harnessiq/providers/` contains provider translation helpers, HTTP utilities, provider-specific API helpers, credentials, clients, and declarative operation catalogs. External service providers follow a stable pattern: `api.py` for URL/header helpers, `client.py` for credential validation plus `prepare_request`/`execute_operation`, `operations.py` for the operation catalog and prepared-request assembly, and `__init__.py` for curated exports.
- `harnessiq/tools/` contains executable tool factories. Provider-backed integrations expose a single MCP-style `namespace.request` tool that accepts `operation`, optional `path_params`, optional `query`, and optional `payload`, then delegates to the provider client.
- `harnessiq/toolset/` exposes the plug-and-play catalog surface. Static provider metadata lives in `catalog.py`; lazy resolution is handled by `registry.py`; module-level convenience accessors live in `__init__.py`.
- `harnessiq/shared/` centralizes cross-cutting constants and small runtime models. For this task, `shared/tools.py` is the key file because it defines provider tool key constants and the canonical `ToolDefinition`/`RegisteredTool` models.
- `tests/` mirrors the runtime layout. Provider integrations are verified with focused unit tests for credentials, API/header helpers, operation catalogs, request preparation, and tool execution. Toolset coverage verifies static catalog registration.

Technology and implementation conventions:
- Language/runtime: Python 3.11+ with stdlib HTTP transport in `harnessiq.providers.http`.
- Request execution is synchronous and JSON-first. Provider helpers lean on `request_json()` and `join_url()`.
- Provider operation catalogs are declarative and stable-order, usually via `OrderedDict`.
- Tool registration uses a single `RegisteredTool` per provider family, keyed as `family.request`.
- Input validation is local and explicit. Credentials use dataclass `__post_init__` validation. Operation handlers validate path/query/payload before executing HTTP requests.
- Public exports are curated through `__init__.py` modules instead of wildcard exports.
- Tests are a mix of `unittest` and `pytest`, but provider tests are predominantly `unittest` and follow highly repetitive conventions that should be preserved.

Data flow for provider-backed tools:
1. Caller resolves a tool from `harnessiq.tools.*` or `harnessiq.toolset`.
2. Tool handler validates arguments and calls the provider client.
3. Client delegates to provider `operations.py` to build a validated prepared request.
4. Prepared request contains method, path, URL, headers, and JSON body.
5. `request_json()` executes the request and returns the decoded response.
6. Tool handler normalizes the result to `{operation, method, path, response}` or a provider-specific equivalent.

Observed codebase inconsistencies relevant to this task:
- Provider tooling is split between `harnessiq.providers.<provider>.operations` and `harnessiq.tools.<provider>.operations`; there is intentional duplication in some families, but the public pattern is still stable.
- The working tree is already dirty in files this task must touch (`shared/tools.py`, `providers/__init__.py`, `toolset/catalog.py`, and others). That creates merge risk if an isolated worktree is created from `HEAD` without the in-flight local state.
- Some tests and support files currently show active in-progress edits elsewhere in the repo. This task must be additive and avoid reverting unrelated work.

### 1b: Task Cross-Reference

User request mapping:
- "Integrate Paperclip into our provider layer" maps to a new provider package under `harnessiq/providers/paperclip/` with the standard files:
  - `api.py` for base URL and auth header helpers.
  - `client.py` for `PaperclipCredentials` and `PaperclipClient`.
  - `operations.py` for the Paperclip operation catalog and prepared-request assembly.
  - `__init__.py` for public exports.
- "Do a comprehensive research/deep dive into its api/github/capabilities" maps to upstream Paperclip primary sources and local artifacts in `memory/integrate-paperclip-provider/`, especially the upstream REST API docs around agents, issues, approvals, activity, costs, heartbeat protocol, and adapter behavior.
- "Register some functionalities of it into our toolset" maps to a new MCP-style provider tool family:
  - `harnessiq/tools/paperclip/__init__.py`
  - `harnessiq/tools/paperclip/operations.py`
  - `harnessiq/shared/tools.py` for `PAPERCLIP_REQUEST`
  - `harnessiq/tools/__init__.py` for exports
  - `harnessiq/toolset/catalog.py` for provider metadata and lazy factory registration
- "Hook them up with tool calls in our tooling layer" maps to the Paperclip request tool definition and handler implementation, following the existing `*.request` provider-backed tool convention.
- "Follow all codebase standards and adhere to `artifacts/file_index.md`" maps to preserving the provider-backed tool boundary. Agents should continue to reach third-party systems through provider clients and the tool layer, not ad hoc HTTP calls.

Relevant existing behavior to preserve:
- External service integrations remain credential-driven and opt-in.
- Tool keys stay in `namespace.request` format and must work with `ToolRegistry` and `ToolsetRegistry`.
- Toolset listing must surface the new provider metadata without requiring credentials.
- Public exports should remain minimal and predictable.

Likely Paperclip capability subset that fits the current Harnessiq pattern:
- Core company/agent discovery and management.
- Issue lifecycle operations, including checkout/release, comments, and issue documents.
- Approval workflow operations.
- Activity log queries.
- Cost event reporting and cost summary queries.

Likely exclusions for the first integration:
- Multipart upload endpoints (attachments, company logo upload) because the current generic provider transport/tooling pattern is JSON-first and does not expose multipart semantics.
- Cookie/session-based board-operator auth flows; Harnessiq provider integrations are currently bearer-credential driven.
- Paperclip adapter runtime internals; Harnessiq should integrate with Paperclip’s control-plane API, not embed Paperclip’s Node runtime.

Blast radius:
- New provider family addition touches provider exports, shared tool constants, tool exports, toolset catalog metadata, and corresponding tests.
- No agent runtime changes are inherently required if the Paperclip surface is exposed as a reusable provider-backed tool.

### 1c: Assumption & Risk Inventory

Assumptions:
- The correct Paperclip project is `paperclipai/paperclip`, whose public docs currently describe a REST API with base URL `http://localhost:3100/api`.
- The most useful Harnessiq integration is against Paperclip’s JSON control-plane API, not its local adapters or UI.
- A bearer-token credential model is sufficient for Harnessiq usage because Paperclip supports agent API keys and run JWTs in the `Authorization` header.
- The user’s request for "some functionalities" allows a curated, high-value subset rather than forcing full coverage of every documented endpoint.

Risks:
- Multipart endpoints would require transport capabilities not shared by most existing provider tools. Supporting them in this ticket would either distort the provider pattern or require extra transport abstractions.
- Paperclip’s docs distinguish agent-run behavior from board-operator behavior. Some endpoints may behave differently depending on token type, so the tool descriptions must be explicit.
- The existing dirty worktree overlaps the exact files this change must modify. Following the skill’s worktree flow literally from `HEAD` would omit local in-flight changes and risks clobbering user work during later integration.
- Paperclip is evolving quickly; operation names and exact payload shapes may drift. Implementation should stay close to current upstream docs and keep the catalog declarative so future expansion is easy.
- The provider HTTP helper may not infer `paperclip` as the provider name for all local deployments, especially `localhost`. This is non-blocking for core functionality but worth noting if error labeling becomes important later.

Resolution stance:
- No blocking ambiguity remains that requires user clarification before implementation. The request leaves the Paperclip surface intentionally open-ended, and the existing Harnessiq provider/tool pattern supports a sensible curated subset without changing surrounding architecture.

Phase 1 complete
