# Self-Critique — All 5 Providers

## Issues Found and Fixed

### 1. Test catalog count assertions were wrong
Three tests asserted incorrect operation counts (my planning estimates were slightly off from the actual catalog sizes). Fixed by querying the actual catalog counts before writing the assertions.

### 2. Apollo `test_catalog_returns_all_operations` asserting 25 not 25
Apollo catalog has exactly 25 operations. Test passes. No issue.

## Issues Reviewed (No Change Needed)

### Dual implementation of tool definition functions
Both `harnessiq/providers/{name}/operations.py` and `harnessiq/tools/{name}/operations.py` contain separate `build_{name}_request_tool_definition` and `create_{name}_tools` functions. The exa provider follows the same pattern. The tool-layer versions have richer descriptions. This matches the established pattern.

### ZeroBounce `build_headers()` takes no arguments
Correct — ZeroBounce auth is via query param, not header. The function signature is intentionally different from Apollo/Lusha. This is correct and documented.

### Expandi `masked_api_secret()` extra method
Added because Expandi has two credentials. Having both `masked_api_key()` and `masked_api_secret()` is appropriate and follows the principle that `as_redacted_dict()` must never expose raw secrets.

### Query param injection pattern (ZeroBounce, Expandi, Smartlead)
The `merged_query` dict approach correctly puts auth params first, then caller query params, so callers cannot accidentally overwrite the auth params with colliding keys. This is the right approach.

### Lusha `api_key` header is lowercase
Intentional and correct per Lusha documentation. Not a mistake.

## Verdict
All 5 providers are correct, follow established conventions, have comprehensive tests, and contain no tech debt. No further changes needed.
