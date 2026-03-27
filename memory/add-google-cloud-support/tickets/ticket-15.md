Title: Add a cloud runtime wrapper and GCS-backed memory sync
Issue URL: https://github.com/cerredz/HarnessHub/issues/302
PR URL: https://github.com/cerredz/HarnessHub/pull/347
Status: implemented, awaiting merge into `main`

Intent:
Close the gap between "a job can be deployed" and "a harness can run repeatedly in Cloud Run with continuity." This ticket introduces the remote runtime path that can execute any manifest-backed harness and synchronize its durable memory/profile state with GCS.

Scope:
Add the runtime wrapper and memory-sync support needed for deployed Cloud Run jobs. Because the live codebase stores rich memory directories rather than a single generic `memory.json`, this ticket should adapt the design doc to synchronize the harness memory folder and profile state in a codebase-compatible way.

Relevant Files:
- `harnessiq/providers/gcloud/runtime.py`: Add the generic cloud runtime wrapper that resolves config and invokes the appropriate harness run path.
- `harnessiq/providers/gcloud/storage/cloud_storage.py`: Extend storage support as needed for directory/profile sync helpers.
- `tests/test_gcloud_runtime.py`: Verify runtime-wrapper command resolution and GCS sync behavior with fakes.

Approach:
Use the manifest-driven deploy spec from Ticket 14 to resolve the remote run. Before the harness starts, sync the relevant memory/profile state from GCS into the local working directory; after the run, sync updated state back to GCS. This adapts the design doc's memory-persistence goal to the actual repository architecture, which persists many files per harness rather than one universal memory document.

Assumptions:
- Folder/profile synchronization is a better fit for this codebase than forcing all harnesses into a single `memory.json` abstraction.
- The Cloud Run container can execute a generic HarnessIQ runtime wrapper rather than requiring one container entrypoint per harness.
- Some harnesses may still require later refinement for browser-session or external-artifact handling, but the generic sync path should cover the common durable-memory contract.

Acceptance Criteria:
- [x] A generic cloud runtime wrapper can resolve a stored GCP deploy config and invoke the correct harness run path.
- [x] Harness profile and durable memory state can be synced from GCS before execution and back to GCS after execution.
- [x] The runtime wrapper is generic across built-in manifests rather than hard-coded to one harness.
- [x] Tests cover sync-in, sync-out, and failure-handling behavior without live GCP access.

Verification Steps:
- Static analysis: No configured linter; manually review filesystem and subprocess paths for safety and clarity.
- Type checking: No configured type checker; keep runtime-wrapper and sync helper APIs explicitly annotated.
- Unit tests: Run `pytest tests/test_gcloud_runtime.py`.
- Integration and contract tests: Mock storage provider behavior and harness invocation paths to validate end-to-end control flow.
- Smoke and manual verification: Run the wrapper locally against a fake config and fake storage provider to confirm sync ordering.

Dependencies:
Ticket 14.

Drift Guard:
Do not spread cloud-specific branching through individual harness implementations unless a generic wrapper proves insufficient. This ticket should prefer one shared remote execution path and one shared memory-sync abstraction.
