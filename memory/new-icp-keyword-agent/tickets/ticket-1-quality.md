Stage 1 — Static Analysis:
- No project linter is configured in this environment. Applied existing repository style manually while implementing the new shared Instagram memory module.

Stage 2 — Type Checking:
- No project type checker is configured in this environment. Added explicit annotations across the new shared dataclasses, protocol, and memory-store methods.

Stage 3 — Unit Tests:
- Verified with:
  - `python -m unittest tests.test_instagram_agent`

Stage 4 — Integration & Contract Tests:
- Verified with:
  - `python -m unittest tests.test_instagram_playwright`

Stage 5 — Smoke & Manual Verification:
- Confirmed the new shared memory contract produces persisted `icp_profiles.json`, `search_history.json`, `lead_database.json`, and `runtime_parameters.json` files in temporary test directories.
- Confirmed canonical persisted emails are deduped and retrievable from the memory store.
