## Phase 1

### 1a: Structural Survey

The repository is a Python 3.11+ SDK and CLI centered on the live `harnessiq/` package. `build/`, `src/`, `.pytest_cache/`, and package metadata directories are generated residue and not authoritative runtime sources. The generated architecture references in [`artifacts/file_index.md`](C:\Users\422mi\HarnessHub\artifacts\file_index.md) and [`README.md`](C:\Users\422mi\HarnessHub\README.md) are derived from live code by [`scripts/sync_repo_docs.py`](C:\Users\422mi\HarnessHub\scripts\sync_repo_docs.py), so source changes that affect the CLI or sink inventory must be followed by doc regeneration rather than hand-edited docs.

Top-level architecture is split cleanly:
- `harnessiq/agents/` contains harness implementations and the shared runtime. The output-sink hook is in [`harnessiq/agents/base/agent_helpers.py`](C:\Users\422mi\HarnessHub\harnessiq\agents\base\agent_helpers.py), where completed runs emit a `LedgerEntry` after execution and sink failures are logged and swallowed.
- `harnessiq/utils/` owns the ledger subsystem and built-in sink implementations. [`harnessiq/utils/ledger_models.py`](C:\Users\422mi\HarnessHub\harnessiq\utils\ledger_models.py) defines `LedgerEntry` and the `OutputSink` protocol. [`harnessiq/utils/ledger_connections.py`](C:\Users\422mi\HarnessHub\harnessiq\utils\ledger_connections.py) persists global sink connections and parses per-run sink specs. [`harnessiq/utils/ledger_sinks.py`](C:\Users\422mi\HarnessHub\harnessiq\utils\ledger_sinks.py) is the built-in sink registry and constructor surface.
- `harnessiq/providers/` owns external-system clients and compatibility facades. Provider-backed sink transport helpers live in [`harnessiq/providers/output_sink_clients.py`](C:\Users\422mi\HarnessHub\harnessiq\providers\output_sink_clients.py) and are re-exported through [`harnessiq/providers/output_sinks.py`](C:\Users\422mi\HarnessHub\harnessiq\providers\output_sinks.py) and [`harnessiq/providers/__init__.py`](C:\Users\422mi\HarnessHub\harnessiq\providers\__init__.py).
- `harnessiq/cli/ledger/commands.py` owns global `connect`, `connections`, `logs`, `export`, and `report` commands. Each built-in sink gets an explicit `connect <sink>` registration with typed CLI flags.
- `tests/` uses `unittest` and `pytest` together. Sink behavior is concentrated in [`tests/test_output_sinks.py`](C:\Users\422mi\HarnessHub\tests\test_output_sinks.py) and CLI registration/round-trips in [`tests/test_ledger_cli.py`](C:\Users\422mi\HarnessHub\tests\test_ledger_cli.py).

The sink data flow is consistent:
1. Agents finish a run and build one `LedgerEntry`.
2. The runtime resolves default and explicit output sinks.
3. Each sink receives the immutable entry via `on_run_complete`.
4. Built-in sink types are created by name from either persisted `connections.json` or per-run `--sink` specs.
5. Provider-backed sinks delegate network or storage delivery to dedicated client helpers.

Conventions visible in the sink surface:
- Built-in sink implementations are `@dataclass(slots=True)` classes with small `on_run_complete` methods.
- External integrations are wrapped behind minimal client classes instead of embedding request logic directly in CLI or agents.
- Public compatibility surfaces matter. If a new client or sink is added, the repo typically re-exports it through `harnessiq.providers`, `harnessiq.providers.output_sinks`, `harnessiq.utils.ledger`, and `harnessiq.utils`.
- Tests prefer behavior assertions with `MagicMock` clients over implementation-detail assertions.
- Generated docs are treated as contract artifacts and must stay in sync with source.

Relevant inconsistencies and constraints:
- Some sinks are pure local file/webhook sinks while others rely on provider clients, so MongoDB can reasonably join the provider-client path even though it is not a traditional model/service provider package.
- Current provider-backed sink clients are HTTP-only; MongoDB support will likely require a driver dependency because there is no existing generic MongoDB client abstraction in the repo.
- There is no existing MongoDB naming or credential convention anywhere in the repository, so the sink config shape will need to be introduced deliberately but still match the surrounding sink style.

### 1b: Task Cross-Reference

User request: add a MongoDB sync so a user can connect an agent export with MongoDB like the other built-in sinks, while adhering to the repository file index.

Concrete codebase mapping:
- Built-in sink registration belongs in [`harnessiq/utils/ledger_sinks.py`](C:\Users\422mi\HarnessHub\harnessiq\utils\ledger_sinks.py). This is where the new `MongoDBSink` class and `"mongodb"` factory entry should live.
- Global CLI connection support belongs in [`harnessiq/cli/ledger/commands.py`](C:\Users\422mi\HarnessHub\harnessiq\cli\ledger\commands.py). Adding `harnessiq connect mongodb ...` requires registering the sink and its required flags there.
- Per-run sink overrides already flow through `parse_sink_spec()` and `build_output_sink()`, so no new parsing subsystem is needed. The new sink just needs a stable config shape that works in both CLI and programmatic paths.
- Provider-backed delivery logic belongs in [`harnessiq/providers/output_sink_clients.py`](C:\Users\422mi\HarnessHub\harnessiq\providers\output_sink_clients.py), with compatibility re-exports in [`harnessiq/providers/output_sinks.py`](C:\Users\422mi\HarnessHub\harnessiq\providers\output_sinks.py) and [`harnessiq/providers/__init__.py`](C:\Users\422mi\HarnessHub\harnessiq\providers\__init__.py).
- Public ledger utility exports belong in [`harnessiq/utils/ledger.py`](C:\Users\422mi\HarnessHub\harnessiq\utils\ledger.py) and [`harnessiq/utils/__init__.py`](C:\Users\422mi\HarnessHub\harnessiq\utils\__init__.py).
- Shared constants are currently only needed for HTTP-backed sinks in [`harnessiq/shared/output_sinks.py`](C:\Users\422mi\HarnessHub\harnessiq\shared\output_sinks.py). MongoDB may not require shared constants unless a default app name or similar constant is introduced.
- Tests need to expand in [`tests/test_output_sinks.py`](C:\Users\422mi\HarnessHub\tests\test_output_sinks.py) for sink construction, listing, client delegation, and optional explode behavior, and in [`tests/test_ledger_cli.py`](C:\Users\422mi\HarnessHub\tests\test_ledger_cli.py) for parser/connection coverage.
- User-facing sink documentation belongs in [`docs/output-sinks.md`](C:\Users\422mi\HarnessHub\docs\output-sinks.md).
- Because the file index and README are generated, [`scripts/sync_repo_docs.py`](C:\Users\422mi\HarnessHub\scripts\sync_repo_docs.py) must be rerun after the new sink is added so [`artifacts/file_index.md`](C:\Users\422mi\HarnessHub\artifacts\file_index.md), [`artifacts/commands.md`](C:\Users\422mi\HarnessHub\artifacts\commands.md), and [`README.md`](C:\Users\422mi\HarnessHub\README.md) reflect the live sink/CLI inventory.
- Packaging metadata will likely need updates in [`pyproject.toml`](C:\Users\422mi\HarnessHub\pyproject.toml) and [`requirements.txt`](C:\Users\422mi\HarnessHub\requirements.txt) if MongoDB requires a new runtime dependency.

Existing behavior that must be preserved:
- Output sinks remain post-run only and cannot affect the model loop.
- Sink failures remain non-fatal to completed runs.
- Existing sink names, CLI flags, and docs must remain intact.
- The `connect`/`connections` workflow must keep using `SinkConnection` and `ConnectionsConfigStore` rather than introducing a Mongo-specific config path.

Expected blast radius:
- Focused to the ledger/output-sink subsystem, provider sink-client exports, CLI sink registration, packaging dependencies, tests, and generated docs.
- No agent business logic, tool definitions, or manifest metadata should need changes.

### 1c: Assumption & Risk Inventory

Assumptions I can implement against without user follow-up:
- “MongoDB sync” means a new built-in output sink type named `mongodb` that persists completed ledger exports to a MongoDB collection.
- The sink should be available through the same three surfaces as the current built-ins: programmatic construction, `harnessiq connect mongodb ...`, and per-run `--sink "mongodb:key=value,..."`.
- The most compatible config shape is `connection_uri`, `database`, and `collection`, with optional `explode_field` mirroring the existing multi-record sink behavior in `LinearSink` and `GoogleSheetsSink`.
- Default behavior should be append-only insertion, analogous to `JSONLLedgerSink` and `SupabaseSink`, rather than update or upsert semantics.

Primary risks:
- Adding MongoDB support likely requires a new dependency such as `pymongo`; the version choice must be compatible with Python 3.11+ and not destabilize the current package.
- MongoDB document shape is not specified by the user. If the sink stores the full ledger entry by default and optional exploded records when configured, that needs to be documented clearly so users know what lands in the collection.
- URI strings may contain commas or equals signs, which are awkward for per-run `kind:key=value,key=value` parsing. The global `connect mongodb` path will be straightforward, but per-run examples should note quoting and the expectation that complex URIs are passed as a single CLI argument.
- If MongoDB insertion returns non-JSON-safe identifiers or metadata, the sink should avoid leaking transport-specific result objects into the runtime contract.

There are no blocking ambiguities that require a clarification stop. The existing sink architecture is strong enough to proceed with a standard MongoDB URI + database + collection design and document that choice.

Phase 1 complete.
