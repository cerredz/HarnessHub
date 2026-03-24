No meaningful ambiguities remain after Phase 1.

Implementation will:

- support both `.env` and `local.env` for CLI run-time bootstrapping,
- keep existing process env vars authoritative,
- wire the bootstrap into both the legacy prospecting run path and the platform-first adapter run path,
- preserve LangSmith alias seeding behavior.
