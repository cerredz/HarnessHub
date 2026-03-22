No blocking ambiguities remained after Phase 1.

Working assumption:

- "All CLI commands" means the full currently registered command surface exposed by the root argparse parser, including command families such as `linkedin` and `connect`, plus their concrete subcommands.

Implementation implication:

- The artifact will catalog commands and subcommands with short descriptions, but it will not attempt to document every option flag for every command.
