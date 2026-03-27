Title: Convert platform CLI and profile storage surfaces to DTO-based contracts

Intent:
Replace the platform CLI’s raw adapter/context/result dictionaries with explicit DTOs so the CLI boundary is self-documenting and aligned with the new DTO-first public agent APIs.

Issue URL:
https://github.com/cerredz/HarnessHub/issues/329

Scope:
- Introduce CLI DTOs in the shared DTO package.
- Convert adapter context, adapter result payloads, profile/run snapshot transport, and platform command helpers to DTO-based contracts.
- Keep the CLI’s emitted JSON shape stable where possible by serializing DTOs at the final emission boundary.
- Do not redesign argparse command semantics or provider credential resolution logic beyond what the DTO conversion requires.

Relevant Files:
- `harnessiq/shared/dtos/cli.py` - new CLI-boundary DTO definitions.
- `harnessiq/cli/adapters/base.py` - replace raw dict return types with CLI DTO contracts.
- `harnessiq/cli/adapters/context.py` - replace raw runtime/custom parameter transport with DTO-backed context fields where appropriate.
- `harnessiq/cli/adapters/utils/payloads.py` - serialize CLI DTOs into final JSON-safe output envelopes.
- `harnessiq/cli/commands/command_helpers.py` - replace raw `_base_payload()` / run-request glue with DTO composition.
- `harnessiq/cli/commands/platform_commands.py` - consume DTOs throughout the platform command flow.
- `harnessiq/config/harness_profiles.py` - convert persisted profile/run snapshot boundaries to DTO-aligned transport where appropriate.
- `tests/test_platform_cli.py` - update platform CLI expectations to DTO-driven internals with stable final JSON.
- `tests/test_harness_profiles.py` - verify DTO-aware persisted profile/run snapshot behavior.

Approach:
Create focused CLI DTOs for adapter context, adapter state/results, and persisted run/profile transport. The command layer can keep emitting JSON dictionaries at the outermost terminal boundary, but the internal CLI contracts should become DTO-first so they no longer pass anonymous nested dicts between adapters, command helpers, and profile storage. This ticket comes after the agent DTO tickets so CLI code can target stable DTO-based agent contracts.

Assumptions:
- Final CLI stdout should remain JSON for user-facing compatibility.
- Internal DTOs can coexist with persisted JSON files as long as serialization is explicit and tested.
- The command helper layer is the right place to centralize DTO-to-JSON conversion before `emit_json(...)`.

Acceptance Criteria:
- [ ] The platform CLI adapter/context/result contracts in scope use explicit DTOs rather than raw dicts.
- [ ] Profile and run-snapshot persistence logic is DTO-aware and remains loadable from JSON storage.
- [ ] The platform CLI tests continue to pass with stable final JSON output shape.
- [ ] No platform command loses existing resume/profile behavior due to the DTO conversion.

Verification Steps:
- Run `tests/test_platform_cli.py`.
- Run `tests/test_harness_profiles.py`.
- Run any CLI/common tests affected by the changed command-helper contracts.
- Smoke-check `prepare`, `show`, and `run` for at least one platform harness.

Dependencies:
- Ticket 1.
- Ticket 2.
- Ticket 3.

Drift Guard:
This ticket must stay inside the platform CLI/profile boundary. It must not absorb provider client/tool DTO work or unrelated command-surface redesign.
