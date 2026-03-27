Critique review focused on whether the Exa Outreach extraction preserved the CLI contract without leaving awkward side effects or hidden coupling in the runner path.

Improvements applied:
- Moved the Exa Outreach delivery-factory validation ahead of environment seeding so invalid non-`--search-only` invocations fail before the runner mutates process environment from local `.env` state.
- Re-ran the Exa Outreach compile step, the focused builder/runner/CLI pytest suite, and the manual smoke check after the ordering fix to confirm the command contract and run-summary behavior remained intact.

The resulting runner now fails faster on invalid arguments while keeping the CLI surface, payloads, and summary output unchanged.
