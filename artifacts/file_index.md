This artifact tracks the meaningful repository layout and the current architecture of the codebase. Keep it focused on the important folders and update it whenever the high-level package structure changes.

Context:

- This file is not meant to be a full inventory of every subdirectory or support artifact. Its job is to explain the architectural shape of the repository so a reader can understand where core product logic lives, where public-facing documentation lives, and where new work should usually be added.
- The top-level folders matter because they define the boundaries of the codebase: the SDK itself lives under `harnessiq/`, supporting documentation lives outside it, and repository artifacts describe or support the package rather than becoming part of the shipped runtime.

Codebase standards:

- Agents in this codebase are defined as harnesses: they inherit shared runtime behavior from the main `BaseAgent` class and then specialize prompts, parameter sections, tool wiring, and domain-specific logic.
- We define tools and toolsets as reusable building blocks for users. Users should be able to choose which tools or toolsets to inject into which agent rather than being locked into one fixed bundle.
- Agents should interact with external capabilities through the tool layer, and third-party platforms should be reached through provider-backed tools and provider clients rather than through undocumented ad hoc calls.
- Agents should be structured to accept an injected toolset or tool executor as part of their configuration instead of strictly defining the full tool surface internally. An agent can provide a sensible default toolset, but that default should remain overridable.
- Autonomous agents are expected to have a durable memory folder. That memory can store any files needed across runs, including user inputs, runtime parameters, custom parameters, action logs, and deterministic state records.
- Tools are not only optional model add-ons; they should be used wherever a deterministic check is possible. If an agent can verify state from durable memory or another authoritative source, it should do that explicitly instead of relying on model recall alone (for example, checking LinkedIn memory to confirm whether a job was already applied to).
- These agents are being built for full autonomy, so designs must assume multiple context window resets. Durable memory and parameter sections should carry forward the state needed to resume work without losing orientation.
- Agent behavior should be configurable through parameters. The shared runtime comes from `BaseAgent`, while concrete harnesses can expose runtime parameters and user-defined custom parameters where the workflow requires them.

Top-level directories:

- `artifacts/`: repository-level architecture and maintenance artifacts. This folder explains how the repo is organized and gives contributors a shared reference point for structural decisions.
- `docs/`: lightweight package documentation and usage guides. This folder matters because it explains how the SDK is intended to be used outside the source tree.
- `harnessiq/`: the production Python SDK package for Harnessiq. This is the most important top-level folder because it contains the runtime, abstractions, integrations, and public package surface that actually ship to users.

Source layout:

- `harnessiq/agents/`: provider-agnostic agent runtime primitives plus concrete agent harnesses
- `harnessiq/cli/`: package-native command-line entrypoints and root command dispatch
- `harnessiq/config/`: repo-local credential config models, persisted agent credential bindings, and `.env` loader/store helpers
- `harnessiq/integrations/`: adapters that bridge the core SDK to external runtime surfaces such as model implementations and browser automation
- `harnessiq/master_prompts/`: curated, deployable system prompts for agents and direct SDK use
- `harnessiq/providers/`: provider translation helpers, HTTP clients, and operation catalogs for both LLM providers and external-service APIs
- `harnessiq/shared/`: shared types, configs, and constants reused across modules
- `harnessiq/tools/`: the executable tool runtime layer, including built-in tools, prompt/filesystem helpers, reasoning tools, and provider-backed tool factories
- `harnessiq/toolset/`: plug-and-play toolset SDK for retrieving, composing, and registering built-in, provider, and custom tools
- `harnessiq/utils/`: agent-agnostic utility infrastructure such as run storage and other reusable support code that does not belong to a single agent, provider, or tool family
