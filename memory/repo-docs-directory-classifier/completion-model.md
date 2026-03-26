# Completion Model

1. `memory/repo-docs-directory-classifier/` contains the planning and verification artifacts for this cycle.
2. Phase 1 internalization documents the repository structure, the task mapping, and the implementation risks.
3. No unresolved ambiguity remains that would require user input; the chosen interpretation is recorded explicitly.
4. A ticket exists with precise scope, acceptance criteria, drift guard, and verification steps for one concrete improvement.
5. A GitHub issue exists for that ticket and its URL is written back into the local ticket artifacts.
6. Implementation occurs in a fresh worktree branched from current `origin/main`, without mutating the dirty root checkout.
7. `scripts/sync_repo_docs.py` replaces the single flat top-level directory fallback with an extensible classifier pattern that keeps existing known-directory behavior intact.
8. The classifier covers current local repo cases that fall through today, specifically `.worktrees` and `data`.
9. Regression tests exercise the classifier behavior directly and existing docs-sync coverage still passes.
10. The quality pipeline results are written to a ticket quality artifact after passing execution in the implementation worktree.
11. A post-implementation critique is recorded, improvements from that critique are implemented, and the quality pipeline is re-run.
12. The work is committed, pushed, and a PR targeting `main` is created and recorded.
13. The temporary implementation issue is deleted and the worktree is cleaned up after PR creation.
