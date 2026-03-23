## Ticket 2 Critique

- CLI persistence is still not fully generic because the existing harnesses do not all store runtime-like values in the same file shape. This refactor deliberately centralized typing and metadata first without forcing a storage-layout rewrite.
- The LinkedIn CLI still accepts open-ended custom parameters, which the manifest marks explicitly. That preserves behavior, but it also means LinkedIn custom params are documented rather than strongly typed for now.
- The lazy sink-config and home-directory fallback fixes were added because the manifest refactor surfaced brittle environment assumptions during verification; both are low-risk robustness improvements.
