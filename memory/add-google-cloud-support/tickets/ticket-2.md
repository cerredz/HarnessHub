Title: Add core GCP command parameters and flag fragments
Issue URL: https://github.com/cerredz/HarnessHub/issues/289
PR URL: https://github.com/cerredz/HarnessHub/pull/306

Intent:
Centralize the typed command inputs and the smallest reusable flag fragments so every later command module can build on one consistent command vocabulary.

Scope:
Add the foundational `commands/` pieces that all later builders depend on: `__init__.py`, `params.py`, and `flags.py`, plus targeted unit tests. This ticket does not add the per-service command-builder modules, provider classes, or CLI commands.

Relevant Files:
- `harnessiq/providers/gcloud/commands/__init__.py`: Re-export the public builder surface.
- `harnessiq/providers/gcloud/commands/params.py`: Add typed parameter dataclasses such as `JobSpec`, `ScheduleSpec`, and `SecretRef`.
- `harnessiq/providers/gcloud/commands/flags.py`: Add reusable flag-fragment builders.
- `tests/test_gcloud_commands_core.py`: Verify the parameter objects and flag fragments.

Approach:
Keep this layer completely pure: every helper returns either a typed dataclass or a `list[str]` fragment, with no subprocess calls, no filesystem access, and no imports from outside the `commands/` package beyond shared typing primitives. Encode the design invariants directly into flag behavior, especially omission of default values, no project flag emission, and one-flag-per-secret semantics.

Assumptions:
- The command-builder layer should follow the design doc closely because it aligns with repository preferences for explicit, unit-testable helpers.
- The `GcloudClient` from Ticket 1 will own project flag injection universally.
- The pure command-builder surface is large but still cohesive enough for one bounded ticket because it introduces no runtime side effects.

Acceptance Criteria:
- [ ] The `commands/` package exists with `params.py`, `flags.py`, and clean exports.
- [ ] Parameter dataclasses capture the shared command inputs with sensible defaults.
- [ ] Flag helpers omit empty/default values instead of emitting malformed flags.
- [ ] No helper in this layer emits a project flag.
- [ ] Unit tests assert representative parameter defaults and flag-fragment behavior.

Verification Steps:
- Static analysis: No configured linter; manually review imports, naming, and fragment formatting.
- Type checking: No configured type checker; keep all signatures annotated and validate via test imports.
- Unit tests: Run `pytest tests/test_gcloud_commands_core.py`.
- Integration and contract tests: Not applicable; the helpers are pure and should be validated with exact-value unit tests.
- Smoke and manual verification: Import `harnessiq.providers.gcloud.commands as cmd` in a shell and inspect representative flag fragments.

Dependencies:
Ticket 1.

Drift Guard:
Do not add the per-service command-builder modules, provider classes, CLI code, or subprocess execution in this ticket. The deliverable here is only the shared typed inputs and flag fragments.

