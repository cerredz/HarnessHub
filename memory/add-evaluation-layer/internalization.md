## Phase 1

### 1a: Structural Survey

- `harnessiq/` is the only authoritative runtime package. The package is organized by role: agents orchestrate workflows, tools expose deterministic callable surfaces, providers wrap external systems, shared modules hold constants/models, toolset manages lookup/registration, and utils own cross-cutting runtime support.
- `harnessiq/tools/` is the closest existing architectural analogue for the requested evaluation layer. Tool families are grouped into subpackages, exported through package `__init__.py` modules, and validated with focused tests under `tests/`.
- A narrow evaluation-related surface already exists in `harnessiq/tools/eval/`. It is tool-facing and currently limited to the prospecting-oriented `eval.evaluate_company` tool definition. It is not a reusable repo-wide evaluation framework.
- `harnessiq/__init__.py` exposes top-level SDK modules lazily through `_EXPORTED_MODULES`. New first-class package surfaces must be added there if they should be importable as `harnessiq.<module>`.
- `tests/` mixes `unittest` and `pytest`, but the suite already supports `pytest` directly via `pyproject.toml`. Focused behavior tests are the standard pattern for new infrastructure surfaces.
- `scripts/sync_repo_docs.py` is the source of truth for generated repo docs. `artifacts/file_index.md` is generated, not hand-maintained, and package layout / key file descriptions are mostly static lists inside that script.
- The working tree is already dirty in unrelated `memory/` artifacts and on branch `issue-348-orchestrator-master-prompt`; those existing changes must be preserved.

### 1b: Task Cross-Reference

- Requested new runtime surface: `harnessiq/evaluations/` as a net-new first-class package under the live SDK tree.
- Existing adjacent code:
  - `harnessiq/tools/eval/` shows current naming overlap with “eval” but serves a different concern: agent-callable evaluation tooling rather than repository evaluation scaffolding.
  - `harnessiq/shared/tools.py` and the general tool registry patterns provide the existing “tooling layer” conventions the new evaluation scaffolding should align with conceptually.
  - `tests/test_sdk_package.py` verifies top-level package exposure and packaging smoke behavior, so adding a new exported package likely requires test updates.
  - `scripts/sync_repo_docs.py` and generated `artifacts/file_index.md` must be updated so the file index reflects the new evaluation layer.
- Requested functional scope:
  - Create an evaluation architecture that is easy to extend.
  - Separate evaluations by subfolder according to what they evaluate.
  - Add boilerplate and very basic general-purpose pytest-oriented evaluation helpers, around 10-15 total.
  - Avoid building a full real evaluation suite now; focus on scaffolding and simple baseline helpers.
- Likely touched files:
  - `harnessiq/__init__.py`
  - new files under `harnessiq/evaluations/`
  - new tests under `tests/`
  - `scripts/sync_repo_docs.py`
  - generated `artifacts/file_index.md` and any other generated outputs changed by the docs sync script

### 1c: Assumption & Risk Inventory

- Assumption: “pi test evaluation functions” means `pytest`-compatible evaluation helpers. This is consistent with the article and the repo’s configured test runner.
- Assumption: the user wants reusable primitives and sample category structure, not a heavyweight runner tied to LangSmith, CI tags, or live model execution yet.
- Assumption: the evaluation layer should be package-level infrastructure (`harnessiq/evaluations`) rather than a `tests/evals/` suite, because the request explicitly names `harnessiq/evaluations`.
- Risk: naming collision or conceptual confusion with the existing `harnessiq.tools.eval` family. The new package should clearly distinguish “evaluation scaffolding” from “agent-callable eval tools.”
- Risk: generated docs will drift unless `scripts/sync_repo_docs.py` is updated and rerun.
- Risk: top-level package exposure and packaging smoke tests may fail if the new package is not exported consistently.
- Risk: the `github-software-engineer` skill prescribes GitHub issue creation and worktree steps, but the repo is already mid-flight on an existing feature branch with unrelated local artifacts. Implementation should avoid disturbing those existing changes.

Phase 1 complete.
