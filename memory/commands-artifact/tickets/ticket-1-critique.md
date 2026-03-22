## Self-Critique

Initial review found one maintainability gap: the artifact described the current CLI surface, but it did not explicitly tell future contributors when it should be updated. That increases the chance of drift after later parser changes.

## Improvement Applied

Added a short maintenance note near the top of `artifacts/commands.md` instructing contributors to update the artifact whenever a new subparser or subcommand is added under `harnessiq/cli/`.

## Residual Risk

The artifact is still maintained manually. It is accurate now, but future parser additions can still drift if contributors skip the update note.
