### 1a: Structural Survey

The repository is a Python 3.11+ SDK packaged from the live `harnessiq/` tree via setuptools in `pyproject.toml`. Runtime code is split by responsibility: `harnessiq/agents/` contains harness implementations, `harnessiq/providers/` wraps external systems, `harnessiq/tools/` exposes deterministic tool surfaces, `harnessiq/shared/` holds common models/constants, `harnessiq/integrations/` adapts model providers, and `harnessiq/cli/` exposes argparse entrypoints. Tests live under `tests/` and are a mix of `pytest`-style function tests and `unittest` packaging smoke tests. Repo docs in `README.md` and `artifacts/*.md` are generated from `scripts/sync_repo_docs.py`, so source-tree changes that alter package shape or descriptions must be reflected there rather than hand-maintained.

PR 392 added a new `harnessiq.evaluations` package and exported it from `harnessiq/__init__.py`. That new package currently uses several layers of abstraction: dataclass models in `harnessiq/evaluations/models.py`, helper factories in `assertions.py`, category builders in `boilerplate.py` plus subpackages, metrics in `metrics.py`, and case/registry abstractions in `registry.py`. The associated tests in `tests/test_evaluations.py` verify those abstractions directly. Packaging smoke tests in `tests/test_sdk_package.py` assert that `harnessiq.evaluations` exists and currently expose `EvaluationContext`.

The repository does not currently define any general pytest marker conventions outside ordinary `pytest.mark.parametrize`, and there is no existing `conftest.py` or pytest plugin wiring for evaluation-specific CLI options. That means targeted eval selection by category/model is net-new behavior and needs explicit pytest integration.

### 1b: Task Cross-Reference

The user request is anchored to the PR 392 review. The review rejects the current framework as overbuilt and instead asks for evaluation scaffolding that looks like plain pytest tests with docstrings, tag/category markers, ideal-trajectory efficiency scoring, and optional LLM-as-a-judge style correctness helpers. Concretely, that maps to the current PR files as follows:

- `harnessiq/evaluations/__init__.py`: must stop exporting the registry/model abstraction surface and instead expose only a minimal pytest-oriented helper surface.
- `harnessiq/evaluations/*.py`: the current `models.py`, `assertions.py`, `registry.py`, `boilerplate.py`, and category boilerplate subpackages are the main overbuilt surface called out by the review and are candidates for deletion or replacement.
- `tests/test_evaluations.py`: must be rewritten from framework-unit tests into minimal helper/plugin tests that prove the requested usage pattern.
- `tests/test_sdk_package.py`: must stop asserting the removed rich API and instead assert the smaller surface that remains public.
- `pyproject.toml` and/or `tests/conftest.py`: likely need minimal pytest integration so `--eval-category` and `--model` work in repo tests without extra boilerplate.
- `scripts/sync_repo_docs.py`, `README.md`, and `artifacts/file_index.md`: must be updated so generated docs describe the lightweight evaluation scaffolding rather than a registry/check-factory system.
- `memory/add-evaluation-layer/*`: belongs to the superseded implementation and should not remain as the planning artifact for the rewritten PR.

Relevant existing runtime data models already live elsewhere in the SDK. For example, `harnessiq/shared/agents.py` exposes `AgentRunResult`, `AgentModelResponse`, and related tool-call structures, while `tests/test_agent_models.py` shows existing `parallel_tool_calls` semantics in model integrations. Those models can inform helper behavior, but the review does not ask for a deep framework around them.

### 1c: Assumption & Risk Inventory

- Assumption: the review intends the `harnessiq.evaluations` package to remain as a small public package, not to be removed entirely. This is supported by the original PR goal and the packaging tests expecting the module to exist.
- Assumption: the desired API should prefer generic object/mapping introspection over new Harnessiq-specific eval dataclasses, because the review explicitly asks for “very simple functions with docstrings and strings in general.”
- Assumption: category selection and model injection should be implemented through pytest-native hooks/options, because the review shows `@pytest.mark.eval_category(...)` and `pytest ... --eval-category ... --model ...`.
- Risk: pytest CLI options will not be recognized unless the plugin is loaded automatically in repository test runs. The implementation needs explicit plugin wiring.
- Risk: removing the current abstraction surface will break the existing package smoke tests unless they are updated to assert the new surface.
- Risk: generated docs will drift if file descriptions still reference deleted `models.py`/`registry.py` files or the old evaluation architecture.
- Risk: the user asked to redo an existing PR branch, while the current checkout is on an unrelated dirty branch. All implementation work must stay isolated in the PR worktree so unrelated local changes are untouched.

Phase 1 complete.
