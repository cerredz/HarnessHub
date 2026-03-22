Title: Expand the file index preface with agent architecture standards
Intent: Make the repository file index more useful as an onboarding artifact by stating the core architectural standards that govern how agents, tools, providers, memory, and reset-aware autonomy are expected to work in this codebase.
Scope:
- Add a compact standards section at the beginning of `artifacts/file_index.md`.
- Cover the requested topics: agent definition, provider-mediated tool/platform access, per-agent memory, deterministic tool usage against durable state, reset-aware autonomy, and `BaseAgent` inheritance with user-configurable parameters.
- Preserve the existing directory and file inventory below the new standards section.
- Do not refactor unrelated duplication or rewrite the full file index.
Relevant Files:
- `memory/update-file-index-codebase-standards/internalization.md`: Phase 1 repository/task mapping for this documentation update.
- `memory/update-file-index-codebase-standards/clarifications.md`: record that no additional clarification was required.
- `memory/update-file-index-codebase-standards/tickets/ticket-1.md`: implementation ticket for the standards update.
- `memory/update-file-index-codebase-standards/tickets/index.md`: dependency-ordered local ticket index.
- `artifacts/file_index.md`: add the standards preface at the top of the artifact.
Approach: Insert a short "Codebase standards" section immediately after the opening paragraph in `artifacts/file_index.md`. Phrase each point so it reflects the current architecture shown by `BaseAgent`, the concrete memory-backed agents, the provider/tool split, and the existing persisted runtime/custom parameter files. Keep the section concise enough that the rest of the file index remains the primary structural reference.
Assumptions:
- The user wants a documentation update only, not code changes to the runtime.
- The file index should describe the project's intended operating model even if some details are implemented most concretely in the shipped harnesses rather than in `BaseAgent` alone.
- GitHub issue creation is not required for this local documentation task unless explicitly requested later.
Acceptance Criteria:
- [ ] `artifacts/file_index.md` begins with a clear standards section before the directory listings.
- [ ] The new standards language states that agents are defined as harnesses that inherit runtime behavior and interact with tools/provider-mediated third-party platforms.
- [ ] The new standards language states that autonomous agents rely on durable per-agent memory that survives across runs and context resets.
- [ ] The new standards language explains that tools should be used for deterministic checks against durable state when possible, not only as optional model add-ons.
- [ ] The new standards language explains that reset-aware continuity is a first-class design concern for autonomous agents.
- [ ] The new standards language notes that behavior can be configured through agent parameters, including user-supplied parameters where supported.
Verification Steps:
- Review the diff for `artifacts/file_index.md` to confirm the change is scoped to the new preface.
- Manually verify each new standards bullet against `harnessiq/agents/base/agent.py`, `README.md`, and `harnessiq/shared/linkedin.py`.
- Confirm no repository formatter, linter, or type checker is configured for Markdown-only docs in `pyproject.toml`.
Dependencies: None.
Drift Guard: This ticket must not refactor unrelated portions of `artifacts/file_index.md`, must not alter runtime code, and must not claim guarantees that are contradicted by the current architecture. The goal is a precise standards preface, not a broader documentation overhaul.
