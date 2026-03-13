This artifact is useful for the information related to the structure/directory layout of the codebase. It contains a brief index of the meaningful folders in the repository.

src/:

- `src/tools/`: canonical tool schemas, tool registry helpers, and built-in example tools
- `src/providers/`: provider-specific payload translation helpers and shared provider formatting utilities
- `src/agents/`: abstract runtime-capable agent primitives

tests/:

- unit tests covering tools, providers, and agents

memory/:

- task artifacts for planning, quality results, critique notes, and PR context

artifacts/:

- repository-level structural documentation such as this file index
