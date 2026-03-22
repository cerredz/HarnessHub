# Ticket 4: ExaOutreach CLI Commands and Final Registration

## Title
Add `harnessiq outreach` CLI sub-commands and update artifacts/file_index.md

## Intent
Expose ExaOutreachAgent via the `harnessiq outreach` CLI sub-command (prepare, configure, show, run) matching the LinkedIn CLI pattern. Register the new commands in `cli/main.py`. Update `artifacts/file_index.md` to document all new modules.

## Scope
**Creates:**
- `harnessiq/cli/exa_outreach/__init__.py`
- `harnessiq/cli/exa_outreach/commands.py` — `register_exa_outreach_commands()`
- `tests/test_exa_outreach_cli.py`

**Modifies:**
- `harnessiq/cli/main.py` — register outreach commands
- `artifacts/file_index.md` — add all new modules

**Does NOT touch:**
- Agent harness
- Shared types
- `harnessiq/agents/__init__.py` (already done in Ticket 3)

## Relevant Files
Reference: `harnessiq/cli/linkedin/commands.py` — exact pattern to mirror.

## Approach

### Commands

**`harnessiq outreach prepare`** — Creates or refreshes the outreach agent memory folder.
```
--agent     required  Logical agent name
--memory-root  default="memory/outreach"
```

**`harnessiq outreach configure`** — Writes search query, agent identity, runtime params, additional prompt.
```
--agent          required
--memory-root    default="memory/outreach"
--query-text     inline search query
--query-file     path to query file
--agent-identity-text / --agent-identity-file
--additional-prompt-text / --additional-prompt-file
--runtime-param KEY=VALUE  (max_tokens, reset_threshold)
```

**`harnessiq outreach show`** — Renders current persisted state as JSON.
```
--agent, --memory-root
```

**`harnessiq outreach run`** — Runs the agent from persisted CLI state.
```
--agent          required
--memory-root
--model-factory  required  module:callable returning AgentModel
--exa-credentials-factory   module:callable returning ExaCredentials
--resend-credentials-factory  module:callable returning ResendCredentials
--email-data-factory   module:callable returning list[dict]
--runtime-param  KEY=VALUE  (override max_tokens, reset_threshold for this run only)
--max-cycles     int
```

The `run` handler:
1. Loads `ExaOutreachMemoryStore` and calls `prepare()`
2. Calls each factory
3. Builds `ExaOutreachAgentConfig` (with `FileSystemStorageBackend` defaulting to memory path)
4. Instantiates `ExaOutreachAgent`
5. Calls `agent.run(max_cycles=args.max_cycles)`
6. Prints run summary (leads found, emails sent counts from the run file)
7. Emits JSON result

### SUPPORTED_EXA_OUTREACH_RUNTIME_PARAMETERS
```python
SUPPORTED_EXA_OUTREACH_RUNTIME_PARAMETERS = ("max_tokens", "reset_threshold")
```
With corresponding `normalize_exa_outreach_runtime_parameters()` function.

### artifacts/file_index.md additions
New entries for:
- `harnessiq/shared/exa_outreach.py`
- `harnessiq/agents/exa_outreach/`
- `harnessiq/agents/exa_outreach/prompts/`
- `harnessiq/cli/exa_outreach/`
- `tests/test_exa_outreach_shared.py`
- `tests/test_exa_outreach_agent.py`
- `tests/test_exa_outreach_cli.py`

## Assumptions
- Depends on Tickets 2 and 3.
- Factory pattern for credentials (`--exa-credentials-factory`) mirrors `--model-factory` from LinkedIn CLI.
- `email_data_factory` returns `list[dict]`; CLI converts each to `EmailTemplate.from_dict(d)`.
- Default `--memory-root` is `"memory/outreach"` (parallel to `"memory/linkedin"`).

## Acceptance Criteria
- [ ] `harnessiq outreach --help` prints usage with prepare/configure/show/run sub-commands
- [ ] `harnessiq outreach prepare --agent test-agent` creates `memory/outreach/test-agent/` with expected files
- [ ] `harnessiq outreach configure --agent test-agent --query-text "VPs at SaaS startups"` writes query config and prints JSON summary
- [ ] `harnessiq outreach show --agent test-agent` prints current state as JSON
- [ ] `register_exa_outreach_commands` is called from `cli/main.py`
- [ ] All tests pass: `pytest tests/test_exa_outreach_cli.py -v`
- [ ] `artifacts/file_index.md` documents all new files introduced across tickets 1–4

## Verification Steps
1. `pytest tests/test_exa_outreach_cli.py -v` — all pass
2. `harnessiq outreach --help` — shows sub-commands
3. `harnessiq outreach prepare --agent smoke-test` — creates memory directory and exits 0
4. `harnessiq outreach configure --agent smoke-test --query-text "test query"` — writes and prints JSON
5. `harnessiq outreach show --agent smoke-test` — prints full state

## Dependencies
- Ticket 2 (shared types) and Ticket 3 (agent harness) must be merged.

## Drift Guard
Must not modify the agent harness or shared types. CLI commands must only interact with `ExaOutreachMemoryStore` and `ExaOutreachAgent` via their public APIs. Must not modify the LinkedIn CLI.
