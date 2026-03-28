## Issue 390 Self-Critique

### Finding
- The first documentation pass added the dedicated guide and generator-backed doc links, but discoverability in the generated `README.md` was still too passive because the feature only appeared in the Repo Docs list.

### Improvement Applied
- Updated `scripts/sync_repo_docs.py` so the generated `README.md` now includes a short `## Dynamic Tool Selection` section near the top-level getting-started content.
- Regenerated the affected repo docs so the high-signal README view now points readers to the dedicated guide before they reach the longer reference sections.

### Regression Check
- Re-ran:
  - `python scripts/sync_repo_docs.py --check`
  - `pytest tests/test_docs_sync.py`
- Result: both commands passed after the refinement.
