## Stage 1 - Static Analysis

Configured linter: none found in `pyproject.toml`.

Verification run:
```powershell
python -m py_compile harnessiq/agents/instagram/agent.py harnessiq/tools/instagram.py tests/test_instagram_agent.py
```

Result:
- Passed.

## Stage 2 - Type Checking

Configured type checker: none found in `pyproject.toml`.

Verification:
- Relied on successful `py_compile` for syntax validation.
- New logic stays within existing typed interfaces and dataclass contracts.

Result:
- No repo-configured type-check stage available.

## Stage 3 - Unit Tests

Requested command from ticket:
```powershell
python -m pytest tests/test_instagram_agent.py
```

Result:
- Blocked because `pytest` is not installed in the active interpreter: `No module named pytest`.

Fallback command:
```powershell
python -m unittest tests.test_instagram_agent
```

Fallback result:
- Blocked by an unrelated repository baseline issue before the Instagram tests could run:
  - `NameError: name 'dataclass' is not defined` from `harnessiq/shared/http.py`

## Stage 4 - Integration & Contract Tests

No separate Instagram integration/contract suite was run for this ticket.

Reason:
- The current `main` baseline fails during shared provider import initialization in `harnessiq/shared/http.py` before the Instagram-specific test path can execute.

Result:
- Not completed due unrelated baseline failures outside this ticket's scope.

## Stage 5 - Smoke & Manual Verification

Executed direct source inspection plus syntax validation to confirm:
- `InstagramKeywordDiscoveryAgent.load_parameter_sections()` now emits only `ICP Profiles` and `Recent Searches`
- `Recent Searches` is rendered as a comma-separated keyword string
- `harnessiq/tools/instagram.py` tool results no longer emit `query` or `visited_urls`
- the Instagram prompt no longer instructs the model to read `Recent Search Results`
- the Instagram tests assert the reduced parameter sections and compact tool payloads

Observed result:
- The edited files compile successfully and the reduced context/tool behavior is reflected consistently across runtime, prompt, and tests.
