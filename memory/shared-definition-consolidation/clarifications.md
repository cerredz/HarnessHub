Phase 2 outcome:

No blocking clarifications remain after Phase 1.

Rationale:
- `artifacts/file_index.md` already answers the folder-placement question: `harnessiq/shared/` is the central home for shared types, configs, and constants.
- The current codebase already establishes the intended pattern through `shared/linkedin.py`, `shared/knowt.py`, `shared/exa_outreach.py`, `shared/providers.py`, and `shared/tools.py`.
- The remaining ambiguity is about exact granularity on the provider side; the safest interpretation is to move definition-only constants/configs/types into shared modules while leaving behavioral request/client logic where it is.

Implementation implication:
- Proceed without additional user questions.
- Preserve current public exports while shifting the source of truth to `harnessiq/shared/*`.
