Title: Document and verify the end-to-end GCP workflow
Issue URL: https://github.com/cerredz/HarnessHub/issues/303
PR URL: https://github.com/cerredz/HarnessHub/pull/360
Status: implemented, awaiting merge into `main`

Intent:
Make the new GCP support operable by other engineers and lock in its behavior with end-to-end coverage. Without this ticket, the feature set would exist but remain difficult to adopt and easy to regress.

Scope:
Add focused documentation for the GCP deployment flow, extend test coverage across the CLI and runtime path, and update any generated repo docs that should reflect the new top-level command family or provider package. This ticket should not introduce new runtime features beyond what earlier tickets already define.

Relevant Files:
- `docs/gcloud.md`: Add operator-facing documentation for init, credential sync, deployment, scheduling, logs, and memory sync behavior.
- `README.md`: Add a short entry point for the new GCP support.
- `tests/test_gcloud_cli.py`: Extend CLI coverage to the end-to-end command surface as needed.
- `tests/test_gcloud_runtime.py`: Extend runtime coverage to the documented flow as needed.
- `artifacts/commands.md`: Update generated command docs if the generator output changes.
- `artifacts/file_index.md`: Update generated architecture docs if the generator output changes.

Approach:
Document the implemented behavior rather than restating the design doc verbatim. Keep docs aligned with the repository's actual argparse and JSON conventions, call out the credential-binding reuse explicitly, and describe the GCS-backed memory sync approach chosen to fit the live harness architecture. If generated artifacts need updating, rerun the repo's doc-sync script rather than hand-editing the generated outputs.

Assumptions:
- A dedicated `docs/gcloud.md` page is the right place for operational instructions.
- Generated docs in `artifacts/` should only be updated through the existing repo tooling.
- By the time this ticket starts, the provider layer, CLI, deploy spec derivation, and runtime wrapper all exist.

Acceptance Criteria:
- [x] The repository contains focused documentation for the GCP deployment workflow.
- [x] The README points readers to the new GCP support.
- [x] End-to-end CLI and runtime tests cover the main deployment flow and the memory-sync path.
- [x] Any generated docs affected by the new command family or provider package have been regenerated instead of hand-edited.

Verification Steps:
- Static analysis: No configured linter; manually review docs for command accuracy and code fences for validity.
- Type checking: No configured type checker; rely on the earlier tickets' typed code plus test execution.
- Unit tests: Run the relevant GCP CLI and runtime test modules.
- Integration and contract tests: Exercise the end-to-end mocked deployment path through the CLI and runtime wrapper.
- Smoke and manual verification: Follow the documented flow locally with dry-run settings and confirm the documented outputs match reality.

Dependencies:
Ticket 15.

Drift Guard:
Do not add new deployment features in this ticket. The work here is documentation, regression coverage, and generated-artifact alignment for the features already implemented.
