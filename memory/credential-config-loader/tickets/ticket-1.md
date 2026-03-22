Title: Add repo `.env` credential config models and loader store

Issue URL: https://github.com/cerredz/HarnessHub/issues/28

Intent:
Introduce a reusable credential configuration layer under `harnessiq/config/` that maps agents to required environment-variable names, loads values from the repository `.env` file, and raises explicit errors when the file or required variables are missing.

Scope:
Create the new config package, define the credential reference/value models and loader/store APIs, add validation/error types, and add focused tests for loading, missing `.env`, and missing variables. This ticket does not wire agents or CLI commands yet.

Relevant Files:
- `harnessiq/config/__init__.py`: public exports for the new config layer
- `harnessiq/config/credentials.py`: credential config dataclasses, store, loader, and errors
- `harnessiq/__init__.py`: expose the new top-level `config` module
- `tests/test_credentials_config.py`: unit coverage for the new config layer
- `tests/test_sdk_package.py`: packaging/import smoke coverage for the new module
- `artifacts/file_index.md`: register the new top-level package area

Approach:
Define a small, typed credential-config system around agent-scoped credential bindings. The persisted config should store only environment-variable references and metadata, not secrets. Implement a lightweight `.env` parser locally to avoid adding dependencies. The store should support saving/loading a JSON config file in a predictable path and resolving an agent binding into concrete key/value pairs from the repo `.env`. Use explicit exception types for missing `.env` files, unknown agents, and missing variables so callers and CLI commands can surface actionable failures cleanly.

Assumptions:
- The repo root for `.env` resolution can be derived from the current working directory or an explicit store root passed to the API.
- Persisted credential configs should store env-var names only, not raw secret values.
- Agent-specific credential requirements can be represented as a generic mapping now and specialized by later tickets.

Acceptance Criteria:
- [ ] A public `harnessiq.config` module exists and is importable from the built package.
- [ ] The config layer can persist and reload agent credential bindings from disk.
- [ ] The loader reads from a repo `.env` file and returns resolved key/value pairs for an agent binding.
- [ ] Loading raises a clear error when the `.env` file is missing.
- [ ] Loading raises a clear error when a required env var for the selected agent is missing.
- [ ] New unit tests cover happy path and failure modes.

Verification Steps:
- Run the credential-config unit tests.
- Run packaging smoke tests that import `harnessiq.config` from the built wheel.
- Manually verify a temporary config file plus temporary `.env` file round-trip through the loader API.

Dependencies:
- None

Drift Guard:
This ticket must not wire any concrete agent constructors, provider clients, or CLI commands. It establishes only the reusable config-layer foundation and its tests.
