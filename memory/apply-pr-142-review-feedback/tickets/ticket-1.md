Title: Update the PR #142 branch file index for the arXiv provider

Intent: Apply the review feedback on PR `#142` by bringing the branch-local repository architecture artifact in line with the new arXiv provider files introduced by `issue-139`.

Scope:
- Update `artifacts/file_index.md` to document the added arXiv provider package and its test coverage.
- Write the planning and verification artifacts for this review task under `memory/apply-pr-142-review-feedback/`.
- Do not modify arXiv runtime code or alter unrelated sections of the file index.

Relevant Files:
- `artifacts/file_index.md`: add `harnessiq/providers/arxiv/` and `tests/test_arxiv_provider.py`.
- `memory/apply-pr-142-review-feedback/internalization.md`: Phase 1 analysis for the review task.
- `memory/apply-pr-142-review-feedback/clarifications.md`: note that no further clarifications are required.
- `memory/apply-pr-142-review-feedback/tickets/index.md`: single-ticket index for this task.
- `memory/apply-pr-142-review-feedback/tickets/ticket-1.md`: this ticket document.

Approach:
- Inspect the branch-local `artifacts/file_index.md` format and insert the missing arXiv entries alongside the existing provider and test bullets.
- Keep the patch strictly additive so the review fix remains small and easy to validate.

Assumptions:
- PR `#142` corresponds to local branch `issue-139`, as recorded in `memory/arxiv-provider/tickets/index.md`.
- The user’s instruction to "Adhere to file index" means the branch must document the new provider/test files already present in the PR.
- Network restrictions prevent live GitHub comment retrieval, so the change set must be inferred from local repository evidence.

Acceptance Criteria:
- [ ] `artifacts/file_index.md` includes a provider bullet for `harnessiq/providers/arxiv/`.
- [ ] `artifacts/file_index.md` includes a test bullet for `tests/test_arxiv_provider.py`.
- [ ] No runtime code under `harnessiq/providers/arxiv/` is changed.
- [ ] The diff is limited to the file index and task memory artifacts.

Verification Steps:
1. Review `git diff --stat` to confirm only the file index and review-task memory artifacts changed.
2. Review `git diff -- artifacts/file_index.md` to confirm the inserted bullets are accurate and scoped.
3. Run `python -m pytest tests/test_arxiv_provider.py -q` to confirm the branch still passes its provider test coverage.

Dependencies:
- None.

Drift Guard:
This ticket must not rewrite the broader file index format, must not port unrelated `main` documentation changes into `issue-139`, and must not modify the arXiv provider implementation itself. The goal is a narrow PR-review fix tied to the files already introduced by PR `#142`.
