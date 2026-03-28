## Issue 389 Quality Pipeline

### Stage 1: Static Analysis
- No repository linter is configured in `pyproject.toml`.
- Applied existing code style conventions manually while reviewing the changed runtime, CLI, selector, and test files.

### Stage 2: Type Checking
- No repository type checker is configured in `pyproject.toml`.
- All new and changed Python code keeps explicit type annotations consistent with the surrounding codebase patterns.
- `python -m compileall harnessiq`
  - Result: passed.

### Stage 3: Unit Tests
- `pytest tests/test_agents_base.py tests/test_provider_base_agents.py tests/test_leads_agent.py tests/test_cli_policy_options.py tests/test_cli_runners.py`
  - Result: 62 passed.
- `pytest tests/test_toolset_dynamic_selector.py tests/test_provider_embeddings.py tests/test_interfaces.py tests/test_embedding_integrations.py`
  - Result: 31 passed.

### Stage 4: Integration & Contract Tests
- `python scripts/sync_repo_docs.py`
  - Result: regenerated `README.md`, `artifacts/commands.md`, and `artifacts/file_index.md` to reflect the live CLI/runtime surface.
- `python scripts/sync_repo_docs.py --check`
  - Result: passed after regeneration.
- `pytest`
  - Result: 1797 passed, 4 warnings.

### Stage 5: Smoke & Manual Verification
- Verified that `BaseAgent.build_model_request()` preserves the full static tool surface when `tool_selection.enabled=False` and narrows the request tool list when a selector is injected and enabled.
- Verified prompt/schema alignment in provider-base and leads agents through request-level assertions on the model-facing tool list and rendered prompt content.
- Verified CLI opt-in flow by asserting parsed `--dynamic-tools`, `--dynamic-tool-candidates`, `--dynamic-tool-top-k`, and `--dynamic-tool-embedding-model` values arrive in `runtime_config.tool_selection`.
