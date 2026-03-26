## Self-Critique Findings

1. The initial implementation removed `artifacts/live_inventory.json` from the generated output contract, but it did not actively clean up or reject stale local copies. That left a path for the artifact to linger in old checkouts and be recommitted later.
2. Removing the JSON renderer left an unused `json` import behind in `scripts/sync_repo_docs.py`.

## Improvements Applied

- Added `LEGACY_OUTPUTS` to `scripts/sync_repo_docs.py` so `write_outputs()` deletes `artifacts/live_inventory.json` if it is present and `check_outputs()` flags it as drift if it reappears.
- Removed the unused `json` import after deleting the inventory renderer.
- Added regression tests covering both stale-artifact detection and stale-artifact cleanup.

## Post-Critique Verification

Commands rerun after the refinement:

```text
python -m py_compile scripts/sync_repo_docs.py tests/test_docs_sync.py
python -m pytest tests/test_docs_sync.py
python scripts/sync_repo_docs.py --check
python scripts/sync_repo_docs.py
```

Observed results:
- Syntax validation passed with no output.
- `python -m pytest tests/test_docs_sync.py` passed: `8 passed in 17.19s`.
- `python scripts/sync_repo_docs.py --check` reported `Generated docs are in sync.`
- `python scripts/sync_repo_docs.py` regenerated docs without recreating `artifacts/live_inventory.json`.
