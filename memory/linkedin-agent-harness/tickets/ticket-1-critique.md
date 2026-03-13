## Post-Critique Changes

1. The first reset heuristic would clear context whenever the full request exceeded the threshold, even if the durable parameter block alone was already above the limit.
- Risk: the agent could thrash on repeated no-op resets.
- Improvement made: tightened the reset rule in `src/agents/base.py` so resets happen only when clearing the rolling transcript would actually reduce the request below the configured budget.

2. The initial committed runtime depended on unrelated local context-compaction modules that were not part of the LinkedIn harness change.
- Risk: the branch would fail to import on a clean checkout and the PR would silently include the wrong architectural dependency.
- Improvement made: removed the unrelated dependency chain and kept the runtime self-contained while preserving explicit tool-call and tool-result transcript entries.
