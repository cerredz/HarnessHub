## Issue 390 Quality Pipeline

### Stage 1: Static Analysis
- No repository linter is configured in `pyproject.toml`.
- Reviewed the Markdown and generator changes manually for style, link consistency, and repo-doc alignment.

### Stage 2: Type Checking
- No repository type checker is configured in `pyproject.toml`.
- `python -m compileall harnessiq`
  - Result: passed.

### Stage 3: Unit Tests
- `pytest tests/test_docs_sync.py`
  - Result: 11 passed.

### Stage 4: Integration & Contract Tests
- `python scripts/sync_repo_docs.py`
  - Result: regenerated `README.md`, `artifacts/commands.md`, and `artifacts/file_index.md`.
- `python scripts/sync_repo_docs.py --check`
  - Result: passed.
- `pytest`
  - Result: not fully green because the current `origin/main` baseline already contains unrelated failures outside this ticket's documentation-only scope.
  - Observed unrelated failing areas:
    - `tests/test_agents_base.py`
    - `tests/test_instagram_agent.py`
    - `tests/test_provider_base.py`
    - `tests/test_providers.py`
    - `tests/test_sdk_package.py`
  - The failures are in runtime/provider code paths untouched by this branch, while the docs-sync suite and generated-doc check both passed.

### Stage 5: Smoke & Manual Verification
- Confirmed the new [docs/dynamic-tool-selection.md](/C:/Users/422mi/HarnessHub/.worktrees/issue-390/docs/dynamic-tool-selection.md) document matches the implemented behavior:
  - static path remains the default
  - dynamic selection is opt-in
  - `allowed_tools` remains the execution ceiling
  - CLI support is limited to existing tool keys/patterns
  - custom callables remain a Python construction concern
- Confirmed [docs/agent-runtime.md](/C:/Users/422mi/HarnessHub/.worktrees/issue-390/docs/agent-runtime.md) and [docs/tools.md](/C:/Users/422mi/HarnessHub/.worktrees/issue-390/docs/tools.md) point to the dedicated dynamic-selection doc instead of duplicating the full contract.
- Confirmed the generated repo docs now surface the new guide in [README.md](/C:/Users/422mi/HarnessHub/.worktrees/issue-390/README.md) and the regenerated artifact references.
