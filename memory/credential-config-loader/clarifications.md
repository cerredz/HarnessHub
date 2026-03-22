## Clarifications

1. Credential payload contract

The repo currently has no general secret store, only direct `ResendCredentials` objects in [harnessiq/tools/resend.py](C:/Users/Michael Cerreto/HarnessHub/harnessiq/tools/resend.py) and raw `api_key: str` fields in provider clients. Your note that the stored values should be "solely environment variables or api keys" can be implemented in two materially different ways:

- persist literal secret values and env-var references side by side
- persist only env-var names/references and resolve secrets from the process environment at load time
- allow both, but validate that every stored entry is one of those two kinds

This changes the storage format, security model, and the runtime loader API. Which contract do you want?

Response:

- Read from the repo `.env` file.
- Raise an error if the `.env` file does not exist.
- Raise an error if a variable required for the target agent is missing.

Implication:

- The first implementation should treat the repo-local `.env` file as the canonical credential source instead of persisting literal secrets in managed JSON state.
- The config layer should store references to required environment-variable names and resolve them at load time.

2. Initial support scope

Today the only agent with an explicit credential parameter is the email path in [harnessiq/agents/email.py](C:/Users/Michael Cerreto/HarnessHub/harnessiq/agents/email.py). `LinkedInJobApplierAgent` has durable runtime state but no dedicated credentials parameter. Should this ticket:

- add the new config-loader/store generically, wire it into the current email/Resend agent path, and leave the abstraction ready for future agents
- also retrofit the current provider clients under `harnessiq/providers/` to load from the same config layer now
- also introduce a new credentials parameter surface to agents that do not currently have one

This determines whether the change stays medium-scope or becomes a broader SDK-wide credential refactor.

Response:

- Add the new layer under `harnessiq/config/`.
- Add a new credentials parameter to agents that do not currently have one.

Implication:

- The implementation should introduce a general credential-config API in `harnessiq/config/` and update the public agent constructors to accept a credentials/config object consistently.
- Provider-client retrofits were not explicitly requested in the response, so the first implementation will keep provider clients unchanged unless needed internally.

3. Meaning of "upload"

The repository currently has CLI-managed file ingestion only for LinkedIn memory in [harnessiq/cli/linkedin/commands.py](C:/Users/Michael Cerreto/HarnessHub/harnessiq/cli/linkedin/commands.py). For this credential work, should "upload" mean:

- SDK-only APIs such as `store.save(...)` / `store.load(...)`
- SDK APIs plus loading from a JSON config file on disk
- SDK APIs plus a new CLI command for writing credential configs

This affects whether I stay inside the SDK package or also expand the CLI surface.

Response:

- Support SDK APIs.
- Support a new CLI command.
- Users should be able to work either through the CLI or directly in code.

Implication:

- The config layer needs both a Python API and a command-line workflow for registering and inspecting agent credential bindings.
- The CLI surface should be general to the SDK rather than LinkedIn-specific because the user wants credential management across agents.
