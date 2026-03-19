Stage 1 — Static Analysis:
- No configured linter in this environment. Reviewed CLI wiring, README changes, and package exports manually.

Stage 2 — Type Checking:
- No configured type checker in this environment. Added annotations to the new CLI command module and retained existing parser/factory patterns.

Stage 3 — Unit Tests:
- Verified with:
  - `python -m unittest tests.test_instagram_cli`
  - `python -m unittest tests.test_sdk_package`

Stage 4 — Integration & Contract Tests:
- Verified with:
  - `python -m unittest tests.test_agents_base tests.test_linkedin_agent tests.test_linkedin_cli tests.test_sdk_package`

Stage 5 — Smoke & Manual Verification:
- Confirmed the root CLI now exposes `instagram` and `instagram get-emails`.
- Confirmed package smoke tests still pass with the new agent exported through `harnessiq.agents`.
- Confirmed README and `artifacts/file_index.md` describe the new agent/integration surface.
