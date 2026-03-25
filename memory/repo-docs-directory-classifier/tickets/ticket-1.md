Title: Introduce an extensible top-level directory classifier for generated repo docs

Issue URL: https://github.com/cerredz/HarnessHub/issues/270

Intent:
Reduce maintenance debt in the repository docs generator by replacing the single hardcoded top-level directory map with an explicit classifier pipeline. This makes directory classification easier to extend as the repo grows and prevents new local directories from silently degrading to the generic `other` bucket.

Scope:
- Refactor top-level directory classification inside `scripts/sync_repo_docs.py`.
- Preserve current classifications for already-known tracked directories.
- Add direct regression coverage for classifier behavior, including `.worktrees` and `data`.
- Regenerate generated docs only if the implementation changes outputs in the worktree checkout.

Out of scope:
- No changes to runtime harness, CLI, provider, or tool behavior.
- No broad rewrite of the docs generator’s AST parsing or markdown rendering pipeline.
- No attempt to classify every possible directory name beyond the specific extensibility seam addressed here.

Relevant Files:
- `scripts/sync_repo_docs.py` — replace flat top-level directory fallback logic with an extensible classifier pipeline.
- `tests/test_docs_sync.py` — add regression tests for direct classifier behavior and ensure docs sync still passes.
- `artifacts/file_index.md` — regenerated only if the worktree checkout’s rendered output changes.
- `artifacts/live_inventory.json` — regenerated only if the worktree checkout’s rendered output changes.
- `README.md` — regenerated only if the worktree checkout’s rendered output changes.

Approach:
Use a small classifier-chain design inside the docs generator. Keep exact-name rules for current known directories, then layer explicit strategy functions for local Git worktrees and local data directories before falling back to the default `other` classification. Expose one helper that classifies a single top-level directory entry so tests can validate behavior directly without requiring the directories to exist in the implementation worktree. This keeps the change narrow, readable, and easy to extend when future repo-local directories appear.

Assumptions:
- The current exact-match metadata is the source of truth for already-classified directories and must remain behaviorally unchanged.
- `.worktrees` should be documented as local worktree state rather than left unclassified.
- `data` should be documented as local data/state rather than left unclassified.
- No user clarification is required because the task explicitly authorizes autonomous pattern selection.

Acceptance Criteria:
- [ ] `scripts/sync_repo_docs.py` no longer hardcodes top-level directory classification as a single dict lookup plus inline fallback.
- [ ] The docs generator exposes a reusable helper that classifies one top-level directory entry.
- [ ] Existing exact-name classifications remain unchanged for known directories such as `artifacts`, `docs`, `harnessiq`, `memory`, and `tests`.
- [ ] `.worktrees` resolves to a non-generic classification with a concrete responsibility description.
- [ ] `data` resolves to a non-generic classification with a concrete responsibility description.
- [ ] `tests/test_docs_sync.py` contains direct regression coverage for the classifier behavior.
- [ ] Existing docs-sync verification still passes after the refactor.

Verification Steps:
1. Run targeted docs-sync tests covering the new classifier helper and existing docs-sync behavior.
2. Run the generated-docs sync check.
3. If generated outputs change in the worktree checkout, run the generator and confirm the check passes afterward.
4. Record the executed commands and observed results in the ticket quality artifact.

Dependencies:
- None.

Drift Guard:
This ticket must stay confined to the repository docs generator seam. It must not expand into runtime CLI refactors, manifest changes, or broader repo-doc redesign. The goal is to introduce a maintainable classification pattern and prove it with tests, not to restructure unrelated parts of the generator.
