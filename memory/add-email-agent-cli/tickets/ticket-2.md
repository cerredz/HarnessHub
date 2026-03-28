Title: Add the dedicated and platform-first CLI surfaces for the email campaign harness
Intent: Replace the helper-script workflow with a first-class CLI system that matches repository patterns and gives the email agent the same lifecycle surface as existing dedicated harnesses.
Scope: Add the dedicated `email` command family, builder, runner, adapter, root CLI registration, manifest registration, and package exports. Do not regenerate docs in this ticket.
Relevant Files:
- `harnessiq/cli/email/__init__.py` — dedicated email CLI package export.
- `harnessiq/cli/email/commands.py` — dedicated parser-only email commands.
- `harnessiq/cli/builders/email.py` — email memory persistence and state summary logic.
- `harnessiq/cli/runners/email.py` — email run orchestration and credential resolution.
- `harnessiq/cli/adapters/email.py` — manifest-backed platform adapter.
- `harnessiq/cli/builders/__init__.py` — export the email builder.
- `harnessiq/cli/runners/__init__.py` — export the email runner.
- `harnessiq/cli/adapters/__init__.py` — export the email adapter.
- `harnessiq/cli/adapters/utils/stores.py` — add the prepared email-store loader.
- `harnessiq/cli/adapters/utils/__init__.py` — export the email-store loader.
- `harnessiq/cli/main.py` — register the dedicated `email` command family.
- `harnessiq/shared/harness_manifests.py` — register the built-in email manifest.
- `harnessiq/shared/__init__.py` — export the built-in email manifest.
Approach: Mirror the Instagram split exactly: `commands.py` only parses and delegates, builder owns persistence, runner owns execution, and adapter bridges the generic manifest-driven CLI. Use the existing credential-binding system for Resend rather than inventing a second secret path.
Assumptions:
- Dedicated `email` commands should cover `prepare`, `configure`, `show`, `run`, and one recipient-inspection command.
- Credential binding remains platform-first via `harnessiq credentials bind email ...`.
Acceptance Criteria:
- [x] `harnessiq email prepare|configure|show|run|get-recipients` exists.
- [x] The generic `prepare/show/run/inspect/credentials` commands recognize the built-in `email` harness.
- [x] The dedicated CLI remains thin and business logic lives in builders/runners/adapters/shared modules.
- [x] The email platform adapter requires a bound `resend` credential for runs.
Verification Steps:
- Run dedicated email CLI tests.
- Run platform CLI tests that inspect and execute the email harness.
Dependencies: `ticket-1.md`
Drift Guard: Do not bypass the manifest/adapter architecture and do not reintroduce one-off helper-script behavior under the CLI.
