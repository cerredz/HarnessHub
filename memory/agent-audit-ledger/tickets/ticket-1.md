Title: Add universal ledger models and runtime sink dispatch

Intent:
Create the framework-level audit envelope and always-on JSONL persistence so every completed agent run can be recorded durably without changing existing agent call sites.

Scope:
Add the shared/runtime contracts and the default JSONL sink, wire sink dispatch into `BaseAgent.run()`, and preserve existing run semantics.

Relevant Files:
- `harnessiq/shared/agents.py`: extend runtime/result-adjacent shared contracts for ledger support.
- `harnessiq/agents/base/agent.py`: add post-run ledger construction and sink dispatch.
- `harnessiq/utils/`: add the ledger utility module(s) and public exports.
- `tests/test_agents_base.py`: cover sink dispatch, failure swallowing, and default ledger behavior.

Approach:
Introduce a universal `LedgerEntry` dataclass and `OutputSink` protocol, add sink configuration to `AgentRuntimeConfig`, implement an append-only JSONL sink under `utils`, and centralize terminal-result handling in `BaseAgent` so each terminal path flows through the same ledger-dispatch code.

Assumptions:
- The default sink should be active without explicit user configuration.
- The runtime should not convert uncaught exceptions into synthetic `AgentRunResult` values for this ticket.
- The sink layer is additive and must not mutate `AgentRunResult`.

Acceptance Criteria:
- [ ] Every terminal `BaseAgent.run()` path emits a `LedgerEntry` through the configured sinks.
- [ ] A default JSONL sink is applied when no explicit sinks are configured.
- [ ] Sink exceptions are logged/swallowed and do not interrupt later sinks or change the returned `AgentRunResult`.
- [ ] Existing runtime tests remain compatible.

Verification Steps:
- Run focused runtime tests for `BaseAgent`.
- Add and run tests for JSONL append behavior and sink failure swallowing.

Dependencies:
- None.

Drift Guard:
Do not add remote sink backends, connection management, or CLI query/export functionality in this ticket. Keep this ticket limited to the shared runtime contract and local default persistence.
