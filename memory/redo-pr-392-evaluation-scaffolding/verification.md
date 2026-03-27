Verification run on the PR worktree after the rewrite:

- `python -m pytest tests\test_evaluations.py tests\evals\test_minimal_scaffolding.py`
  - Result: `8 passed`
- `python -m pytest tests\test_sdk_package.py -k "top_level_package_exposes_sdk_modules or package_builds_wheel_and_sdist_and_imports_from_wheel"`
  - Result: `2 passed, 4 deselected`
- `python -m pytest tests\evals --eval-category tool_use --model gpt-4o -q`
  - Result: `1 passed, 2 deselected`
- `python scripts\sync_repo_docs.py`
  - Result: regenerated repo docs from live source
- `python scripts\sync_repo_docs.py --check`
  - Result: `Generated docs are in sync.`
