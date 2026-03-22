1. Scope of provider support
Ambiguity: the conversation names `apollo`, `leadiq`, `lemlist`, and “etc.”, but this repo currently has tooling for `leadiq`, `lemlist`, `outreach`, `zoominfo`, `peopledatalabs`, `snovio`, and others, not Apollo.
Why it matters: this determines whether I should build a generic provider-injection harness over the providers already present, or also add a new provider integration as part of the ticket.
Options:
- Preferred: implement the leads agent generically over the providers already present in this repo, with platform selection as config.
- Alternative: also add a net-new Apollo provider/tool surface now.
- Alternative: restrict v1 to a smaller explicit subset such as `leadiq + lemlist`.

2. Scope of save destinations for v1
Ambiguity: the conversation mentions Google Drive, database connection, or agent memory as possible save targets.
Why it matters: this changes whether the task is a harness-only implementation with a pluggable storage abstraction, or a broader integrations project.
Options:
- Preferred: implement a pluggable `StorageBackend` contract with a default filesystem backend; other destinations can be added later.
- Alternative: filesystem backend plus one additional concrete integration now.
- Alternative: in-memory/session-only persistence for the first cut.

3. ICP orchestration boundary
Ambiguity: “each ICP gets an agent loop” could mean one agent instance that advances through ICP state internally, or an outer controller that spins a fresh sub-run per ICP.
Why it matters: it determines the memory model, run logging model, and whether context resets happen inside one run or between per-ICP runs.
Options:
- Preferred: one leads agent run that maintains an ICP queue and advances through ICPs via deterministic internal state.
- Alternative: a controller launches one fresh run per ICP and aggregates results across runs.

4. Search-history compaction contract
Ambiguity: the requested design says tool calls are ephemeral, searches persist, and every 500 searches the search log is summarized.
Why it matters: the current `BaseAgent` transcript model does not deterministically drop tool-call/result entries after each turn unless the runtime is changed.
Options:
- Preferred: keep the base runtime intact, persist search logs outside the transcript, and inject rolling summaries/tails as parameter sections; transcript resets stay threshold-based.
- Alternative: extend `BaseAgent` so the leads agent can deterministically compact transcript state on a fixed interval.
- Alternative: leave compaction mostly model-driven through the existing context tools.

5. Initial public surface
Ambiguity: the task says “implement the leads agent,” but does not say whether v1 must include CLI commands/docs/examples or only the SDK harness and tests.
Why it matters: adding CLI support expands the blast radius into `harnessiq/cli/`, docs, and packaging examples.
Options:
- Preferred: deliver the SDK agent harness, shared models/memory store, and tests first.
- Alternative: include a minimal CLI entrypoint in the same pass.

## Responses

1. Provider scope for v1
Response: add Apollo and fully integrate it into the repo. Existing providers should remain injectable alongside Apollo.
Implication: implementation now includes a net-new Apollo provider stack (`providers`, `tools`, tests, toolset catalog/file index updates) plus the leads agent harness consuming it.

2. Save destinations for v1
Response: include the pluggable `StorageBackend` for agent memory.
Implication: the leads agent should persist through a storage abstraction rather than hard-coding filesystem writes, but should still ship with a default file-backed backend.

3. ICP orchestration boundary
Response: use one agent with a `for` loop over ICPs; each iteration should save searches scoped to that ICP and replace the ICP context in the context window.
Implication: the leads agent should manage a single run with deterministic per-ICP state, not spawn separate per-ICP harness instances.

4. Search-history compaction contract
Response: tool-call transcript pruning should happen deterministically on a fixed interval based on search count or total token length, with shared config/constants.
Implication: this requires a shared runtime enhancement rather than relying only on the current threshold-based `BaseAgent.reset_context()` behavior.

5. Initial public surface
Response: add everything.
Implication: deliver the SDK harness, provider integration, runtime changes, tests, docs, exports, and CLI support in this pass.
