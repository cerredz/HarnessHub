No blocking clarifications were required after Phase 1.

Implementation assumptions carried forward:
- The existing deterministic instance-registry helpers are the correct foundation; this task finishes and applies them rather than inventing a second registry format.
- Shared default SDK memory paths move to `memory/agents/<agent_name>/<instance_id>/`.
- Explicit CLI and SDK memory paths remain valid and are registered as-is.
