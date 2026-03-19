Title: Add global sink connections and CLI/runtime sink injection

Intent:
Support the three intended sink injection paths: programmatic runtime config, globally configured CLI connections, and per-run CLI sink overrides.

Scope:
Add a persisted global connections store plus CLI wiring that resolves enabled sinks into `AgentRuntimeConfig` for existing run commands.

Relevant Files:
- `harnessiq/utils/ledger.py`: sink connection models and store.
- `harnessiq/cli/main.py`: register top-level ledger/connect commands.
- `harnessiq/cli/ledger/`: add connect/connections/log/export/report commands.
- `harnessiq/cli/linkedin/commands.py`: merge global connections and `--sink` overrides into runtime config.
- `harnessiq/cli/exa_outreach/commands.py`: merge global connections and `--sink` overrides into runtime config.

Approach:
Persist enabled sink definitions in a home-scoped `connections.json`, build sinks lazily at CLI runtime, and keep the harness boundary clean by passing only `AgentRuntimeConfig(output_sinks=...)` into agents.

Assumptions:
- Global sink connections can store raw sink config payloads for now.
- Existing CLI run commands are the primary initial injection points.

Acceptance Criteria:
- [ ] `harnessiq connect <sink>` can persist a global sink connection.
- [ ] `harnessiq connections list|test|remove` manages stored connections.
- [ ] Existing CLI run commands automatically inject enabled global sinks.
- [ ] Existing CLI run commands accept `--sink` for per-run overrides.

Verification Steps:
- Run CLI tests for connect/list/test/remove.
- Run CLI tests for per-run sink injection on an existing agent command.

Dependencies:
- Ticket 1.

Drift Guard:
Do not introduce agent-specific sink logic or move sink configuration into harness code. Injection belongs to the runtime-config and CLI layer only.
