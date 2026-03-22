# Provider API Expansion — Internalization

## 1a: Structural Survey

### Architecture Overview

HarnessIQ is a Python SDK that wraps multiple third-party AI and B2B data APIs behind a uniform agent tooling interface. The key architectural layers:

- `harnessiq/providers/`: Third-party API clients, credential models, request builders, and operation catalogs
- `harnessiq/tools/`: MCP-style tool factories that expose provider operations to AI agents
- `harnessiq/shared/tools.py`: Shared types (`ToolDefinition`, `RegisteredTool`, `ToolArguments`) and canonical tool key constants
- `tests/`: One test file per provider following a consistent pattern

### Two Provider Styles

**New-style providers** (arcads, creatify, exa, instantly, lemlist, outreach):
- `providers/{p}/operations.py`: `_op()` factory with full HTTP method/path/payload_kind metadata → `OrderedDict[str, XOperation]` catalog
- `providers/{p}/client.py`: `XClient.prepare_request()` dispatches via catalog → `XPreparedRequest`
- `tools/{p}/operations.py`: `build_X_request_tool_definition()` + `create_X_tools()` using the same catalog
- Tool handler: calls `client.prepare_request()` then `client.request_executor(...)`

**Old-style providers** (snovio, leadiq, salesforge, phantombuster, zoominfo, peopledatalabs, proxycurl, coresignal):
- `providers/{p}/operations.py`: Descriptive-only catalog (name, category, description)
- `providers/{p}/client.py`: Individual methods per operation (e.g. `client.domain_search(token, domain, ...)`)
- `providers/{p}/requests.py`: Individual request builder functions
- `providers/{p}/api.py`: URL builders per endpoint
- `tools/{p}/operations.py`: Tool factory dispatches via `getattr(client, operation_name)(token, **payload)`

### Proxycurl
Deprecated — shut down January 2025. Preserved for reference only. Do not add new operations.

### Operation Naming Convention
- New-style: snake_case verb_noun (e.g., `list_products`, `create_script`, `generate_video`)
- Old-style: same snake_case but dispatched via method name reflection

### Test Pattern
Every provider has `tests/test_{provider}_provider.py` containing:
1. Credential validation tests (blank values, timeout <= 0)
2. API header tests
3. Operation catalog tests (category coverage, operation count, specific op assertions)
4. Client tests (URL construction, path param interpolation, auth headers, error cases)
5. Tool factory tests (create_tools returns RegisteredTool tuple, handler executes correctly, requires credentials)

---

## 1b: Task Cross-Reference

**Task**: Research each provider's API docs, cross-reference with current implementation, add missing operations to both `providers/{p}/operations.py` and `tools/{p}/operations.py`.

### Providers to audit (non-deprecated, non-LLM):
1. Arcads — new-style
2. Creatify — new-style (50+ ops, likely comprehensive)
3. Exa — new-style
4. Instantly — new-style (70+ ops, likely comprehensive)
5. Lemlist — new-style
6. Outreach — new-style
7. Snov.io — old-style
8. Salesforge — old-style
9. PhantomBuster — old-style
10. ZoomInfo — old-style
11. People Data Labs — old-style
12. Coresignal — old-style
13. LeadIQ — old-style

### What needs updating per provider:

**New-style providers** (arcads, exa, lemlist, outreach):
- `providers/{p}/operations.py`: Add `_op()` entries to `_XCATALOG`
- Test: Update `test_catalog_has_correct_operation_count`, add assertions for new ops

**Old-style providers** (snovio, salesforge, phantombuster, zoominfo, pdl, coresignal, leadiq):
- `providers/{p}/operations.py`: Add entries to `_CATALOG`
- `providers/{p}/api.py`: Add URL builder functions for new endpoints
- `providers/{p}/client.py`: Add methods for new operations
- `providers/{p}/requests.py`: Add request builder functions for new operations
- `tools/{p}/operations.py`: Update tool description to mention new ops
- Tests: Add test cases for new operations

---

## 1c: Assumption & Risk Inventory

1. **Proxycurl is excluded** — marked as deprecated in code comments (shut down Jan 2025). Confirmed skip.
2. **LLM providers excluded** — task says "all providers" but context from file_index shows the non-LLM providers are the focus of expansion; LLM providers (anthropic, openai, gemini, grok) are infrastructure layers, not data provider integrations.
3. **Old-style providers**: Adding operations requires touching 4-5 files per new op vs 1 file for new-style. Risk of missing a file.
4. **Creatify & Instantly**: Current catalogs are very comprehensive (50+ and 70+ ops). Risk of low delta.
5. **API documentation accuracy**: Web research may find outdated or private API endpoints. We should only add operations that are clearly documented in official public API docs.
6. **Old-style tool dispatch**: Uses `getattr(client, operation_name)`. New operations must have matching method names on the client or a routing mechanism.

**Phase 1 complete.**
