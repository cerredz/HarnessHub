Title: Add managed LinkedIn agent memory artifacts for CLI-driven configuration
Issue URL: Not created; `gh` is installed but unauthenticated in this environment.

Intent: Establish a durable, agent-scoped storage contract for LinkedIn CLI usage so the SDK can persist typed runtime parameters, arbitrary user metadata, free-form prompt data, and copied user files in one managed memory folder.

Scope:
- Extend the LinkedIn shared definitions and memory-store behavior to support CLI-managed configuration artifacts.
- Preserve the existing memory files and backward compatibility for current SDK consumers.
- Add persistence helpers for copied user artifacts plus metadata that preserves original source paths.
- Do not add any command-line parsing or console entrypoints in this ticket.

Relevant Files:
- `harnessiq/shared/linkedin.py`: define new filename constants and any new dataclasses or typed config helpers for CLI-managed LinkedIn memory.
- `harnessiq/agents/linkedin.py`: extend `LinkedInMemoryStore` and `LinkedInJobApplierAgent` to prepare, read, and expose the new durable inputs.
- `tests/test_linkedin_agent.py`: cover managed file ingestion, new memory artifacts, and parameter-section behavior.

Approach:
- Keep the current file-based memory model and expand it with a small number of explicit artifacts rather than introducing a database or opaque blob store.
- Add a dedicated managed artifacts directory inside each LinkedIn memory folder so uploaded files are copied into stable agent-owned storage.
- Persist agent-aligned runtime params separately from arbitrary user-defined key/value metadata and free-form prompt content so each concern remains readable and testable.
- Load the new persisted inputs into the LinkedIn agent through additional parameter sections rather than changing the existing system-prompt contract more than necessary.

Assumptions:
- Each LinkedIn CLI target corresponds to one memory folder on disk.
- Existing files such as `job_preferences.md` and `user_profile.md` remain authoritative and should still be generated.
- Arbitrary key/value metadata and free-form prompt content should be readable by the agent at run time through the existing parameter-section mechanism.
- Managed artifact copying should preserve the original filename or a safely normalized equivalent while recording the source path.

Acceptance Criteria:
- [ ] `LinkedInMemoryStore.prepare()` bootstraps any new CLI-managed files and directories required by the LinkedIn CLI flow.
- [ ] The LinkedIn memory model can copy a user-provided file into managed storage and persist metadata that includes the source path and managed path.
- [ ] The LinkedIn agent can load typed runtime params, arbitrary key/value metadata, and free-form prompt data from the managed memory folder.
- [ ] Existing LinkedIn memory bootstrapping behavior remains backward compatible.
- [ ] Automated tests cover the new storage and parameter-loading behavior.

Verification Steps:
- Static analysis: manually review changed files for naming, path handling, and exception consistency because no configured linter is present.
- Type checking: no configured checker; validate dataclass, protocol, and method signatures through tests and import-time execution.
- Unit tests: run `python -m unittest tests.test_linkedin_agent`.
- Integration and contract tests: run the broader agent/package tests that exercise LinkedIn exports and packaging expectations.
- Smoke/manual verification: create a temporary LinkedIn memory folder, prepare it, ingest a sample file, and confirm the copied artifact plus metadata files exist and load cleanly.

Dependencies: None.

Drift Guard: This ticket must not introduce CLI argument parsing, console scripts, or docs-only changes. Its sole job is to make the LinkedIn memory layer capable of supporting the CLI contract cleanly and durably.
