## Post-Critique Changes

1. The first reset heuristic would clear context whenever the full request exceeded the threshold, even if the durable parameter block alone was already above the limit.
- Risk: the agent could thrash on repeated no-op resets.
- Improvement made: tightened the reset rule in `src/agents/base.py` so resets happen only when clearing the rolling transcript would actually reduce the request below the configured budget.
