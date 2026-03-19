# Ticket 2 Critique

## Findings
- The initial pruning design would have been too generic if it only counted transcript entries, because the leads agent needs pruning to key off durable search progress rather than incidental tool chatter.
- The first runtime branch also allowed deterministic pruning to run after a terminal model response, which created redundant resets and made progress-interval accounting misleading.

## Improvements Applied
- Added `prune_progress_interval` and `prune_token_limit` to `AgentRuntimeConfig`, plus validation, so deterministic pruning is explicit and opt-in.
- Added an overridable `pruning_progress_value()` hook on `BaseAgent` so domain agents can map pruning to saved searches, processed records, or other durable work units.
- Kept completion handling ahead of pruning and reset checks so transcript pruning only runs when there is another turn that can benefit from the smaller context window.
- Added targeted runtime tests for interval-based pruning, explicit prune-token pruning, and invalid configuration values.
