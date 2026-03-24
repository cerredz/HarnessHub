Title: Remove live inventory from generated repo artifacts

Issue URL:
- https://github.com/cerredz/HarnessHub/issues/266

Intent:
Stop committing and advertising `artifacts/live_inventory.json` so the repository’s generated documentation surface stays high-signal and avoids unnecessary token-heavy artifacts.

Scope:
- Remove `artifacts/live_inventory.json` from the committed generated outputs.
- Update the docs-sync generator so it no longer emits or documents the artifact.
- Add regression coverage that prevents the artifact from re-entering the generated output contract.
- Do not change runtime SDK behavior, harness manifests, provider logic, or non-doc generation workflows.

Relevant Files:
- `scripts/sync_repo_docs.py`: Remove the live inventory artifact from the generated output contract and any README doc-link declarations.
- `README.md`: Regenerated to stop advertising the removed artifact.
- `tests/test_docs_sync.py`: Add regression coverage for the updated generated output set and removal behavior.
- `artifacts/live_inventory.json`: Delete the tracked generated artifact from the repository.

Approach:
Update the repo-doc generator as the single source of truth. The implementation should remove `live_inventory.json` from the output set declared by `expected_outputs()` and from the README repo-doc link list, then regenerate README so the checked-in docs match the new contract. Add focused regression tests in `tests/test_docs_sync.py` that assert the removed artifact is no longer part of the expected outputs and that any legacy copy is treated as stale. This keeps the change bounded to repo-doc generation instead of sprinkling ignore rules or ad hoc deletions elsewhere.

Assumptions:
- `artifacts/live_inventory.json` is only a repository-doc artifact and is not required by runtime code.
- The repository should continue to track the remaining generated repo artifacts.
- The implementation can be validated through the existing docs-sync regression surface without introducing new tooling.

Acceptance Criteria:
- [ ] `artifacts/live_inventory.json` is deleted from the repository.
- [ ] `scripts/sync_repo_docs.py` no longer generates or documents `artifacts/live_inventory.json`.
- [ ] Generated `README.md` no longer lists `artifacts/live_inventory.json` in Repo Docs.
- [ ] Regression tests cover the updated docs-sync output contract so the artifact does not reappear silently.
- [ ] The docs-sync verification command passes with the updated generated artifacts.

Verification Steps:
- Static analysis: No configured linter exists; perform syntax validation on changed Python files.
- Type checking: No configured type checker exists; confirm changed code remains annotated/idiomatic and importable.
- Unit tests: Run `python -m pytest tests/test_docs_sync.py`.
- Integration and contract verification: Run `python scripts/sync_repo_docs.py --check`.
- Smoke/manual verification: Run `python scripts/sync_repo_docs.py` and confirm `README.md` omits the artifact and `artifacts/live_inventory.json` is absent afterward.

Dependencies:
- None.

Drift Guard:
This ticket must not broaden into reworking the entire repo-doc generation pipeline, rewriting unrelated generated artifacts, or changing package/runtime behavior. The only allowed behavioral change is removing the live inventory artifact from the generated/committed docs surface and hardening the generator/tests against its accidental return.
