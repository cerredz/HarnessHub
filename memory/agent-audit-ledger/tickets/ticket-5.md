Title: Add local and webhook-backed sinks for Obsidian, Slack, and Discord

Intent:
Ship the highest-visibility non-database sinks first so users can browse run history locally or receive immediate notifications without extra infrastructure.

Scope:
Implement the Obsidian note sink plus Slack/Discord webhook summary sinks.

Relevant Files:
- `harnessiq/utils/ledger.py`: local and notification sink implementations.
- `harnessiq/providers/output_sinks.py`: shared webhook delivery helper.
- `tests/test_output_sinks.py`: validate sink behavior without external network calls.

Approach:
Keep local file rendering in `utils` and centralize webhook transport in a provider helper so the sink layer stays declarative and the provider layer owns HTTP mechanics.

Assumptions:
- Obsidian writes one Markdown note per run.
- Slack and Discord both use lightweight webhook summary payloads.

Acceptance Criteria:
- [ ] Obsidian sink writes one Markdown note per run with frontmatter plus JSON bodies.
- [ ] Slack sink posts a completion summary through a webhook client.
- [ ] Discord sink posts a completion summary through a webhook client.

Verification Steps:
- Run focused sink tests for file output and webhook client delegation.

Dependencies:
- Ticket 1.

Drift Guard:
Do not add broader wiki/database semantics here. This ticket is only for local note export plus notification webhooks.
