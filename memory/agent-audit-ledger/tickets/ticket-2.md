Title: Declare concrete agent outputs and provider-stamped ledger metadata

Intent:
Make the ledger useful across built-in agents by ensuring the universal envelope contains meaningful, agent-specific structured outputs plus normalized provider/model metadata.

Scope:
Add overridable output/tag/metadata hooks to the agent runtime and implement them for the current built-in agents.

Relevant Files:
- `harnessiq/agents/base/agent.py`: add overridable ledger hook methods.
- `harnessiq/agents/linkedin/agent.py`: emit applied-job output records and LinkedIn tags.
- `harnessiq/agents/exa_outreach/agent.py`: emit run/log summary outputs and outreach tags.
- `harnessiq/agents/knowt/agent.py`: emit generated asset outputs and Knowt tags.
- `harnessiq/agents/email/agent.py`: define default/base email ledger hooks where appropriate.
- `harnessiq/providers/`: add provider metadata extraction helper(s).
- Agent-specific tests under `tests/`: assert ledger outputs/tags/metadata.

Approach:
Expose narrow `BaseAgent` hook methods for building `outputs`, `tags`, and extra metadata, then override only where each concrete harness already has authoritative durable state. Use a provider helper to extract best-effort provider/model identity from model adapters without coupling `BaseAgent` to specific providers.

Assumptions:
- Built-in agents should produce concrete outputs immediately; downstream custom agents can inherit envelope-only behavior until they opt in.
- Provider metadata is best-effort and may be partial when models do not expose provider/model names.

Acceptance Criteria:
- [ ] LinkedIn runs emit structured application outputs from durable memory.
- [ ] Exa Outreach runs emit structured lead/email/run outputs without replacing its existing run storage.
- [ ] Knowt runs emit structured content/video outputs from durable memory.
- [ ] Ledger metadata includes stable framework fields plus best-effort provider/model identity.

Verification Steps:
- Run focused agent tests for LinkedIn, Exa Outreach, Knowt, and Email harnesses.
- Add new tests that inspect emitted ledger entries for each built-in agent.

Dependencies:
- Ticket 1.

Drift Guard:
Do not redesign the concrete agents’ existing memory stores or replace their current persistence patterns. The ledger reads from those sources and adds a framework envelope on top.
