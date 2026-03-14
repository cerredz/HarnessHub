Title: Add the Harnessiq CLI package and installable command entrypoint
Issue URL: Not created; `gh` is installed but unauthenticated in this environment.

Intent: Create a first-class scriptable CLI surface inside the `harnessiq` package so SDK users can invoke package functionality from the command line instead of only through Python imports.

Scope:
- Add the top-level CLI package under `harnessiq/`.
- Provide a stable `main()` entrypoint and console-script wiring in packaging metadata.
- Define the CLI dispatch structure that can host LinkedIn-specific subcommands.
- Do not implement the full LinkedIn memory-management and run commands in this ticket beyond the dispatch scaffolding they require.

Relevant Files:
- `harnessiq/cli/__init__.py`: expose the CLI package surface.
- `harnessiq/cli/__main__.py`: support `python -m harnessiq.cli`.
- `harnessiq/cli/main.py`: implement top-level argument parsing and subcommand dispatch.
- `pyproject.toml`: add the installable console-script entrypoint.
- `tests/test_sdk_package.py`: extend packaging smoke coverage to exercise the CLI entrypoint surface.

Approach:
- Use the standard-library `argparse` module so the CLI remains scriptable, dependency-light, and consistent with the repository’s current minimal dependency posture.
- Keep the top-level CLI thin: parse arguments, route to subcommand handlers, and return process exit codes instead of embedding LinkedIn business logic in the root module.
- Wire the CLI through both `python -m harnessiq.cli` and a named console script so local editable installs and built distributions behave consistently.

Assumptions:
- The repository should stay dependency-light and avoid introducing `click` or `typer` for this task.
- A console script in `pyproject.toml` is acceptable and should be covered by smoke tests.
- LinkedIn will be the first CLI domain, but the root CLI structure should leave room for future agent-specific command groups.

Acceptance Criteria:
- [ ] A `harnessiq.cli` package exists with a callable `main()` entrypoint.
- [ ] The CLI can be invoked via `python -m harnessiq.cli --help`.
- [ ] The package metadata exposes a console script for the CLI.
- [ ] The root CLI dispatch can route to a LinkedIn command group without importing unrelated runtime layers eagerly.
- [ ] Packaging tests validate the CLI surface in the built wheel.

Verification Steps:
- Static analysis: manually review parser layout, import boundaries, and exit-code handling.
- Type checking: no configured checker; validate CLI function signatures and imports via tests and direct invocation.
- Unit tests: run `python -m unittest tests.test_sdk_package`.
- Integration and contract tests: run the full package smoke/build tests after adding the console script.
- Smoke/manual verification: run `python -m harnessiq.cli --help` from the repository and confirm the root command renders expected help text.

Dependencies:
- Ticket 1: Add managed LinkedIn agent memory artifacts for CLI-driven configuration.

Drift Guard: This ticket must not hard-code LinkedIn-specific persistence behavior into the root CLI. It establishes the command entrypoint and dispatch layer only.
