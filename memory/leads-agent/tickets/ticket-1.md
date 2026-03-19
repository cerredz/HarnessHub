Title: Add Apollo provider and MCP-style tool integration

Issue URL: https://github.com/cerredz/HarnessHub/issues/149

Intent:
Introduce Apollo as a first-class provider in Harnessiq so the leads agent can discover people and companies, enrich shortlisted records, persist Apollo contacts, inspect usage, and optionally hand contacts off to sequences through the same provider abstraction used elsewhere in the repo.

Scope:
This ticket adds the Apollo provider stack (`credentials`, `api`, `requests`, `client`, `operations`) plus the `apollo.request` tool factory, toolset catalog registration, and provider tests.
This ticket does not implement the leads agent, deterministic transcript pruning, CLI commands, or docs beyond structural catalog/export updates required for the new provider family.

Relevant Files:
- `harnessiq/providers/apollo/__init__.py`: export Apollo provider primitives.
- `harnessiq/providers/apollo/api.py`: define Apollo base URL and auth/header helpers.
- `harnessiq/providers/apollo/credentials.py`: define validated Apollo credential model.
- `harnessiq/providers/apollo/requests.py`: build request payloads and parameter normalization helpers for supported endpoints.
- `harnessiq/providers/apollo/client.py`: prepare and execute Apollo API requests with a consistent repo-native interface.
- `harnessiq/providers/apollo/operations.py`: define the ordered Apollo operation catalog used by the tool layer.
- `harnessiq/tools/apollo/__init__.py`: export Apollo tool helpers.
- `harnessiq/tools/apollo/operations.py`: expose `apollo.request` as an MCP-style request tool.
- `harnessiq/shared/tools.py`: add the `APOLLO_REQUEST` key constant.
- `harnessiq/toolset/catalog.py`: register Apollo in the provider catalog and factory map.
- `tests/test_apollo_provider.py`: add coverage for Apollo credentials, client, operations, and tool behavior.

Approach:
Follow the established provider pattern already used for `leadiq`, `lemlist`, `outreach`, and `zoominfo`. Model Apollo as a provider with a single request tool whose `operation` enum includes the v1 operation set needed for the leads agent: people search, organization search, person/company enrichment, contact persistence, sequence lookup/enrollment, and usage inspection.
Use API-key authentication with explicit credential validation and document the operational assumption that many endpoints require a master API key. Keep the tool interface deterministic by separating `path_params`, `query`, and `payload` where Apollo endpoints need them, matching existing repo conventions rather than inventing Apollo-specific calling semantics.

Assumptions:
- The official Apollo docs accessed during research on March 18, 2026 are the source of truth for endpoint shape and auth requirements.
- API-key auth is the initial integration mode; OAuth partner flows are out of scope.
- Waterfall enrichment webhooks are intentionally deferred from v1.
- The leads agent will consume Apollo through `apollo.request`, not by calling the client directly.

Acceptance Criteria:
- [ ] Apollo provider modules exist and follow the same structural conventions as existing provider families.
- [ ] `apollo.request` is available as a registered provider tool with an explicit operation enum.
- [ ] The Apollo operation catalog covers people search, organization search, person/company enrichment, contact create/search/view/update, sequence search/add-contact, and usage stats.
- [ ] Toolset catalog metadata includes Apollo so `ToolsetRegistry` can resolve the new family.
- [ ] Provider tests verify credentials, request preparation, operation lookup, and tool execution behavior with a fake request executor.

Verification Steps:
- Static analysis: run the project linter against the new Apollo provider and tool files.
- Type checking: run the configured type checker, or if absent, ensure all new code is fully annotated and import-safe.
- Unit tests: run `pytest tests/test_apollo_provider.py`.
- Integration and contract tests: run the broader provider/tool registry coverage that exercises provider registration and shared provider behavior.
- Smoke verification: instantiate the Apollo tool with a fake client and execute representative operations for discovery, enrichment, and usage inspection.

Dependencies:
- None.

Drift Guard:
This ticket must not introduce leads-agent-specific orchestration, runtime transcript pruning logic, CLI flows, or storage abstractions. The only responsibility here is making Apollo a clean, repo-native provider/tool family that other work can compose.
