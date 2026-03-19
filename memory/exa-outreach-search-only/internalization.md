### 1a: Structural Survey

Repository shape relevant to this task:

- `artifacts/file_index.md` is the architectural source-of-truth for repository boundaries and standards. It confirms that agents are harnesses built on `BaseAgent`, that durable memory is expected, that tools should remain provider-backed and deterministic where possible, and that output sinks are post-run exports injected through runtime config.
- `harnessiq/agents/` contains the shared runtime and concrete harnesses. `harnessiq/agents/base/agent.py` owns the generic loop, transcript management, tool execution, reset behavior, agent instance registry wiring, and post-run ledger emission.
- `harnessiq/agents/exa_outreach/agent.py` is the ExaOutreach harness. It wires Exa tools, optional Resend tools, and internal logging tools into a `ToolRegistry`, persists memory with `ExaOutreachMemoryStore`, builds the system prompt from `prompts/master_prompt.md`, and exposes structured run outputs for the ledger.
- `harnessiq/shared/exa_outreach.py` contains the ExaOutreach data model boundary: `ExaOutreachAgentConfig`, `EmailTemplate`, `LeadRecord`, `EmailSentRecord`, `OutreachRunLog`, and the durable memory/run-log store. This is the natural home for any top-level configuration state that must survive constructor boundaries and be reflected in logs or prompts.
- `harnessiq/cli/exa_outreach/commands.py` is the user-facing CLI surface. It persists query/runtime state in `query_config.json`, constructs the SDK agent from factories, and summarizes the run. Existing runtime parameters are CLI-managed through `--runtime-param`, not bespoke flags.
- `harnessiq/utils/run_storage.py` is the deterministic storage contract. The agent logs typed events into per-run JSON files via `StorageBackend`. That already satisfies the “save leads to memory json file” half of the request and also feeds the post-run sink/ledger layer via `BaseAgent`.
- `tests/test_exa_outreach_agent.py` and `tests/test_exa_outreach_cli.py` are the focused regression suites for this feature area. The test style in this repo is behavior-oriented, with constructor/tool-surface assertions, run-file assertions, and CLI parser/runtime assertions.
- `README.md` documents ExaOutreach as a public SDK and CLI surface. The current docs are email-first and include an outdated storage-backend example signature, so any public search-only mode should be reflected there rather than staying implicit.

Conventions observed:

- Configuration is explicit and typed at the shared-model layer, then reassembled into runtime objects inside the concrete agent harness.
- Tool availability is determined deterministically at construction time. If a tool is not added to the `ToolRegistry`, the model cannot call it.
- Durable state is written by tool handlers, not inferred from model text.
- CLI runtime behavior is generally represented as normalized `KEY=VALUE` runtime parameters persisted in memory and reloaded at run time.
- Tests rely on mocked clients and narrow fixtures rather than full end-to-end provider calls.

Notable inconsistencies relevant to this task:

- The ExaOutreach prompt is entirely email-oriented today, so hiding Resend tools alone would leave the prompt telling the model to use capabilities that no longer exist.
- The SDK currently requires non-empty `email_data` even though a search-only mode would not need templates.
- The CLI currently always requires `--resend-credentials-factory` and `--email-data-factory`, which conflicts with a clean search-only workflow unless that surface is adjusted.
- `README.md` still shows an older `StorageBackend` example API (`log_lead`, `log_email_sent`, `is_contacted`) while the actual protocol is `log_event` and `has_seen`.

### 1b: Task Cross-Reference

User request mapped onto the codebase:

1. “Add a `search_only` parameter at the top level of the agent, default false.”
   - Primary implementation point: `harnessiq/agents/exa_outreach/agent.py` constructor.
   - Shared config/state impact: `harnessiq/shared/exa_outreach.py` so the mode is represented in `ExaOutreachAgentConfig` and available to prompt/ledger logic.
   - Agent instance payload impact: `_build_exa_outreach_instance_payload(...)` in `harnessiq/agents/exa_outreach/agent.py` should include this new top-level behavior flag so instance identity remains stable and inspectable.

2. “When true, the agent only uses Exa to search for leads and does not try to email them.”
   - Tool-surface impact: `harnessiq/agents/exa_outreach/agent.py` must deterministically omit Resend tools when `search_only=True`.
   - Internal tool impact: template-selection and email-log tools may need to be omitted or at minimum made irrelevant in search-only mode, otherwise the prompt still advertises an email workflow.
   - Prompt impact: `harnessiq/agents/exa_outreach/prompts/master_prompt.md` plus prompt assembly logic in `build_system_prompt()` need a search-only branch or injected mode-specific instructions.

3. “Deterministically doesn’t have access to the resend tools when this param is set to true.”
   - Exact enforcement point: tool registration in `ExaOutreachAgent.__init__`.
   - Verification point: `tests/test_exa_outreach_agent.py` should assert that `resend.request` is absent in search-only mode even if credentials are supplied.
   - CLI verification point: `tests/test_exa_outreach_cli.py` should assert that CLI run construction can omit resend wiring or that the constructed agent receives `search_only=True`.

4. “Only saves the leads when it finds them.”
   - Existing mechanism: `exa_outreach.log_lead` already writes deterministic `lead` events to the active run file via `StorageBackend.log_event`.
   - Existing sink mechanism: `BaseAgent` emits post-run ledger entries through runtime-config output sinks. `build_ledger_outputs()` in `ExaOutreachAgent` already surfaces `leads_found` and `emails_sent`; in search-only mode, `emails_sent` should remain empty.
   - No new persistence backend is obviously required; the change is primarily behavioral gating plus preserving lead logging.

5. “Agent either saves them to either agent memory json file or a sink that we have defined.”
   - Current architecture already supports both:
     - memory JSON: `memory_path/runs/run_N.json` via `FileSystemStorageBackend`
     - sinks: post-run ledger exports via `AgentRuntimeConfig.output_sinks`
   - The feature should preserve this behavior without adding in-loop sink writes, which would violate the file-index rule that sinks are post-run export concerns.

6. “Adhere to the file index.”
   - This means:
     - keep the change inside the agent/config/CLI/test boundaries already responsible for ExaOutreach behavior
     - preserve provider-backed tool boundaries rather than making ad hoc Exa/Resend calls
     - keep deterministic state persistence inside tool handlers and post-run sinks
     - avoid turning sinks into active agent tools

Likely blast radius:

- SDK agent constructor/config/state
- prompt assembly and possibly prompt text
- CLI configure/show/run runtime parameter handling
- ExaOutreach agent tests
- ExaOutreach CLI tests
- public README examples/docs for SDK and CLI usage

### 1c: Assumption & Risk Inventory

Assumptions currently embedded in the request:

- `search_only` is intended as a public user-facing mode, not an internal-only helper flag.
- This mode should be reachable for both SDK users and CLI users, because the current ExaOutreach feature is exposed in both places and the request refers to “when the user sets this to true.”
- Existing lead logging to run files plus post-run output sinks is sufficient for the persistence requirement; no new sink contract is required.
- Search-only mode should preserve lead de-duplication behavior by continuing to consult prior lead logs before logging the same URL again.

Risks and ambiguities that materially affect implementation:

- `email_data` requirement: today the SDK constructor hard-requires at least one template. If `search_only=True`, requiring email templates would make the mode awkward and partially contradictory.
- CLI contract: today `outreach run` hard-requires both resend credentials and email templates. If search-only is a real mode, forcing those inputs would weaken the feature and likely confuse users.
- Prompt mismatch risk: if the tool surface changes without changing prompt instructions and parameter sections, the model will still be told to pick templates and send emails.
- Public-surface drift risk: if the SDK changes but the CLI/docs do not, the repo will expose inconsistent semantics for the same agent.
- Dirty-root risk: the repository root is currently very dirty and on `feature/agent-audit-ledger-sinks`, so implementation must be isolated in a fresh worktree to avoid crossing unrelated user changes.

Phase 1 complete.
