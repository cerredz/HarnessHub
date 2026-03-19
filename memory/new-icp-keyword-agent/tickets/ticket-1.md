Title: Add Instagram discovery memory models and persistence

Issue URL:
Blocked in local environment. `gh` cannot reach GitHub from this sandbox.

Intent:
Define a durable, explicit memory contract for the new Instagram keyword-discovery agent so ICP inputs, recent searches, search results, and canonical lead/email records survive across runs and can be re-injected into the context window deterministically.

Scope:
- Create a new shared module for the Instagram discovery domain.
- Define persisted filenames, dataclasses, and memory-store helpers for ICPs, search history, and leads/emails.
- Define canonical read/write/query helpers that the agent and CLI can share.
- Keep persistence additive; do not refactor existing agent memory stores.

Relevant Files:
- `harnessiq/shared/instagram.py`: new shared dataclasses, filenames, runtime normalization, and memory-store implementation.
- `harnessiq/utils/run_storage.py`: reuse only; no changes expected unless a narrow shared helper is required.
- `tests/test_instagram_agent.py`: coverage for persistence behavior and retrieval semantics.

Approach:
Follow the established `shared/exa_outreach.py` and `shared/linkedin.py` pattern: define a small memory-store abstraction that owns the on-disk contract, keep files human-readable JSON/text, and provide canonical query helpers such as `read_icp_profiles()`, `append_search()`, `append_leads()`, and `get_emails()`. The canonical lead/email JSON file should support dedupe plus provenance fields such as source keyword and source URL.

Assumptions:
- ICP descriptions are stored as a list of strings.
- Recent searches should be bounded in the context window even if the underlying history file stores all searches.
- Canonical email retrieval should operate over persisted memory, not only per-run files.

Acceptance Criteria:
- [ ] A new shared Instagram memory module exists with typed dataclasses and a memory-store abstraction.
- [ ] The memory store creates and reads default files without requiring pre-existing data.
- [ ] ICP descriptions, search history, and leads/emails persist in JSON files under the agent memory directory.
- [ ] Canonical helper methods return persisted emails across runs and dedupe duplicates deterministically.
- [ ] Tests cover default initialization, append/read flows, and email retrieval behavior.

Verification Steps:
- Run the Instagram agent unit tests that cover the shared memory contract.
- Confirm newly created memory files are written under a temporary directory during tests.
- Manually inspect a generated leads/emails JSON payload shape in test assertions if needed.

Dependencies:
- None.

Drift Guard:
This ticket must not implement the full agent loop, CLI commands, or Playwright browser automation. Its responsibility ends at defining durable state and the read/write/query contract that later tickets consume.
