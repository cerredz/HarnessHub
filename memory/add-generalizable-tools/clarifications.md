No blocking clarifications were required after Phase 1.

Implementation choices recorded:

- Treat the request as a `src/tools/` expansion, not as provider-specific tool payload work.
- Favor a compact, composable tool suite over domain-specific tools so the additions remain useful across research, scraping, triage, workflow, and planning agents.
- Include one general control-flow tool (`control.pause_for_human`) because the existing agent runtime already supports structured pause signals and that behavior is broadly useful.
