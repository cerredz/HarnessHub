No blocking ambiguities were identified after Phase 1.

Implementation will proceed against refreshed `main` with two bounded tickets:

1. Restore ExaOutreach runtime/storage compatibility and CLI run JSON stability on `main`.
2. Fix provider exception propagation so HTTP provider errors preserve the original exception instead of collapsing into a traceback-assignment `TypeError`.
