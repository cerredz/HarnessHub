### Phase 2 Clarifications

1. CLI scope boundary
   Ambiguity: the request can be interpreted as either a configuration CLI or a runnable agent CLI.
   Why it matters: this decides whether I only build commands that manage LinkedIn memory/config files, or whether I also add a command that constructs and launches `LinkedInJobApplierAgent`.
   Options:
   - Configuration-only CLI that prepares memory/config for later SDK use.
   - Configuration + run CLI that also launches the LinkedIn agent once inputs are set.
   - Full workflow CLI with both setup commands and an execution command as separate subcommands.

2. Meaning of "upload files"
   Ambiguity: "upload files" could mean storing references to files, copying files into agent memory, or driving a live browser upload.
   Why it matters: each choice changes persistence, validation, and how the LinkedIn agent consumes the files later.
   Options:
   - Save file paths in CLI-managed config so the browser runtime can use them later.
   - Copy user files into the LinkedIn memory directory and track those copied paths.
   - Both: copy the files into managed storage and expose the resolved managed paths in config.

3. Shape of the custom parameter layer
   Ambiguity: "custom parameters" could refer only to existing `LinkedInAgentConfig` fields or to arbitrary user-defined metadata.
   Why it matters: this determines whether I build a typed config model with known keys or a more flexible schema that the agent injects into its prompt/context.
   Options:
   - Typed runtime params only: `max_tokens`, `reset_threshold`, `action_log_window`, `linkedin_start_url`, `notify_on_pause`, `pause_webhook`, `memory_path`.
   - Typed params plus arbitrary extra key/value pairs persisted for the LinkedIn agent.
   - Arbitrary free-form sections/documents that get injected into the agent context as additional parameter blocks.

4. CLI UX style
   Ambiguity: it is unclear whether you want a scriptable command surface, an interactive wizard, or both.
   Why it matters: argument parsing, tests, and the package entrypoint differ substantially between a non-interactive CLI and an interactive setup flow.
   Options:
   - Non-interactive subcommands with flags and file arguments.
   - Interactive setup command plus non-interactive edit/update commands.
   - Interactive-only flow.

### User Responses

1. CLI scope boundary
   Response: the CLI should be the executable surface that runs the SDK rather than only configuring files.
   Implication: implementation needs a runnable command path that can construct the LinkedIn agent from CLI-managed state, not just a setup utility.

2. Meaning of "upload files"
   Response: the CLI should both store the source file paths and copy the files or file content into managed LinkedIn memory storage.
   Implication: each LinkedIn agent instance needs a managed memory folder, likely with a dedicated subdirectory for user-provided artifacts plus persisted metadata that preserves the original source path.

3. Shape of the custom parameter layer
   Response: support user-defined key/value data and free-form prompt data, aligned with the agent class parameters.
   Implication: the CLI should likely persist:
   - typed runtime params that map onto `LinkedInJobApplierAgent` constructor/config fields,
   - arbitrary metadata key/value pairs,
   - additional free-form prompt content that can be injected into the agent parameter sections.

4. CLI UX style
   Response: scriptable.
   Implication: the CLI should use deterministic subcommands and flags rather than an interactive wizard.
