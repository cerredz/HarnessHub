## Stage 1 — Static Analysis

Command:
```powershell
git diff --check
```

Result:
- Passed with no diff-formatting errors.
- Git emitted CRLF normalization warnings for modified files, but no actionable whitespace violations were reported.

## Stage 2 — Type Checking

Result:
- No dedicated type checker is configured in this branch/worktree.
- Validation relied on importing the changed modules through the test suite and direct toolset assertions.

## Stage 3 — Unit Tests

Command:
```powershell
python -m unittest tests.test_instagram_agent tests.test_instagram_cli tests.test_instagram_playwright tests.test_playwright_provider tests.test_sdk_package
```

Result:
- Passed.
- 20 tests ran successfully.
- Coverage included the Instagram agent behavior, CLI flow, Instagram URL normalization, shared Playwright helpers, and packaging smoke/import behavior.

## Stage 4 — Integration & Contract Tests

Command:
```powershell
@'
from harnessiq.toolset import get_family, get_tool, list_tools

assert get_tool("instagram.search_keyword").key == "instagram.search_keyword"
assert [tool.key for tool in get_family("instagram")] == ["instagram.search_keyword"]
entries = {entry.key: entry for entry in list_tools()}
assert entries["instagram.search_keyword"].family == "instagram"
assert entries["instagram.search_keyword"].requires_credentials is False
print("toolset-ok")
'@ | python -
```

Result:
- Passed (`toolset-ok`).
- Confirmed the Instagram tool is registered in the shared built-in toolset catalog and discoverable by key, family, and metadata listing.

## Stage 5 — Smoke & Manual Verification

Observed via automated smoke tests:
- `tests.test_sdk_package` verified wheel/sdist builds and importability of the top-level package plus Instagram agent export.
- `tests.test_instagram_cli` exercised `instagram prepare`, `configure`, `show`, `run`, and `get-emails`.
- `tests.test_instagram_agent` confirmed durable-memory writes, search result persistence, and parameter refresh after `instagram.search_keyword`.

Environment note:
- `pytest` is not installed in either the system interpreter or the repo `.venv`, so the pytest-only file `tests/test_toolset_registry.py` was validated through the direct Python assertion command above instead of `pytest`.
