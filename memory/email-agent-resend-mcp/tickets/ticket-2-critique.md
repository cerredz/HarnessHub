## Self-Critique

- The abstract email harness needed to stay reusable rather than drifting into a concrete campaign agent, so the prompt scaffolding and extra parameter sections were kept hook-based.
- The export wiring had to be aligned with the repository's newer shared-definition layout instead of assuming the earlier `src/agents/__init__.py` shape.

## Implemented Improvements

- Kept the class abstract with explicit hooks for objective, additional parameter sections, extra rules, and optional extra instructions.
- Patched the public export surface against the current working-tree layout and added tests that verify both masked credential injection and allowed-operation limiting.
