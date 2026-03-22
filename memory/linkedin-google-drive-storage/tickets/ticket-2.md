Title: Add deterministic LinkedIn application persistence, duplicate guard, and Google Drive sync
Issue URL: https://github.com/cerredz/HarnessHub/issues/147

Intent: Make successful LinkedIn applications produce one aligned local and remote record, while preventing duplicate applications through explicit deterministic checks against durable agent memory.

Scope:
- Expand the LinkedIn persisted application payload so local memory can store the richer job details required by the task.
- Add an internal `already_applied` tool that checks durable LinkedIn memory and returns a context-safe decision payload.
- Add optional Google Drive persistence to the successful-application path, defaulting to disabled.
- Keep the deterministic write trigger at the LinkedIn agent’s successful-application tool handler.
- Do not add user-facing CLI flags or docs in this ticket except for minimal runtime plumbing that is inseparable from the agent implementation.

Relevant Files:
- `harnessiq/shared/linkedin.py`: extend runtime parameter constants and application record/data models for richer job metadata and Drive-related runtime controls.
- `harnessiq/agents/linkedin/agent.py`: add the duplicate-check tool, enrich the application persistence flow, and integrate optional Drive sync inside the deterministic success handler.
- `tests/test_linkedin_agent.py`: add coverage for richer record persistence, duplicate detection, and optional Drive sync behavior using a fake client/store.

Approach:
- Keep local memory as the system of record and make Google Drive a synchronous mirror when enabled.
- Introduce a richer canonical application record or paired structured artifact that can serialize the requested fields consistently to both local disk and Drive `job.json`.
- Add an explicit `linkedin.already_applied` tool so the model can deterministically consult memory before applying rather than inferring from prompt text alone.
- Ensure duplicate checks are keyed by stable job identity and that Drive folder naming is deterministic from `company + title + job_id`.

Assumptions:
- The existing `linkedin.append_company` handler is the correct deterministic “successful application committed” hook.
- The browser/model will provide the richer job fields at the time it records a successful application.
- A Drive failure should be surfaced clearly rather than silently ignored, but the exact local/remote failure semantics can be implemented without violating the deterministic contract.
- Duplicate detection should rely on local durable memory, not live LinkedIn state.

Acceptance Criteria:
- [ ] The LinkedIn agent exposes an `already_applied` internal tool that deterministically reports whether a job is already present in durable memory.
- [ ] The LinkedIn successful-application persistence path stores aligned rich job/application metadata locally.
- [ ] When `save_to_google_drive` is enabled and Google Drive credentials/client are available, the successful-application path creates or reuses a stable Drive folder and upserts a canonical `job.json` file.
- [ ] The agent’s runtime parameter surface includes `save_to_google_drive` with a default of `false`.
- [ ] Automated tests cover duplicate detection, rich local persistence, and enabled/disabled Drive-sync behavior.

Verification Steps:
- Static analysis: manually review LinkedIn agent changes for side-effect ordering, deterministic naming, and failure-path clarity.
- Type checking: no configured checker; validate new signatures and runtime-parameter coercion through tests and import-time execution.
- Unit tests: run `python -m pytest tests/test_linkedin_agent.py`.
- Integration and contract tests: run the broader agent/package tests that exercise LinkedIn exports and runtime parameter loading.
- Smoke/manual verification: in a temp memory folder, simulate one successful application, confirm the local record is written, call the duplicate-check tool for the same job, and verify it reports the job as already applied.

Dependencies:
- Ticket 1.

Drift Guard: This ticket must not introduce a new general-purpose storage subsystem, background synchronization worker, or interactive Google auth flow. It is limited to deterministic LinkedIn memory semantics and optional synchronous Drive mirroring.
