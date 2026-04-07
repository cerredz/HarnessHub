## Self-Critique

1. Initial file copies were too blunt against current `main`.
   - Copying older branch versions into the PR worktree dropped newer definitions that already existed on `main` (`BrowserUseCredentials`, current CLI runner seams, current harness manifest surfaces).
   - Improvement: restored those files to `HEAD` and reapplied only the intended boundary changes so the PR stays compatible with the current branch tip.

2. The architecture guard needed to match the refactor scope.
   - A blanket "shared may only import shared" assertion was too strict for the current codebase and would have failed on unrelated existing dependencies.
   - Improvement: narrowed the test to the concrete regressions this refactor addresses: `shared/email.py` importing `tools.resend`, `shared/credentials.py` importing `config.models`, and the `shared` modules that previously imported `utils.run_storage` / `utils.ledger_models`.

3. Shared ownership needed to cover the full CLI path, not just command wrappers.
   - Moving runtime-parameter normalization into `shared/` but leaving builders and runners to coerce through manifests would still duplicate responsibility in the CLI layer.
   - Improvement: updated the Exa Outreach and Leads builders/runners to call the shared normalization functions directly while preserving the current runner architecture.
