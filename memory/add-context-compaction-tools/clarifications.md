No blocking clarifications were required after Phase 1.

Implementation choices recorded:

- Add the requested compaction behavior to the merged `src/tools/` extension surface instead of waiting on the older unmerged `src/agents` branch.
- Introduce a small explicit agent-context model so "parameter" entries, tool calls, tool results, and summary entries can be manipulated deterministically.
- Expose `log_compaction` through a factory that accepts an injected summarizer callable, because the requested behavior depends on a separate LLM/agent pass.
