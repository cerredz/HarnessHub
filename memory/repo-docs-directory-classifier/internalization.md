### 1a: Structural Survey

- The repository is a Python 3.11+ SDK defined by [pyproject.toml](C:\Users\422mi\HarnessHub\pyproject.toml), with runtime source under `harnessiq/`, repo tooling under `scripts/`, generated artifacts under `artifacts/`, architecture notes under `docs/`, and broad unittest coverage under `tests/`.
- The generated repository docs flow through `scripts/sync_repo_docs.py`, which parses the live source tree and rewrites `README.md`, `artifacts/commands.md`, `artifacts/file_index.md`, and `artifacts/live_inventory.json`.
- The live runtime architecture is already deliberately layered: harness manifests in `harnessiq/shared/`, CLI entrypoints in `harnessiq/cli/`, provider integrations in `harnessiq/providers/`, tool surfaces in `harnessiq/tools/`, and shared utility infrastructure in `harnessiq/utils/`.
- Testing is primarily regression-oriented `unittest` plus some `pytest`-compatible modules. `tests/test_docs_sync.py` is the existing guardrail for docs-generator behavior.
- Current repo conventions favor small helper functions, AST-backed static analysis for repo docs, JSON-safe outputs for CLI surfaces, and deterministic generated artifacts.
- The dirty root checkout is not a safe implementation surface: `git status` shows many unrelated modified and untracked files, and the root branch is behind `origin/main`. Worktree isolation is required to avoid clobbering user work.
- One visible inconsistency in the generated file index from the dirty root is that `.worktrees/` and `data/` fall through to the default `"other"` classification, which means the docs generator currently hardcodes only exact-name matches and has no extensible mechanism for classifying new local directories.

### 1b: Task Cross-Reference

- User intent: continuously inject sound design patterns where they reduce tech debt and make future changes easier. In a bounded single invocation, the most defensible interpretation is to complete one full issue-to-PR improvement loop for the highest-value, low-blast-radius opportunity found during internalization.
- Best candidate seam: `scripts/sync_repo_docs.py`.
  - It currently owns top-level directory classification through a flat `TOP_LEVEL_DIRECTORY_DESCRIPTIONS` mapping plus a hardcoded fallback.
  - That makes new local directories invisible until someone edits the dict directly, which is a maintenance smell in a script whose job is to reflect live repository shape.
- Supporting verification surface: `tests/test_docs_sync.py`.
  - Existing coverage already imports the sync script module and validates generated outputs.
  - This is the right place to add classifier-specific regression tests without touching runtime SDK code.
- Generated-output surface:
  - If the implementation changes rendered output in the worktree checkout, `README.md` and/or `artifacts/file_index.md` may need regeneration.
  - If the implementation only improves classification for directories absent in the worktree checkout, generated outputs may remain unchanged while behavior is still verified by direct classifier tests.
- GitHub workflow surface:
  - Create one issue from a ticket document.
  - Implement in a fresh worktree from `origin/main`.
  - Push a branch and open a PR targeting `main`.

### 1c: Assumption & Risk Inventory

- Assumption: the user's request to "keep repeating this process" means to complete one full, high-quality improvement cycle now rather than attempt an unbounded infinite loop inside one session.
- Assumption: a design-pattern improvement in repo tooling counts as valid tech-debt cleanup because it improves maintainability without inventing unnecessary runtime abstractions.
- Assumption: the correct pattern here is a classifier chain / strategy list for top-level directory metadata, not a broader rewrite of the docs generator.
- Risk: the dirty root checkout contains unrelated user work. Mitigation: perform implementation only inside a new worktree created from fetched `origin/main`.
- Risk: generated outputs in the implementation worktree may differ from the dirty root because the worktree has a different top-level directory shape. Mitigation: verify behavior primarily through tests and only regenerate tracked artifacts if the worktree’s expected outputs actually change.
- Risk: the `implementation` GitHub label may not exist. Mitigation: inspect labels and create it if missing before creating the issue.
- Risk: push or PR creation could fail because of remote policy or auth drift. Mitigation: use the authenticated `gh` CLI and surface any repository-level failure explicitly if encountered.

Phase 1 complete
