# Ticket 2 — Migrate creatify tool factory to `harnessiq/tools/creatify/`

## Title
Move creatify tool registry from `providers/creatify/operations.py` into `harnessiq/tools/creatify/`, add key constant to shared, enhance description

## Intent
PR #42 feedback: the tool registry (`create_creatify_tools()`, `build_creatify_request_tool_definition()`) lives inside the provider layer, which should only describe API operations. Moving it to `tools/creatify/` follows the file index mandate and makes the tool layer discoverable alongside other tools.

## Scope
**In scope:**
- Create `harnessiq/tools/creatify/__init__.py` and `harnessiq/tools/creatify/operations.py`
- Move tool factory + tool definition builder from `providers/creatify/operations.py` to `tools/creatify/operations.py`
- Add `CREATIFY_REQUEST = "creatify.request"` to `harnessiq/shared/tools.py`
- Update `providers/creatify/operations.py` to re-export the tool factory for backward compat
- Enhance the tool description string to be more semantically rich
- Update test imports accordingly

**Out of scope:**
- Changing the operation catalog structure
- Changing the credential model
- Any other provider

## Relevant Files
- `harnessiq/tools/creatify/__init__.py` — **create**: module marker + public exports
- `harnessiq/tools/creatify/operations.py` — **create**: tool factory + definition builder (migrated + enhanced)
- `harnessiq/providers/creatify/operations.py` — **update**: remove tool factory, keep catalog only; add re-export shim
- `harnessiq/shared/tools.py` — **update**: add `CREATIFY_REQUEST` constant
- `tests/test_creatify_provider.py` — **update**: import tool factory from new location

## Approach
1. Create `harnessiq/tools/creatify/` directory.
2. Write `tools/creatify/operations.py` importing the catalog accessors from `providers/creatify/operations.py` and containing `build_creatify_request_tool_definition()` + `create_creatify_tools()` + enhanced description builder.
3. The description should explain: what Creatify does (AI video creation platform), what categories of operations are available, when to use path_params vs payload, and the lifecycle pattern (create → preview → render).
4. Update `providers/creatify/operations.py`: remove `build_creatify_request_tool_definition` and `create_creatify_tools`, add re-export imports from `tools/creatify/operations.py`.
5. Add `CREATIFY_REQUEST = "creatify.request"` to `shared/tools.py` and its `__all__`.
6. Update test imports.

## Assumptions
- The `CreatifyOperation` dataclass and `_CREATIFY_CATALOG` stay in `providers/creatify/operations.py` because they describe the API, not the tool layer.
- Backward-compat re-exports prevent breaking any consumer that imports from the old path.

## Acceptance Criteria
- [ ] `harnessiq/tools/creatify/operations.py` contains `create_creatify_tools` and `build_creatify_request_tool_definition`
- [ ] `CREATIFY_REQUEST` is importable from `harnessiq.shared.tools`
- [ ] Tool description mentions Creatify's purpose, operation categories, and usage guidance
- [ ] All existing creatify tests pass
- [ ] `mypy` reports no new type errors

## Verification Steps
1. `python -c "from harnessiq.tools.creatify.operations import create_creatify_tools; from harnessiq.shared.tools import CREATIFY_REQUEST; print(CREATIFY_REQUEST)"`
2. `pytest tests/test_creatify_provider.py -v`
3. `mypy harnessiq/tools/creatify/ harnessiq/providers/creatify/`

## Dependencies
None (can run in parallel with ticket 3+)

## Drift Guard
This ticket must not restructure the operation catalog itself, change HTTP behavior, or touch any provider other than creatify.
