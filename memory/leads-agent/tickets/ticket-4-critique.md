# Ticket 4 Critique

## Findings
- Letting the model decide when and how to switch ICPs would have made the run boundary ambiguous and would have mixed prior ICP transcript noise into later ICP prompt windows.
- The pruning signal needed to come from durable search progress, not raw transcript size, otherwise tool chatter and context resets would distort when pruning fired.

## Improvements Applied
- Moved ICP orchestration into `LeadsAgent.run()` so Python owns the outer `for` loop and the model only works inside the current ICP segment.
- Added internal tools for search logging, manual compaction, dedupe checks, and lead saving, all backed by the shared leads memory/storage layer.
- Overrode `pruning_progress_value()` to sum durable per-ICP search counts, ensuring transcript pruning aligns with real search work rather than ephemeral transcript length.
- Kept provider-tool composition generic through the shared provider factory catalog while still allowing injected tools for deterministic harness tests.
