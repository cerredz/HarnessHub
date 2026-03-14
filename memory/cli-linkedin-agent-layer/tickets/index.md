# CLI LinkedIn Agent Layer Ticket Index

1. Ticket 1: Add managed LinkedIn agent memory artifacts for CLI-driven configuration
   - Extend the LinkedIn memory model so CLI-managed files, parameters, and custom prompt data persist in one agent-scoped folder.
   - Status: implemented locally. GitHub issue creation and PR creation remain blocked because `gh` is unauthenticated in this environment.

2. Ticket 2: Add the Harnessiq CLI package and installable command entrypoint
   - Introduce the package-native CLI root, dispatch layer, and console-script wiring.
   - Depends on: Ticket 1.
   - Status: implemented locally. GitHub issue creation and PR creation remain blocked because `gh` is unauthenticated in this environment.

3. Ticket 3: Implement LinkedIn CLI commands for managed inputs and agent execution
   - Deliver scriptable LinkedIn subcommands for preparing memory, ingesting files, persisting parameters, and running the agent.
   - Depends on: Ticket 1, Ticket 2.
   - Status: implemented locally. GitHub issue creation and PR creation remain blocked because `gh` is unauthenticated in this environment.

Phase 3a complete

Phase 3 complete locally; GitHub issue creation could not be completed because `gh` is unauthenticated in this environment.
