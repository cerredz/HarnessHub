No blocking clarifications required after Phase 1.

Implementation assumptions carried forward:

- Deliver the baseline audit-ledger system that the current codebase can support cleanly now: universal ledger envelope, always-on JSONL sink, concrete agent output extraction, provider metadata stamping, and CLI ledger inspection/export/report.
- Do not implement external sink connection management or remote sink backends in this task.
- Keep `AgentRunResult` backward-compatible and make the ledger strictly additive.
