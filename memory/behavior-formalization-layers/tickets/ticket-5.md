Title: Implement communication behaviors and finalize public behavior surface

Intent:
Complete the design doc by adding the communication/transparency category, wiring full package exports, and regenerating the generated repository artifacts so the new behavior surface is visible in the documented architecture.

Issue URL:
https://github.com/cerredz/HarnessHub/issues/444

Scope:
- Implement the typed communication category base.
- Implement `ProgressReportingBehavior`, `DecisionLoggingBehavior`, `UncertaintySignalingBehavior`.
- Finalize package-level exports for all behavior categories across both the new and legacy-compatible surfaces.
- Add any remaining aggregate behavior tests.
- Regenerate `artifacts/file_index.md` through the repository doc generator.
- Do not revisit earlier category semantics except for necessary follow-up fixes discovered while finalizing exports or docs.

Relevant Files:
- `harnessiq/interfaces/formalization/behaviors/communication/base.py`: `CommunicationRuleSpec` and `BaseCommunicationBehaviorLayer`.
- `harnessiq/interfaces/formalization/behaviors/communication/progress.py`: `ProgressReportingBehavior`.
- `harnessiq/interfaces/formalization/behaviors/communication/decision_log.py`: `DecisionLoggingBehavior`.
- `harnessiq/interfaces/formalization/behaviors/communication/uncertainty.py`: `UncertaintySignalingBehavior`.
- `harnessiq/interfaces/formalization/behaviors/__init__.py`: Final category re-exports.
- `harnessiq/interfaces/formalization/__init__.py`: Final behavior exports.
- `harnessiq/interfaces/formalization.py`: Final compatibility exports.
- `harnessiq/interfaces/__init__.py`: Final top-level interface exports.
- `harnessiq/formalization/__init__.py`: Final legacy-compatible exports.
- `tests/test_formalization_behaviors_communication.py`: Communication behavior tests.
- `tests/test_interfaces.py`: Final export assertions if expanded.
- `artifacts/file_index.md`: Regenerated architecture snapshot.

Approach:
Implement communication behaviors as deterministic blockers that force explicit reporting, decision capture, or uncertainty signaling before the next class of action proceeds. Reuse the existing control-tool family where it already expresses the right semantics, such as `control.emit_decision`, and introduce behavior-owned tools only where the current runtime has no equivalent. Finish by making the export graph coherent across `interfaces`, compatibility modules, and legacy-friendly surfaces, then regenerate the file index so the documented architecture reflects the new package tree.

Assumptions:
- Tickets 1 through 4 have landed the shared behavior runtime and all earlier category implementations.
- Existing control-tool semantics are stable enough to be reused for decision logging and progress-style reporting when appropriate.
- `scripts/sync_repo_docs.py` remains the source of truth for generated repo docs.

Acceptance Criteria:
- [ ] Communication category base and all three concrete communication behaviors exist and are exported.
- [ ] All behavior categories are publicly accessible from both the newer interface surface and legacy-compatible exports.
- [ ] Generated repository docs reflect the new behavior package layout after regeneration.
- [ ] Tests cover communication behavior gating and final export visibility.

Verification Steps:
1. Run targeted static analysis on the communication and export files.
2. Run `pytest tests/test_formalization_behaviors_communication.py tests/test_interfaces.py`.
3. Run `python scripts/sync_repo_docs.py` and verify `artifacts/file_index.md` updates cleanly.
4. Smoke-test imports from `harnessiq.interfaces`, `harnessiq.interfaces.formalization.behaviors`, and `harnessiq.formalization`.

Dependencies:
- Ticket 1.
- Ticket 2.
- Ticket 3.
- Ticket 4.

Drift Guard:
This ticket must not reopen core runtime design questions or broad earlier-category refactors. It should finish the communication category, close export/documentation gaps, and leave only integration fixes that are directly required to ship the full design-doc surface.
