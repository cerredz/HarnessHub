Title: Add the LinkedIn job application agent harness
Intent: Build the concrete `LinkedInJobApplierAgent` on top of the new runtime so the repository contains an actual durable agent harness that matches the user’s formalized LinkedIn design.
Scope:
- Add LinkedIn-specific prompt assembly, memory-file management, and tool definitions.
- Implement harness-owned memory and control-flow tools for the LinkedIn workflow.
- Add tests for LinkedIn defaults, memory persistence, append-only job history semantics, and pause/reset behavior.
- Update repository artifacts to reflect the new package layout.
- Do not implement a real Playwright/MCP browser client inside the repository.
Relevant Files:
- `src/agents/linkedin.py`: LinkedIn-specific memory store, tool catalog, and concrete agent class.
- `src/agents/__init__.py`: export the LinkedIn agent surface.
- `tests/test_linkedin_agent.py`: LinkedIn-specific behavior coverage.
- `artifacts/file_index.md`: document the new `src/agents/` source package.
Approach: Model LinkedIn memory as durable files under a configurable `memory_path`, with append-only JSONL logs for jobs and actions. Build the system prompt from the specification’s identity/goal/input/tool/rule sections and inject the latest parameter state on startup and after resets. Register harness-local tools for action logging, job persistence, job skipping/status updates, memory reads, and pause signaling; treat browser tools as injected runtime collaborators.
Assumptions:
- `update_job_status` should preserve append-only durability by appending a newer record for the same `job_id` instead of mutating prior lines in place.
- The LinkedIn agent should expose the full documented tool catalog, while requiring runtime handlers for browser tools from the caller.
- Saving screenshots to memory can be modeled as an optional injected callback because the repository does not own a browser implementation.
Acceptance Criteria:
- [ ] `LinkedInJobApplierAgent` exists and subclasses or composes the shared base runtime cleanly.
- [ ] The LinkedIn agent manages `job_preferences.md`, `user_profile.md`, `agent_identity.md`, `applied_jobs.jsonl`, and `action_log.jsonl` under a configurable memory directory.
- [ ] LinkedIn prompt assembly matches the documented sections and behavioral rules.
- [ ] Harness-local tools append/read/update durable state correctly, including skipped jobs and recent actions.
- [ ] Tests cover memory-file bootstrap, append-only job status behavior, parameter injection, and pause/reset semantics.
- [ ] `artifacts/file_index.md` reflects the new `src/agents/` package.
Verification Steps:
- Run `python -m unittest tests.test_linkedin_agent`.
- Run `python -m unittest`.
- Smoke-check a temporary memory directory with a fake model to confirm the LinkedIn agent rebuilds its parameter block after a transcript reset.
Dependencies: Ticket 1.
Drift Guard: This ticket must not turn into a browser automation implementation or a provider-specific adapter. The deliverable is a LinkedIn-oriented harness and durable state layer built on the generic runtime.
