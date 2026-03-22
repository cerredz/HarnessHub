Title: Add first-class custom sink registration to the ledger subsystem

Intent:
Enable SDK users to define new output sink types and resolve them through `build_output_sinks()`, connection records, and sink specs without patching framework internals.

Scope:
- Add a sink-registry surface to the ledger subsystem.
- Keep built-in sink behavior intact.
- Export the new registration/listing helpers through the public SDK surface.
- Add tests for custom sink registration and sink construction.
- Do not change the audit-ledger execution model or let sinks participate in model turns.

Relevant Files:
- `harnessiq/utils/ledger_sinks.py`: introduce sink-registry helpers and route sink construction through them.
- `harnessiq/utils/ledger.py`: re-export new ledger sink helpers.
- `harnessiq/utils/__init__.py`: expose new public helpers.
- `tests/test_output_sinks.py`: verify registration, collision handling, and custom sink construction.

Approach:
Define a lightweight sink factory registry with built-ins registered as defaults, then make `build_sink_from_spec()`, `build_sink_from_connection()`, and `build_output_sinks()` resolve sink types through that registry. Expose minimal public helpers to register, inspect, and build sink types while preserving the current built-in sink API and spec syntax.

Assumptions:
- Custom sink registration should be additive and module-level, similar to the toolset registry model.
- Built-in sink names remain reserved and should reject accidental overwrite.

Acceptance Criteria:
- [ ] SDK users can register a custom sink factory under a new sink type name.
- [ ] `build_output_sinks()` can build registered custom sinks from sink specs and connection records.
- [ ] Built-in sink behavior and public imports remain unchanged.
- [ ] Duplicate sink-type registration raises a clear error.
- [ ] Tests cover custom sink registration and construction.

Verification Steps:
- Run `pytest tests/test_output_sinks.py`.
- Run any adjacent agent runtime tests affected by sink resolution.

Dependencies:
- None.

Drift Guard:
This ticket must not redesign the ledger format, alter sink execution timing, or move sink logic out of the post-run layer. It is strictly an extensibility enhancement for sink definition and construction.
